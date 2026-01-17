import os
import hashlib
import warnings
from sqlmodel import Session, select, create_engine, SQLModel
from dotenv import load_dotenv
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup, Tag, NavigableString
from models import Author, Book, Chapter

# Suppress library warnings
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')

# 1. Database Setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(DATABASE_URL)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def generate_book_id(filename, title, author):
    unique_string = f"{title}{author}".lower().encode('utf-8')
    hash_digest = hashlib.sha256(unique_string).hexdigest()
    return int(hash_digest, 16) % 2147483647


def get_epub_metadata(book):
    title = book.get_metadata('DC', 'title')
    author = book.get_metadata('DC', 'creator')
    final_title = title[0][0] if title else "Unknown Title"
    final_author = author[0][0] if author else "Unknown Author"
    return final_title, final_author


def flatten_toc(toc):
    """Recursively extracts chapters from the TOC tree."""
    chapters = []
    for item in toc:
        if isinstance(item, tuple) and len(item) == 2:
            section, children = item
            chapters.append(section)
            chapters.extend(flatten_toc(children))
        elif isinstance(item, ebooklib.epub.Link):
            chapters.append(item)
    return chapters


def extract_fragment(soup, start_id, stop_ids):
    """
    Extracts text starting from element with `start_id`
    UNTIL it hits any element containing an id in `stop_ids`.
    """
    if not start_id:
        # If no anchor, assume the whole file is the chapter (for non-monolithic files)
        # But if the file is huge (>200KB), this is risky. Check is done by caller.
        text = soup.get_text(separator='\n')
        return "\n\n".join([line.strip() for line in text.split('\n') if line.strip()])

    start_elem = soup.find(id=start_id)
    if not start_elem:
        return "[Error: Start anchor not found]"

    content_buffer = []

    # Add the title/header itself
    content_buffer.append(start_elem.get_text(separator='\n').strip())

    # Walk through next siblings
    # If the start element is inside a div, we might need to walk up and then next.
    # Standard Ebook strategy: usually flat or nested in sections.

    curr = start_elem.next_element

    while curr:
        if isinstance(curr, Tag):
            # CHECK: Is this the start of the NEXT chapter?
            # If this tag has an ID that is in our "stop_ids" list, we are done.
            if curr.has_attr('id') and curr['id'] in stop_ids:
                break

            # Optimization: Don't dive into tags we just checked
            # If it's a block tag, get its text
            if curr.name in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'li']:
                text = curr.get_text(separator=' ').strip()
                if text:
                    content_buffer.append(text)

        curr = curr.next_element

    return "\n\n".join(content_buffer)


def ingest_book_by_toc(file_path: str):
    try:
        book = epub.read_epub(file_path)
    except Exception:
        print(f"❌ Corrupt: {os.path.basename(file_path)}")
        return

    title, author = get_epub_metadata(book)
    book_id = generate_book_id(file_path, title, author)

    with Session(engine) as session:
        # Check Exists
        if session.exec(select(Book).where(Book.gutenberg_id == book_id)).first():
            print(f"⏭️  Skipping '{title}' (Exists)")
            return

        # Author Setup
        db_author = session.exec(select(Author).where(Author.name == author)).first()
        if not db_author:
            db_author = Author(name=author)
            session.add(db_author)
            session.commit()
            session.refresh(db_author)

        print(f"📖 Processing: {title}...")
        db_book = Book(title=title, gutenberg_id=book_id, author_id=db_author.id)
        session.add(db_book)
        session.commit()
        session.refresh(db_book)

        # 1. Map Files to Soup objects (Parse only once for speed)
        # file_map = { 'index.html': BeautifulSoup_Object }
        file_soups = {}
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Pre-clean the soup to remove scripts/styles
                s = BeautifulSoup(item.get_content(), 'html.parser')
                for trash in s(["script", "style", "title", "meta"]): trash.decompose()
                file_soups[item.file_name] = s

        # 2. Get TOC and build "Fence Posts"
        toc_items = flatten_toc(book.toc)

        # We need to know where the NEXT chapter starts to know where THIS one ends.
        # Group items by filename to create local stop-lists.
        # file_anchors = { 'index.html': ['chap1', 'chap2', 'chap3'] }
        file_anchors_map = {}

        for item in toc_items:
            href_parts = item.href.split('#')
            fname = href_parts[0]
            anchor = href_parts[1] if len(href_parts) > 1 else None

            if fname not in file_anchors_map:
                file_anchors_map[fname] = []

            if anchor:
                file_anchors_map[fname].append(anchor)

        # 3. Extract Content
        db_chapters = []
        counter = 1
        BATCH_SIZE = 25

        for i, item in enumerate(toc_items):
            href_parts = item.href.split('#')
            fname = href_parts[0]
            current_anchor = href_parts[1] if len(href_parts) > 1 else None

            if fname in file_soups:
                soup = file_soups[fname]

                # Determine Stop IDs (The "Fence Posts")
                # All anchors in this file that come AFTER the current one are valid stop signs.
                stop_ids = set()
                if fname in file_anchors_map:
                    all_anchors = file_anchors_map[fname]
                    try:
                        curr_idx = all_anchors.index(current_anchor) if current_anchor else -1
                        # The stop IDs are everything after the current index
                        stop_ids = set(all_anchors[curr_idx + 1:])
                    except ValueError:
                        pass  # Anchor might not be in our mapped list (rare)

                # EXTRACT
                content_str = extract_fragment(soup, current_anchor, stop_ids)

                # Validation: If extracting failed (empty), fallback to raw text
                # ONLY if it's a small file. If huge, we leave it empty/error to prevent crash.
                if len(content_str) < 50:
                    raw_len = len(soup.get_text())
                    if raw_len < 50000:  # 50KB limit for fallback
                        content_str = soup.get_text(separator='\n')
                    elif raw_len > 50000 and len(content_str) < 10:
                        content_str = "[Error: Could not slice huge chapter. Anchor missing?]"

                # Clean Title & ID
                t_lower = item.title.lower()
                is_intro = any(x in t_lower for x in ['intro', 'preface', 'contents', 'acknowledgment'])
                c_num = None if is_intro else counter

                chap = Chapter(
                    book_id=db_book.id,
                    chapter_number=c_num,
                    title=item.title[:100],
                    content=content_str,  # Now correctly sliced!
                    word_count=len(content_str.split())
                )
                db_chapters.append(chap)

                if c_num: counter += 1

            # Batch Commit
            if len(db_chapters) >= BATCH_SIZE:
                session.add_all(db_chapters)
                session.commit()
                db_chapters = []

        # Commit remaining
        if db_chapters:
            session.add_all(db_chapters)
            session.commit()

        print(f"   ✅ Finished {title}.")


if __name__ == "__main__":
    create_db_and_tables()
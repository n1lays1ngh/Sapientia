import os
import sys
from sqlmodel import Session, select, create_engine
from dotenv import load_dotenv
from models import Book, Chapter

# 1. Setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)


def audit_api_readiness():
    with Session(engine) as session:
        print("\n🚀 STARTING FINAL API AUDIT...\n")

        books = session.exec(select(Book)).all()
        total = len(books)

        passed_count = 0
        delete_list = []  # CRITICAL failures
        check_list = []  # WARNINGS (Manual review needed)

        # Valid sentence terminators
        valid_endings = ('.', '!', '?', '"', "'", '”', '’', ')', ']', '}', '_', '-')

        for index, book in enumerate(books, 1):
            print(f"   Scanning [{index}/{total}]: {book.title[:40]}...")

            # Get chapters ordered by number (NULLs come first or last depending on DB, so we sort carefully)
            chapters = session.exec(
                select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.chapter_number)).all()

            # --- CRITICAL CHECKS (Must Delete) ---

            # 1. EMPTY BOOK
            if not chapters:
                delete_list.append((book, "❌ EMPTY (0 Chapters)"))
                continue

            # 2. MISSING "CHAPTER 1" (Story must start at 1)
            # We filter out the NULLs (Intros) and look at the first Real Number
            real_chapters = [c for c in chapters if c.chapter_number is not None]
            real_chapters.sort(key=lambda x: x.chapter_number)  # Ensure sorted 1, 2, 3

            if not real_chapters:
                # It has content, but NO numbered chapters (e.g. only "Preface")
                delete_list.append((book, "❌ NO STORY (Only Unnumbered Front Matter)"))
                continue

            if real_chapters[0].chapter_number != 1:
                delete_list.append(
                    (book, f"❌ STARTS WRONG (First real chapter is {real_chapters[0].chapter_number}, not 1)"))
                continue

            # 3. GAPS IN NUMBERING (1, 2, 4...) -> Breaks "Next Chapter" button
            expected = 1
            gap_found = False
            for ch in real_chapters:
                if ch.chapter_number != expected:
                    delete_list.append((book, f"❌ GAP IN IDs (Expected {expected}, got {ch.chapter_number})"))
                    gap_found = True
                    break
                expected += 1
            if gap_found: continue

            # 4. TRUNCATION (Text cuts off mid-sentence)
            # We check the LAST real chapter.
            last_ch = real_chapters[-1]
            content = last_ch.content.strip()
            if not content:
                delete_list.append((book, f"❌ EMPTY CONTENT (Chapter {last_ch.chapter_number} is blank)"))
                continue

            last_char = content[-1]
            if last_char not in valid_endings and not last_char.isalnum():
                snippet = content[-20:].replace('\n', ' ')
                delete_list.append((book, f"❌ TRUNCATED (Ends with: '...{snippet}')"))
                continue

            # --- WARNING CHECKS (Manual Review) ---

            # A. "Introduction" has a Number (User sees "Chapter 1: Introduction")
            # Ideally, Intro should be NULL. If it has a number, it's not fatal, but annoying.
            first_real_title = real_chapters[0].title.lower()
            if any(x in first_real_title for x in ["introduction", "preface", "foreword"]):
                check_list.append((book, f"⚠️  INTRO IS NUMBERED (Chapter 1 is '{real_chapters[0].title}')"))

            # B. Formatting (Wall of Text)
            # Check a random middle chapter for paragraph breaks
            mid_idx = len(real_chapters) // 2
            mid_ch = real_chapters[mid_idx]
            if mid_ch.word_count > 1000 and "\n\n" not in mid_ch.content:
                check_list.append(
                    (book, f"⚠️  BAD FORMATTING (Chapter {mid_ch.chapter_number} has no paragraph breaks)"))

            # If we survive all this, the book is GOOD.
            passed_count += 1

        # --- FINAL REPORT ---
        print("\n" + "=" * 60)
        print(f"📢  ACTION REPORT")
        print("=" * 60)
        print(f"✅  KEEP:   {passed_count} books are perfect.")
        print(f"⚠️   CHECK:  {len(check_list)} books have minor issues.")
        print(f"🔴  DELETE: {len(delete_list)} books are broken.")
        print("=" * 60)

        if delete_list:
            print("\n🚨 DELETE LIST (Run SQL to remove):")
            print("   DELETE FROM book WHERE gutenberg_id IN (", end="")
            ids = [str(b.gutenberg_id) for b, r in delete_list]
            print(", ".join(ids) + ");\n")

            print("   DETAILS:")
            for book, reason in delete_list:
                print(f"   - ID {book.gutenberg_id}: {reason}")

        if check_list:
            print("\n👀 CHECK LIST (Decide if you want to keep):")
            for book, reason in check_list:
                print(f"   - ID {book.gutenberg_id}: {reason}")


if __name__ == "__main__":
    audit_api_readiness()
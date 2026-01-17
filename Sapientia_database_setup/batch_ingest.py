import os
from ingest import ingest_book_by_toc, create_db_and_tables

# !!! POINT THIS TO YOUR FOLDER !!!
LIBRARY_DIR = "clean_library"


def run():
    print("🚀 Initializing Database...")
    create_db_and_tables()

    if not os.path.exists(LIBRARY_DIR):
        print(f"❌ Error: Folder '{LIBRARY_DIR}' not found.")
        return

    files = [f for f in os.listdir(LIBRARY_DIR) if f.endswith(".epub")]
    total = len(files)
    print(f"Found {total} books.")

    for i, f in enumerate(files):
        print(f"[{i + 1}/{total}] {f}")
        file_path = os.path.join(LIBRARY_DIR, f)
        try:
            ingest_book_by_toc(file_path)
        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    run()
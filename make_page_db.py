import hashlib
import zlib
from pathlib import Path
import sqlite3

import tqdm

PAGE_TABLE = """
create table PAGES (
    type text,
    date text,
    hash text,
    content blob
)
"""

def create_tables(db):
    c = db.cursor()
    c.execute(PAGE_TABLE)

def insert_page(db, typ, date, hash, content):
    db.execute("insert into pages values(?, ?, ?, ?)", [typ, date, hash, content])

def main():
    dbfile = Path("pages.db")
    if dbfile.exists():
        dbfile.unlink()
    db = sqlite3.connect(str(dbfile))
    create_tables(db)
    types = ("singles", "albums")
    for page_type, p in tqdm.tqdm([(typ, file) for typ in types for file in Path(typ).iterdir()]):
        page_type = page_type[:-1] # Strip the "s" from the end
        page_date = p.stem.rpartition('-')[2]
        page_data = p.read_bytes()
        page_hash = hashlib.sha256(page_data).hexdigest()
        page_data_compressed = zlib.compress(page_data, level=9)
        insert_page(db, page_type, page_date, page_hash, page_data_compressed)
        db.commit()

if __name__ == "__main__":
    main()

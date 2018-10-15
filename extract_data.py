from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import sys
import sqlite3
from itertools import chain
from tqdm import tqdm

def maybe_string(tag):
    """Tidy up the string value of a tag.

    Some tags don't have strings, others have leading & trailing whitespace.
    """
    s = tag.string
    if s is not None:
        s = s.strip()
    return s

def maybe_num(tag):
    """Tidy up the numeric value of a tag.

    If the tag's string value is numeric, return as a number, otherwise
    return the (stripped) string.
    """
    s = tag.string
    if s is not None:
        s = s.strip()
        if s.isdigit():
            s = int(s)
    return s

def find_entries(soup):
    """Return all chart entries in a file.

    Entries are in div elements with a class of "track"
    (Even for album entries...)
    """
    return soup.find_all("div", class_="track")

def entry_info(entry):
    """Return the information for a chart entry."""
    # The entry is embedded in a HTML table with 7 columns:
    #   Chart position
    #   Last week's position
    #   The entry details
    #   The peak position the entry achieved
    #   The number of weeks the entry stayed in the chart
    #   Some uninteresting details for the website
    #   The entry metadata (for the website)
    cols = entry.find_parent("tr").find_all("td")
    position, lastweek, details, peak, numweeks, _, metadata = cols

    try:
        # Position is a number
        position = maybe_num(position.span)

        # The last week item includes a class marking entries going up or down
        classes = lastweek.span["class"]
        updown = ""
        if "icon-up" in classes:
            updown = "Up"
        elif "icon-down" in classes:
            updown = "Down"

        # Last week's position is a number, or "New", or "Re"
        lastweek = maybe_num(lastweek.span)

        # The entry details are artist, title, label
        artist = maybe_string(details.find("div", class_="artist").a)
        artist_link = details.find("div", class_="artist").a["href"]
        title = maybe_string(details.find("div", class_="title").a)
        label = maybe_string(details.find("span", class_="label"))

        # The entry details also include a cover image
        cover = details.find("div", class_="cover").img["src"]
        # Most covers are processed by an image resizing utility. If the
        # cover url has a "url" query parameter, use that as the actual url.
        cover = parse_qs(urlparse(cover).query).get('url',[cover])[0]

        # Peak and number of weeks are numbers
        peak = maybe_num(peak)
        numweeks = maybe_num(numweeks)

        # Metadata includes product and chart IDs
        product_id = metadata.a.get("data-productid")
        chart_id = metadata.a.get("data-chartid")
    except Exception as e:
        print("Exception", e)
        print(entry.find_parent("tr"))
        raise

    return (position, lastweek, updown,
            artist, artist_link, title, label, cover,
            peak, numweeks,
            product_id, chart_id)

def page_info(soup):
    page = soup.find("article", class_="page")
    heading = maybe_string(page.find("h1", class_="article-heading"))
    date = maybe_string(page.find("p", class_="article-date"))
    nav = soup.find("nav", class_="charts-nav")
    next_link = nav.find("a", class_="next")
    prev_link = nav.find("a", class_="prev")
    if next_link:
        next_link = next_link["href"]
    if prev_link:
        prev_link = prev_link["href"]

    return heading, date, next_link, prev_link

def extract(path):
    with path.open('rb') as f:
        soup = BeautifulSoup(f, "lxml")

    try:
        pi = page_info(soup)
        ei = []
        for entry in find_entries(soup):
            ei.append(entry_info(entry))
    except Exception:
        print("Error in file {}:".format(path))
        raise
    return pi, ei

CHART_TABLE = """
create table CHARTS (
    filename text,
    heading text,
    date text,
    next_link text,
    prev_link text
)
"""

ENTRY_TABLE = """
create table ENTRIES (
    position text,
    lastweek text,
    updown text,
    artist text,
    artist_link text,
    title text,
    label text,
    cover text,
    peak text,
    numweeks text,
    product_id text,
    chart_id text
)
"""

def create_tables(db):
    c = db.cursor()
    c.execute(CHART_TABLE)
    c.execute(ENTRY_TABLE)

def insert_pageinfo(db, filename, pi):
    db.execute("insert into charts values (?, ?, ?, ?, ?)", (filename,) + pi)

def insert_entryinfo(db, eis):
    db.executemany("insert into entries values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", eis)


def main():
    dbfile = Path("charts.db")
    dbfile.unlink()
    db = sqlite3.connect(str(dbfile))
    create_tables(db)
    for p in tqdm(list(chain(Path("singles").iterdir(), Path("albums").iterdir()))):
        pi, eis = extract(p)
        insert_pageinfo(db, str(p), pi)
        insert_entryinfo(db, eis)
        db.commit()

if __name__ == "__main__":
    main()

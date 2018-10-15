"""Get chart data
"""
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests

from bs4 import BeautifulSoup

CHART_URL = "https://www.officialcharts.com/charts/singles-chart/{:%Y%m%d}/"

def get_chartpage(url, datadir):
    """Get the page for a chart.

    Get the data for a single week's chart, save it and return the
    URL of the next chart (going back in time).
    """

    req = requests.get(url)
    if req.status_code != 200:
        url_date = url.split('/')[-2]
        print("No page for {} - {}".format(url_date, req.status_code))
        return
    soup = BeautifulSoup(req.content)
    the_id = soup.find(id="this-chart-id")
    filename = "Singles-{}.html".format(the_id["value"])
    (datadir / filename).write_bytes(req.content)

    the_nav = soup.find("nav", class_="charts-nav")
    prev = the_nav.find("a", class_="prev")
    nexturl = urljoin(url, prev["href"])
    return nexturl

def main():
    """Main script entry point"""
    datadir = Path("singles")
    if not datadir.is_dir():
        datadir.mkdir()
    today = date.today()
    url = CHART_URL.format(today)
    while True:
        print(url)
        url = get_chartpage(url, datadir)
        if url is None:
            break

if __name__ == "__main__":
    main()

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json
import os
import re

from rich import print
from urllib.parse import urljoin, urlparse


def check_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)


class ComicPlaywright:

    url = (
        "https://comicbookrealm.com/series/113/0/marvel-comics-amazing-spider-man-vol-1"
    )
    series_id = None
    issues_dir = "issues"

    def __init__(self):
        self.issues = []
        self.open_browser()
        self.get_series_id()

    def open_browser(self):
        # pw.start(), pw.stop(), browser.new_page(), browser.close()
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()

    def urljoin(self, path):
        parse = urlparse(self.url)
        base_url = f"{parse.scheme}://{parse.netloc}"
        return urljoin(base_url, path)

    def get_series_id(self):

        # Get series id
        match = re.search(r"series/(\d+)/", self.url)
        if match:
            self.series_id = match.group(1)

        # Check the jsonfile existance
        check_folder(self.issues_dir)
        jsonfile = os.path.join(self.issues_dir, str(self.series_id) + ".json")
        if not os.path.exists(jsonfile):
            self.issues = self.get_issues()
            json.dump(self.issues, open(jsonfile, "w"), indent=4)
        else:
            self.issues = json.load(open(jsonfile))

    def get_issues(self):

        # Define the page variable
        issues = []
        current_page = 1
        page_length = None

        # Open the browser
        page = self.browser.new_page()

        # Make a get request to the url
        page.goto(self.url)

        # Wait till issues table exists
        try:

            # While not the end of the issues page
            while not page_length or current_page < page_length:
                css_selector = f"div#series-details div[class=page_{current_page}] table"
                page.is_visible(css_selector, timeout=10000)
                html = page.inner_html("div#series-details")
                soup = BeautifulSoup(html, "html.parser")

                # Get the issue page and Find the issue page length
                if not page_length:
                    page_length = int(soup.select("tr.type_footer a[class=g]")[-1].text)

                # Collect the rows
                item_list = soup.select(
                    f"div[class=page_{current_page}] table tr[class*=comic]"
                )
                for r in item_list:
                    a = r.select_one("td span + a")
                    issue = {
                        "id": r.get("id", "#"),
                        "title": re.sub(r"\s+", " ", r.get("title", "#").strip()),
                        "link": self.urljoin(a.get("href")),
                        "price": r.select_one("td.value").text.strip(),
                    }
                    issues.append(issue)

                # Find the issues table pagination tab and click next
                if current_page < page_length:
                    pagination = page.query_selector_all("tr.type_footer a.g")
                    next_page = pagination[current_page]
                    next_page.click()
                    time.sleep(2)

                # Add current page state by one
                current_page += 1

        except Exception as E:
            print(E)

        # close browser and stop playwright
        self.browser.close()
        self.pw.stop()

        return issues


if __name__ == "__main__":

    cbr = ComicPlaywright()

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

    series_id = None
    issues_dir = "series"

    def __init__(self, url=None):
        self.url = (
            "https://comicbookrealm.com/series/113/0/marvel-comics-amazing-spider-man-vol-1"
            if not url
            else url
        )
        self.issues = []
        self.open_browser()
        self.get_series_id()

    def open_browser(self):
        # pw.start(), pw.stop(), browser.new_page(), browser.close()
        print("Open the browser", end=" ")
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        print("[green]OK[/green]")

    def urljoin(self, path):
        parse = urlparse(self.url)
        base_url = f"{parse.scheme}://{parse.netloc}"
        return urljoin(base_url, path)

    def create_file(self, item):
        dst_path = os.path.join("output", self.series_id)
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        return os.path.join(dst_path, item["id"] + ".json")

    def get_series_id(self):

        # Get series id
        print("Get the list of issues", end=" ")
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
        print("[green]OK[/green]")

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
        # try:

        # While not the end of the issues page
        while not page_length or current_page <= page_length:
            css_selector = (
                f"div#series-details div[class=page_{current_page}] table"
            )
            page.is_visible(css_selector, timeout=10000)
            html = page.inner_html("div#series-details")
            soup = BeautifulSoup(html, "html.parser")

            # Get the issue page and Find the issue page length
            if not page_length:
                try:
                    page_length = int(soup.select("tr.type_footer a[class=g]")[-1].text)
                except IndexError:
                    page_length = 1

            # Collect the rows
            item_list = soup.select(
                f"div[class=page_{current_page}] table tr[class*=comic]"
            )
            for r in item_list:
                a = r.select_one("td span + a")
                issue = {
                    "id": r.get("id", "#"),
                    "link": self.urljoin(a.get("href")),
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

        # except Exception as E:
        #     print(f"[red]ERROR {E}[/red]")

        # close browser and stop playwright
        self.browser.close()
        self.pw.stop()

        return issues

    def get_detail(self, issue):

        start = time.time()
        comic_id = issue.get("id")
        print("Get content detail from #" + comic_id, end=" ")

        try:

            # Get issue details
            detail = {}
            page = self.browser.new_page()
            page.goto(issue.get("link"))
            page.is_visible("#details", timeout=10000)
            html = BeautifulSoup(page.inner_html("#details"), "html.parser")

            # Get issue title, vol, and years
            soup = BeautifulSoup(page.inner_html("#series-information"), "html.parser")
            detail = {
                "Series": page.inner_text("#series_comic_details_page h2").strip(),
                "Publisher": page.inner_text("#series-information a").strip(),
                "Volume/Years": list(soup.strings)[0].strip(),
            }

            # Get content detail
            item_list = html.select("tr")
            for item in item_list:
                if i == 0:
                    label = (
                        list(item.select_one(".label").strings)[-1]
                        .replace(":", "")
                        .strip()
                    )
                else:
                    label = item.select_one(".label").text.replace(":", "").strip()
                detail.update({label: item.select_one(".data").text.strip()})

            tabs = ["contributors", "characters", "collects", "events", "history"]
            for a in tabs:
                php_url = (
                    f"https://comicbookrealm.com/comic.php?a={a}_tab&comic={comic_id}"
                )
                page.goto(php_url)
                page.is_visible("body", timeout=10000)
                html = BeautifulSoup(page.inner_html("body"), "html.parser")

                detail.update({a.title(): []})

                # Get contributors
                if a == "contributors":
                    detail[a.title()] = self.get_contributors(html.select("ul > li"))

                elif a == "characters":
                    detail[a.title()] = self.get_characters(html.select("ul > li"))

                elif a == "collects":
                    text = page.inner_text("body")
                    if text != "":
                        html = BeautifulSoup(page.content(), "html.parser")
                        detail[a.title()] = self.get_collects(
                            html.select("body > ul > li")
                        )

                elif a == "events":
                    detail[a.title()] = self.get_events(html.select("ul > li"))

                elif a == "history":
                    html = BeautifulSoup(page.content(), "html.parser")
                    detail[a.title()] = self.get_history(html.select("body > ul > li"))

            end = time.time()
            print(f"[green]OK {end-start:.2f} sec[/green]")
            return detail

        except Exception as E:
            print(f"[red]ERROR at [b]get_detail[/b]: {E}[/red]")

    def get_contributors(self, item_list):
        contributors = []
        if len(item_list) == 1:
            return list(map(lambda li: li.text.strip(), item_list))
        elif len(item_list) > 1:
            for li in item_list:
                img_url = li.find("img").get("src")
                link = li.find("a").get("href")
                role = li.find("span").text.strip()
                contributors.append(
                    {
                        "name": li.find("a").get("title"),
                        "img_url": self.urljoin(img_url),
                        "link": self.urljoin(link),
                        "role": re.sub("\s+", " ", role),
                    }
                )
            return contributors

    def get_characters(self, item_list):
        characters = []
        if len(item_list) == 1:
            return list(map(lambda li: li.text.strip(), item_list))
        elif len(item_list) > 1:
            for li in item_list:
                img_url = li.find("img").get("src")
                link = li.find("a").get("href")
                characters.append(
                    {
                        "name": li.find("a").text.strip(),
                        "img_url": self.urljoin(img_url),
                        "link": self.urljoin(link),
                        "info": li.find("span")
                        .text.strip()
                        .strip("(")
                        .strip(")"),  # Do remove the outer brackets
                    }
                )
            return characters

    def get_collects(self, item_list):
        def series(item):
            issue_url = item.get("href")
            return dict(issue=item.text.strip(), issue_url=self.urljoin(issue_url))

        # Prepare the variables and collect the characters
        collects = []
        for li in item_list:
            series_url = li.find("a").get("href")
            publisher_url = li.select_one("a[href*=publisher]").get("href")
            collect = {
                "series_title": li.find("a").text.strip(),
                "series_url": self.urljoin(series_url),
                "vol/year": re.sub("\s+", " ", li.find("span").text.strip()),
                "publisher": li.select_one("a[href*=publisher]").text.strip(),
                "publisher_url": self.urljoin(publisher_url),
                "issues": [series(i) for i in li.select("ul > li a[href*=series]")],
            }
            collects.append(collect)
        return collects

    def get_events(self, item_list):
        if len(item_list) > 1:
            return [li.text.strip() for li in item_list]
        elif len(item_list) == 1:
            return [li.text.strip() for li in item_list]
        else:
            return []

    def get_history(self, item_list):
        histories = []
        for li in item_list:
            link = li.find("a").get("href", "")
            histories.append(
                {
                    "by": li.find("a").text.strip(),
                    "users_url": self.urljoin(link),
                    "datetime": li.find("span").text.strip(),
                    "details": [
                        re.sub("\s+", " ", r.text.strip()) for r in li.find_all("li")
                    ],
                }
            )
        return histories


if __name__ == "__main__":

    series = json.load(open("marvel-comic.json"))
    for s in series:
        n = s.get("number_of_issues")
        print(
            f"[green]Start scraping series: {s.get('url')} ({s.get('years')})[/green]"
        )
        cbr = ComicPlaywright(url=s.get("url"))
        for i in cbr.issues:
            jsonfile = cbr.create_file(i)
            if not os.path.exists(jsonfile):
                content = cbr.get_detail(i)
                json.dump(content, open(jsonfile, "w"), indent=4)

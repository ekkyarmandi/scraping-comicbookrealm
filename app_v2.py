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


class Comic:
    detail = {}

    def __init__(self, id="#", series_id="#", url=None, output="output", page=None):
        self.id = id
        self.url = url
        self.page = page
        self.output = output
        self.series_id = series_id
        self.filename = self.create_filename()

    def urljoin(self, path):
        parse = urlparse(self.url)
        base_url = f"{parse.scheme}://{parse.netloc}"
        return urljoin(base_url, path)

    def get(self):
        """Get comic detail"""

        print("Get content detail for #" + str(self.id), end=" ")

        # Create filename and check issue data existance
        if not os.path.exists(self.filename):

            # Start
            start = time.time()

            # Get details
            detail = {}
            self.page.goto(self.url)
            self.page.wait_for_selector("#details", timeout=10000)

            ## Get issue title, vol, and years
            soup = BeautifulSoup(
                self.page.inner_html("#series-information"), "html.parser"
            )
            detail = {
                "Series": self.page.inner_text("#series_comic_details_page h2").strip(),
                "Publisher": self.page.inner_text("#series-information a").strip(),
                "Volume/Years": list(soup.strings)[0].strip(),
            }

            ## Get the detail detail
            html = BeautifulSoup(self.page.inner_html("#details"), "html.parser")
            item_list = html.select("tr")
            for i, item in enumerate(item_list):
                if i == 0:
                    label = (
                        list(item.select_one(".label").strings)[-1]
                        .replace(":", "")
                        .strip()
                    )
                else:
                    label = item.select_one(".label").text.replace(":", "").strip()
                detail.update({label: item.select_one(".data").text.strip()})

            # Get extra info
            tabs = ["contributors", "characters", "collects", "events", "history"]
            for tab in tabs:

                # Prepare the key for detail dictionary
                key = tab.title()
                detail.update({key: []})

                # Click the tab
                selector = f"ul.tabs2 li[ref={tab}]"
                self.page.click(selector)

                # Wait till the tab ul tag is exists
                try:
                    self.page.wait_for_selector(
                        f"#comic-extra-info #{tab} ul", timeout=3000
                    )

                    html = BeautifulSoup(self.page.inner_html(f"#{tab}"), "html.parser")
                    if tab == "contributors":
                        detail[key] = self.get_contributors(html.select("ul > li"))

                    elif tab == "characters":
                        detail[key] = self.get_characters(html.select("ul > li"))

                    elif tab == "collects":
                        html = BeautifulSoup(
                            page.inner_html("#comic-extra-info"), "html.parser"
                        )
                        detail[key] = self.get_collects(
                            html.select(f"div#{tab} > ul > li")
                        )

                    elif tab == "events":
                        detail[key] = self.get_events(html.select("ul > li"))

                    elif tab == "history":
                        html = BeautifulSoup(
                            page.inner_html("#comic-extra-info"), "html.parser"
                        )
                        detail[key] = self.get_history(
                            html.select(f"div#{tab} > ul > li")
                        )

                except TimeoutError:
                    print(tab, "tab is empty")

            # Save content as JSON file
            self.detail = detail
            self.save_as_json()

            # End
            print(f"[green]OK {time.time()-start:.2f} sec[/green]")
        else:
            print(f"[yellow]SKIPPED[/yellow]")

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

    def create_filename(self, ext="json"):
        """Create filename"""
        name = ".".join([self.id, ext])
        dst_path = os.path.join(self.output, self.series_id)
        check_folder(dst_path)
        return os.path.join(dst_path, name)

    def save_as_json(self):
        """Write it out as JSON file"""

        json.dump(self.detail, open(self.filename, "w"), indent=4)


class ComicBookRealm:

    series_id = None
    series_dir = "series"
    dst_path = "output"

    def __init__(self, page=None):
        self.page = page

        # check folder existance
        check_folder(self.series_dir)
        check_folder(self.dst_path)

    def urljoin(self, path):
        parse = urlparse(self.url)
        base_url = f"{parse.scheme}://{parse.netloc}"
        return urljoin(base_url, path)

    def get_issues(self, series):

        # Start
        start = time.time()
        series_id = str(series["id"])
        print(f"Get series list of issues #" + series_id, end=" ")

        # Parepare the json file for the output
        jsonfile = os.path.join(self.series_dir, series_id + ".json")
        if not os.path.exists(jsonfile):
            color = "green"
            issues = self.collect_issues(series)
            json.dump(issues, open(jsonfile, "w"), indent=4)
        else:
            color = "blue"
            issues = json.load(open(jsonfile))

        # End
        print(f"[{color}]OK {time.time()-start:.2f} sec[/{color}]")
        return issues

    def collect_issues(self, series):

        # Define the page variable
        issues = []
        current_page = 1
        page_length = None

        self.url = series["url"]
        self.series_id = series["id"]

        # Make a get request to the url
        self.page.goto(series["url"], timeout=60 * 1e3, wait_until="domcontentloaded")

        # While not the end of the issues page
        while not page_length or current_page <= page_length:
            css_selector = f"div#series-details div[class=page_{current_page}] table"
            self.page.wait_for_selector(css_selector, timeout=10000)
            soup = BeautifulSoup(
                self.page.inner_html("div#series-details"), "html.parser"
            )

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
                pagination = self.page.query_selector_all("tr.type_footer a.g")
                next_page = pagination[current_page]
                next_page.click()
                time.sleep(2)

            # Add current page state by one
            current_page += 1
        return issues


if __name__ == "__main__":

    # Load series file
    series = json.load(open("marvel-comic.json"))

    # Open the playwright and the page
    with sync_playwright() as pw:
        with pw.chromium.launch() as browser:
            with browser.new_page() as page:

                # Assign the page to comic obejct
                cbr = ComicBookRealm(page=page)

                # Iterate the series
                for s in series:
                    print(
                        f"\n[green]Start scraping series: {s['url']} ({s['years']})[/green]"
                    )

                    # Get the issues list
                    issues = cbr.get_issues(series=s)

                    # Get issue detail then save it as jsonfile
                    for i in issues:
                        comic = Comic(
                            id=i["id"],
                            series_id=s["id"],
                            url=i["link"],
                            page=page,
                            output=cbr.dst_path,
                        )
                        comic.get()

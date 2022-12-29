# import webriver library
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import chromedriver_binary

from bs4 import BeautifulSoup
import json
import time
import os
import re

from rich import print


class ComicBookRealm:
    def __init__(self, url=None):
        self.url = "https://comicbookrealm.com/series/113/0/marvel-comics-amazing-spider-man-vol-1" if not url else url
        self.source = "https://comicbookrealm.com"
        self.series = []
        self.time_leapse = []
        self.dst_path = "output"
        self.get_series_id()
        self.open_browser()

    def open_browser(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--level-log=3")
        self.browser = Chrome(options=options)
        self.browser.get(self.url)
        self.get_series()

    def get_series_id(self):
        self.series_id = "#"
        match = re.search(r"series/([0-9]+)/",self.url)
        if match:
            self.series_id = match.group(1)

    def get_series(self):

        start = time.time()

        def check_path(path):
            if not os.path.exists(path):
                os.makedirs(path)

        def clean_description(text):
            return re.sub("\s+", " ", text)

        def get_link(a_tag):
            url = "#"
            if len(a_tag) > 0:
                return a_tag[0].get("href")
            return url

        # check series folder existance
        root = "issues"
        check_path(root)

        self.dst_path = os.path.join(self.dst_path,self.series_id)
        check_path(self.dst_path)

        # check series issue json file
        json_file = os.path.join(root,self.series_id+".json")
        if not os.path.exists(json_file):

            # Define the initial page
            current_page = 1
            page_length = None

            while not page_length or current_page < page_length:

                # Find issues urls on the page
                issues = self.click_on(wait_for=f"div#series-details div.page_{current_page} table tr[class*=comic]")
                for idx,r in enumerate(issues):
                    # if idx==0:
                    #     print(r)
                    a = r.select("td span + a")
                    self.series.append(
                        {
                            "id": r.get("id", "#"),
                            "title": clean_description(r.get("title", "#")),
                            "link": self.urljoin(get_link(a)),
                            "price": r.find("td", {"class": "value"}).text.strip(),
                        }
                    )
                
                # Get the issue page and Find the issue page length
                if not page_length:
                    html = BeautifulSoup(self.browser.page_source,"html.parser")
                    pages = html.select_one("div#series-details tr.type_footer")
                    page_length = max(list(map(int,[a.text.strip() for a in pages.select("a[class=g]")])))

                # Click on the next page
                next_page = self.browser.find_elements(by=By.CSS_SELECTOR,value="#series-details tr.type_footer a.g")[current_page]
                next_page.click()
                current_page += 1

            # After pagination is done save the series data as json file
            json.dump(
                self.series,
                open(json_file,"w"),
                indent=4
            )

        else:
            self.series = json.load(open(json_file))

        # Print out the time leapes
        end = time.time()
        print(f"[green]GET Issues: {end-start:.3f} sec[/green]")

    def get_content_detail(self, item):
        content_detail = {}
        try:
            self.browser.get(item["link"])
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div#details table tbody tr")
                )
            )
            html = BeautifulSoup(self.browser.page_source, "html.parser")

            # Get page title
            div_detail = html.find("div", id="series_comic_details_page")
            title = div_detail.find("h2").text.strip()

            # Get series information
            information = html.find("div", id="series-information")
            publisher = information.find("a").text.strip()
            for i, s in enumerate(information):
                if i == 0:
                    volume = s
                    break

            content_detail.update(
                {"Series/Title": title, "Volume/Year": volume, "Publisher": publisher}
            )

            # Get content detail
            detail = html.select("div#details table tbody tr")
            for tr in detail:
                label = ""
                for s in tr.find("td", {"class": "label"}).strings:
                    label = s
                content_detail.update(
                    {label.strip(): tr.find("td", {"class": "data"}).text.strip()}
                )
            content_detail.update({"Issue URL": item["link"]})
            return content_detail

        except Exception as E:
            print("[red]ERROR get_content_detail: " + str(E) + "[/red]")

    def get_contributors(self):
        
        # Click on contributors tab
        item_list = self.click_on(tab_id="contributors",wait_for="div#contributors li")

        # Prepare the variables and collect the contributors
        contributors = []
        for li in item_list:
            img_url = li.find("img").get("src")
            link = li.find("a").get("href")
            contributor = {
                "name": li.find("a").get("title"),
                "img_url": self.urljoin(img_url),
                "link": self.urljoin(link),
                "role": li.find("span").text.strip()
            }
            contributor['role'] = re.sub("\s+"," ",contributor['role'])
            contributors.append(contributor)
        return contributors

    def get_characters(self):

        # Click on characters tab
        item_list = self.click_on(tab_id="characters",wait_for="div#characters li")

        # Prepare the variables and collect the characters
        characters = []
        for li in item_list:
            img_url = li.find("img").get("src")
            link = li.find("a").get("href")
            character = {
                "name": li.find("a").text.strip(),
                "img_url": self.urljoin(img_url),
                "link": self.urljoin(link),
                "info": li.find("span").text.strip().strip("(").strip(")") # Do remove the outer brackets
            }
            characters.append(character)
        return characters

    def get_collects(self):

        def series(item):
            issue_url = item.get("href")
            return dict(
                issue=item.text.strip(),
                issue_url=self.urljoin(issue_url)
            )
        
        # Click on the collects tab
        item_list = self.click_on(tab_id="collects",wait_for="div#collects > ul > li")

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
                "issues": [series(i) for i in li.select("ul > li a[href*=series]")]
            }
            collects.append(collect)
        return collects

    def get_events(self):

        # Click on history tab and get the list
        item_list = self.click_on("events","#events > ul > li")
        
        # Prepare the variables and collect the characters
        events = []
        if len(item_list) > 1:
            # Find page with no empty events
            return [li.text.strip() for li in item_list]
        elif len(item_list) == 1:
            return [li.text.strip() for li in item_list]
        else:
            return []

    def get_history(self):

        # Click on history tab and get the list
        item_list = self.click_on("history","#history > ul > li")

        # Prepare the variables and collect the characters
        histories = []
        for li in item_list:
            link = li.find("a").get("href","")
            history = {
                "by": li.find("a").text.strip(),
                "users_url": self.urljoin(link),
                "datetime": li.find("span").text.strip(),
                "details": [re.sub("\s+"," ",r.text.strip()) for r in li.find_all("li")]
            }
            histories.append(history)
        return histories

    def click_on(self,tab_id=None,wait_for="css_selector"):

        # Click on the tab
        if tab_id:
            self.browser.find_element(by=By.CSS_SELECTOR,value=f"li[ref={tab_id}]").click()

        # Wait until the table presence
        try:
            WebDriverWait(self.browser,10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,wait_for))
            )

            # Read page source as soup object
            html = BeautifulSoup(self.browser.page_source,"html.parser")

            # Get the item as a list
            return html.select(wait_for)
                
        except Exception as E:
            print(f"[red]ERROR click on tab '{tab_id}' error: {str(E)}[/red]")
            return []

    def quit(self, sec=3):
        time.sleep(sec)
        self.browser.quit()

    def mean_time(self, sec):
        self.time_leapse.append(sec)
        return sum(self.time_leapse)/len(self.time_leapse)

    def urljoin(self, url):
        if url[0] == "/":
            return self.source + url
        else:
            return self.source + "/" + url

if __name__ == "__main__":

    cbr = ComicBookRealm()
    for item in cbr.series:
        _id = item['id']
        filename = os.path.join(cbr.dst_path,str(_id)+".json")
        if not os.path.exists(filename):
            start = time.time()
            content = cbr.get_content_detail(item)
            content.update({
                "Contributors": cbr.get_contributors(),
                "Characters": cbr.get_characters(),
                "Collects": cbr.get_collects(),
                "Events": cbr.get_events(),
                "History": cbr.get_history(),
            })

            # Save the content
            json.dump(
                content,
                open(filename,"w"),
                indent=4
            )

            # Time leapse calculation
            end = time.time()
            tl = end-start
            avg = cbr.mean_time(tl)
            print(f"[green]Collect Issues: {tl:.3f} sec (speed: {avg:.3f} sec/item)[/green]")

    cbr.quit()

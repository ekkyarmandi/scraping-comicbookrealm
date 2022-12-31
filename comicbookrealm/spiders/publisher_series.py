import scrapy
import json
import re


class PublisherSeriesSpider(scrapy.Spider):
    name = "publisher_series"
    allowed_domains = ["www.comicbookrealm.com"]

    # Read all publishers
    publishers = json.load(open("all-publisher.json"))

    start_urls = []
    for p in publishers:
        series = [*p["series"]]
        start_urls.extend(series)

    def parse(self, response):

        # Get the alphabet character from the url
        page = response.url.split("/")[-1].upper()
        if page == "NUM":
            page = "#"

        # Find the table and collect the rows
        item_list = response.css("table#series-search-results tbody > tr[class*=row]")
        for i in item_list:
            url = i.css("td.title a::attr(href)").get()
            series_id = re.search("series/(\d+)/", url).group(1)
            yield {
                "page": page,
                "origin": response.url,
                "id": series_id,
                "url": response.urljoin(url),
                "vol": i.css("td.volume::text").get().strip(),
                "years": i.css("td.years::text").get().strip(),
                "number_of_issues": i.css("td.issues::text").get().strip(),
            }

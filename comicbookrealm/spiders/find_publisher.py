import re
import scrapy


class FindPublisherSpider(scrapy.Spider):
    name = "find_publisher"
    allowed_domains = ["comicbookrealm.com"]
    start_urls = [
        "http://www.comicbookrealm.com/publisher/" + str(i) for i in range(3, 8000)
    ]

    def parse(self, response):
        a_tag = response.css(".publisher-list a::attr(href)").get()
        if a_tag:
            publisher = a_tag.split("/")[-2]
            all_series = response.css(
                ".publisher-list a[href*=publisher]::attr(href)"
            ).getall()
            all_series = [response.urljoin(url) for url in all_series]
            yield {
                "publisher": publisher,
                "series": all_series,
            }
        else:
            pass

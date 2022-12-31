# Comic Book Realm Data Scraping Project

This data scraping project was developed using Selenium.

The main task was about scraping the issue data within a [page](https://comicbookrealm.com/series/113/0/marvel-comics-amazing-spider-man-vol-1).

### How to run
1. Install the dependencies
    ```
    pip install -r requirements.txt
    ```
    Since the script was employeed `Playwright` for rendering the page. It require playwright driver such as chromium or firefox by excuting `playwright install` (this might take sometimes).

2. Gather all the series from the publishers  
    In this step, publisher.json file is require as an input. The publisher.json will contain series of the comic. Each iteration of series will consumed as the input for gathering all the issues.

    Sometime publisher.json are named with the publisher name, i.e. marvel-comic.json.

    To gather all the series of the publisher, you need to crawl it using scrapy by executing the command below
    ```
    scrapy crawl publisher_series -o <publisher-name>.json
    ```

3. Run the script
    ```
    python app_v2.py
    ```

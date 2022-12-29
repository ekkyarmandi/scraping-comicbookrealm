# Comic Book Realm Data Scraping Project

This data scraping project was developed using Selenium.

The main task was about scraping the issue data within a [page](https://comicbookrealm.com/series/113/0/marvel-comics-amazing-spider-man-vol-1).

### How to run
* Install the dependencies
```
pip install -r requirements.txt
```
NOTE: I use chromedriver_binary library instead of external driver chromedriver.exe for the webdriver

* Specify base url
After loading the `ComicBookRealm` object, you can specify the other main url with parameter `url`. By default it was [this](https://comicbookrealm.com/series/113/0/marvel-comics-amazing-spider-man-vol-1).
```
cbr = ComicBookRealm(url="https://comicbookrealm.com/<your-selected-series>")
```

* Run the script
```
python app.py
```

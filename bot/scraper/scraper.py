from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import json
import time
import os

TODAY_NATIONAL = "./scraper/data/today_national.json"

# ========== NATIONAL ==========


def get_today_national(driver):
    """
    Get the links to today's national news from a specific category on a news website.

    Args:
        driver: A Selenium webdriver instance.

    Returns:
        A list of strings, each representing a link to an article.
    """
    driver.get("https://borneobulletin.com.bn/category/national/")
    SCROLL_DOWN_FREQUENCY = 4
    for _ in range(SCROLL_DOWN_FREQUENCY):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    today_date = datetime.today().strftime("%Y-%m-%d")

    articles = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                ".td_module_flex.td_module_flex_1.td_module_wrap.td-animation-stack",
            )
        )
    )

    national_links = []
    for article in articles:
        # Get the date of the article
        try:
            date = article.find_element(
                By.CSS_SELECTOR, ".entry-date.updated.td-module-date"
            ).get_attribute("datetime")
        except NoSuchElementException:
            date = ""

        # Get the 5 national news from hero section
        try:
            hero = article.find_element(By.CSS_SELECTOR, ".td-category-pos-above")
        except:
            hero = None

        if hero != None and date.startswith(today_date):
            link = article.find_element(
                By.CSS_SELECTOR, ".td-image-wrap"
            ).get_attribute("href")
            national_links.append(link)
            continue

        # Get other National news below hero section
        try:
            category = article.find_element(
                By.CSS_SELECTOR, ".td-post-category"
            ).text.lower()
        except NoSuchElementException:
            category = ""

        if category == "national" and date.startswith(today_date):
            link = article.find_element(
                By.CSS_SELECTOR, ".td-image-wrap"
            ).get_attribute("href")
            national_links.append(link)
            continue

    return national_links


def main_national():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(
        options=options,
        service=ChromeService(executable_path=ChromeDriverManager().install()),
    )
    national_links = get_today_national(driver)
    driver.delete_all_cookies()
    article_data = []
    for link in national_links:
        article_data.append(get_article_data(driver, link, download_image=True))
        driver.delete_all_cookies()

    today_date = datetime.today().strftime("%Y-%m-%d")
    today_national = {"date": today_date, "article_data": article_data}

    directory = os.path.dirname(TODAY_NATIONAL)
    os.makedirs(directory, exist_ok=True)
    with open(TODAY_NATIONAL, "w") as outfile:
        json.dump(today_national, outfile)

    return today_national


# ========== SHARED FUNCTIONS ==========


def get_article_data(driver, url, download_image=False):
    """
    Extracts article data from a web page using Selenium.

    Args:
        driver (selenium.webdriver): A Selenium webdriver instance.
        url (str): The URL of the web page to extract data from.
        download_image (bool, optional): Whether to download and include the URL of the first thumbnail image of the article in the output. Default is False.

    Returns:
        dict: A dictionary with the following keys:
        - url (str): The URL of the article.
        - title (str): The title of the article.
        - author (str): The name of the author of the article. If no author is found, this field is an empty string.
        - content_text (str): The full text content of the article.
        - image_url (str, optional): The URL of the first thumbnail image of the article, if `download_image` is True. Otherwise, this field is not included.

        If an error occurs during extraction, the function returns None.
    """
    driver.get(url)

    title_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "h1"))
    )
    title = title_element.text
    content_elements = driver.find_elements(By.TAG_NAME, "p")
    author = content_elements[0].text
    if len(author.split()) <= 5:
        content_text = " ".join([elem.text for elem in content_elements[1:]])
    else:
        author = ""
        content_text = " ".join([elem.text for elem in content_elements[:]])

    if download_image:
        image_url = get_article_image_thumbnail_url(driver)
    else:
        image_url = ""

    article_data = {
        "url": url,
        "title": title,
        "author": author,
        "content_text": content_text,
        "image_url": image_url,
    }

    return article_data


def get_article_image_thumbnail_url(driver):
    """
    Extracts the URL of the first thumbnail image of an article from a webpage using Selenium.

    Args:
        driver (selenium.webdriver): A Selenium webdriver instance.

    Returns:
        str: The URL of the first thumbnail image of the article, or None if no thumbnail is found.
    """
    try:
        image_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.size-full"))
        )
        image_url = image_element.get_attribute("src")
        return image_url
    except:
        return ""




if __name__ == "__main__":
    main_national()

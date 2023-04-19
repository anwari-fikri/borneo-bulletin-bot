from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import urllib.request
import re
import os


def get_today_headline(driver):
    """
    Get the links to today's headlines from a specific category on a news website.

    Args:
        driver: a Selenium webdriver instance

    Returns:
        A list of links (strings) to the articles
    """
    driver.get("https://borneobulletin.com.bn/category/headline/")

    today_date = datetime.today().strftime("%Y-%m-%d")

    articles = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".td-module-container"))
    )

    headline_links = []
    for article in articles:
        try:
            category = article.find_element(By.CSS_SELECTOR, ".td-post-category")
            date = article.find_element(
                By.CSS_SELECTOR, ".entry-date.updated.td-module-date"
            ).get_attribute("datetime")
            if category.text.lower() == "headline" and date.startswith(today_date):
                link = article.find_element(
                    By.CSS_SELECTOR, ".td-image-wrap"
                ).get_attribute("href")
                headline_links.append(link)
        except NoSuchElementException:
            continue

    return headline_links


def get_article_data(driver, url):
    """
    Extract article data from a web page using Selenium.

    Args:
        driver: A Selenium webdriver instance.
        url (str): The URL of the web page to extract data from.

    Returns:
        A dictionary with the following keys:
        - url (str): The URL of the article.
        - title (str): The title of the article.
        - author (str): The name of the author of the article.
        - content_text (str): The full text content of the article.

        If an error occurs during extraction, the function returns None.
    """
    driver.get(url)

    title_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "h1"))
    )
    title = title_element.text

    content_elements = driver.find_elements(By.TAG_NAME, "p")
    author = content_elements[0].text
    content_text = " ".join([elem.text for elem in content_elements[1:]])
    image_path = download_article_images(driver, title)

    article_data = {
        "url": url,
        "title": title,
        "author": author,
        "content_text": content_text,
        "image_path": image_path,
    }

    return article_data


def download_article_images(driver, title):
    """
    Download all images from a webpage and save them in a sub-folder named after the article's title in the 'image' directory.

    Args:
        driver: A Selenium webdriver instance.
        title (str): The title of the article to create a sub-folder name.

    Returns:
        String of folder path of saved images. Images are saved in the 'image' directory in a sub-folder named after the article's title.
        Each image is saved in the sub-folder as a .jpg file with a name corresponding to the order it appears on the page.
    """

    image_elements = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img.size-full"))
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    sub_folder = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")
    folder = os.path.join("image", sub_folder)

    if not os.path.exists(folder):
        os.makedirs(folder)

    for i, image_element in enumerate(image_elements):
        image_url = image_element.get_attribute("src")
        req = urllib.request.Request(image_url, headers=headers)
        filename = f"{i+1}.jpg"
        with urllib.request.urlopen(req) as url_response:
            with open(os.path.join(folder, filename), "wb") as img_file:
                img_file.write(url_response.read())

    return folder


def main():
    # TODO: make the scraper to not restart driver every link (bypass Cloudflare)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(
        options=options,
        service=ChromeService(executable_path=ChromeDriverManager().install()),
    )
    headline_links = get_today_headline(driver)
    driver.close()
    article_data = []
    for link in headline_links:
        driver = webdriver.Chrome(
            options=options,
            service=ChromeService(executable_path=ChromeDriverManager().install()),
        )
        article_data.append(get_article_data(driver, link))
        driver.close()

    return article_data


if __name__ == "__main__":
    main()

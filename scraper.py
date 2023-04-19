from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


def get_today_headline(driver):
    """
    Get the links to today's headlines from a specific category on a news website.

    Args:
        driver: a Selenium webdriver instance

    Returns:
        A list of links (strings) to the articles

    Raises:
        NoSuchElementException: if no headlines are found
        ValueError: if the website's date format is not "YYYY-MM-DD"
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

    if not headline_links:
        raise NoSuchElementException("No headlines found")

    return headline_links


def get_article_data(driver, url):
    driver.get(url)

    title_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "h1"))
    )
    title = title_element.text

    content_elements = driver.find_elements(By.TAG_NAME, "p")
    author = content_elements[0].text
    content_text = " ".join([elem.text for elem in content_elements[1:]])

    article_data = {
        "url": url,
        "title": title,
        "author": author,
        "content_text": content_text,
    }
    return article_data


def main():
    # TODO: make the scraper to not restart driver every link (bypass Cloudflare)
    driver = webdriver.Chrome(
        service=ChromeService(executable_path=ChromeDriverManager().install()),
    )
    headline_links = get_today_headline(driver)
    driver.close()
    article_data = []
    for link in headline_links:
        driver = webdriver.Chrome(
            service=ChromeService(executable_path=ChromeDriverManager().install()),
        )
        article_data.append(get_article_data(driver, link))
        driver.close()

    return article_data


if __name__ == "__main__":
    main()

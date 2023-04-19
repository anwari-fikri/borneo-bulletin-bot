from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime


def get_today_headline(driver):
    driver.get("https://borneobulletin.com.bn/category/headline/")
    driver.implicitly_wait(3)
    today_date = datetime.today().strftime("%Y-%m-%d")
    articles = driver.find_elements(By.CSS_SELECTOR, ".td-module-container")

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
    driver.get(url)
    driver.implicitly_wait(3)

    title = driver.find_element(By.TAG_NAME, "h1")
    print(title.text)

    content = driver.find_elements(By.TAG_NAME, "p")
    for p in content:
        print(p.text)


def main():
    driver = webdriver.Chrome(
        service=ChromeService(executable_path=ChromeDriverManager().install())
    )
    headline_links = get_today_headline(driver)
    for link in headline_links:
        get_article_data(driver, link)
    driver.close()


if __name__ == "__main__":
    main()

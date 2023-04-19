from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime


def get_today_headline(driver, url):
    driver.get(url)
    driver.implicitly_wait(3)
    today_date = datetime.today().strftime('%Y-%m-%d')
    articles = driver.find_elements(By.CSS_SELECTOR, ".td-module-container")

    for article in articles:
        try:
            category = article.find_element(By.CSS_SELECTOR, ".td-post-category")
            date = article.find_element(By.CSS_SELECTOR, ".entry-date.updated.td-module-date").get_attribute("datetime")
            if category.text.lower() == "headline" and date.startswith(today_date):
                link = article.find_element(By.CSS_SELECTOR, ".td-image-wrap").get_attribute("href")
                print(link)
        except NoSuchElementException:
            continue

def get_article_data(driver, url):
    driver.get(url)
    driver.implicitly_wait(3)
    
    title = driver.find_element(By.TAG_NAME, "h1")
    print(title.text)

def main():
    driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
    # get_today_headline(driver, "https://borneobulletin.com.bn/category/headline/")
    get_article_data(driver, "https://borneobulletin.com.bn/raya-treats-for-the-needy/")
    driver.close()


if __name__ == '__main__':
    main()
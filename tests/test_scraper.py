import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bot.scraper import scraper


@pytest.fixture(scope="session")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(
        options=options,
        service=ChromeService(executable_path=ChromeDriverManager().install()),
    )
    yield driver
    driver.quit()


def test_get_today_headline(driver):
    result = scraper.get_today_headline(driver)
    assert isinstance(result, list)
    assert all(isinstance(link, str) for link in result)
    assert all(link.startswith("https://borneobulletin.com.bn") for link in result)


def test_get_article_data(driver):
    url = "https://borneobulletin.com.bn/to-the-rescue-firefighters-save-cats-from-house-fire-2/"
    article_data = scraper.get_article_data(driver, url)

    assert article_data["url"] == url
    assert article_data["title"] == "To the rescue: Firefighters save cats from house fire"
    assert article_data["author"] == "James Kon"
    assert "Firefighters saved a number of cats while battling a two-storey house fire" in article_data["content_text"]

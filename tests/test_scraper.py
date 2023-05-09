from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bot.scraper import scraper


def test_get_today_headline():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(
        options=options,
        service=ChromeService(executable_path=ChromeDriverManager().install()),
    )
    result = scraper.get_today_headline(driver)
    assert isinstance(result, list)
    assert all(isinstance(link, str) for link in result)
    assert all(link.startswith("https://borneobulletin.com.bn") for link in result)
    driver.quit()

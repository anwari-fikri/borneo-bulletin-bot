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

TODAY_HEADLINE = "./scraper/data/today_headline.json"
TODAY_NATIONAL = "./scraper/data/today_national.json"

# ========== HEADLINE ==========


def get_today_headline(driver):
    """
    Get the links to today's headlines from a specific category on a news website.

    Args:
        driver: A Selenium webdriver instance.

    Returns:
        A list of strings, each representing a link to an article.
    """
    driver.get("https://borneobulletin.com.bn/category/headline/")

    today_date = datetime.today().strftime("%Y-%m-%d")

    articles = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                ".td_module_flex.td_module_flex_1.td_module_wrap.td-animation-stack",
            )
        )
    )

    headline_links = []
    for article in articles:
        # Get the date of the article
        try:
            date = article.find_element(
                By.CSS_SELECTOR, ".entry-date.updated.td-module-date"
            ).get_attribute("datetime")
        except NoSuchElementException:
            date = ""

        # Get the 5 headline news from hero section
        try:
            hero = article.find_element(By.CSS_SELECTOR, ".td-category-pos-above")
        except:
            hero = None

        if hero != None and date.startswith(today_date):
            link = article.find_element(
                By.CSS_SELECTOR, ".td-image-wrap"
            ).get_attribute("href")
            headline_links.append(link)
            continue

        # Get other headline news below hero section
        try:
            category = article.find_element(
                By.CSS_SELECTOR, ".td-post-category"
            ).text.lower()
        except NoSuchElementException:
            category = ""

        if category == "headline" and date.startswith(today_date):
            link = article.find_element(
                By.CSS_SELECTOR, ".td-image-wrap"
            ).get_attribute("href")
            headline_links.append(link)
            continue

    return headline_links


def main_headline():
    # TODO: make the scraper to not restart driver every link (bypass Cloudflare)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
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
        article_data.append(get_article_data(driver, link, download_image=True))
        driver.close()

    today_date = datetime.today().strftime("%Y-%m-%d")
    today_headline = {"date": today_date, "article_data": article_data}

    directory = os.path.dirname(TODAY_HEADLINE)
    os.makedirs(directory, exist_ok=True)
    with open(TODAY_HEADLINE, "w") as outfile:
        json.dump(today_headline, outfile)

    return today_headline


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
    SCROLL_DOWN_FREQUENCY = 2
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
    for link in national_links:
        print(link)
    driver.close()
    article_data = []
    for link in national_links:
        driver = webdriver.Chrome(
            options=options,
            service=ChromeService(executable_path=ChromeDriverManager().install()),
        )
        article_data.append(get_article_data(driver, link, download_image=True))
        driver.close()

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
        image_url = None

    article_data = {
        "url": url,
        "title": title,
        "author": author,
        "content_text": content_text,
    }

    if download_image:
        article_data["image_url"] = image_url

    return article_data


def get_article_image_thumbnail_url(driver):
    """
    Extracts the URL of the first thumbnail image of an article from a webpage using Selenium.

    Args:
        driver (selenium.webdriver): A Selenium webdriver instance.

    Returns:
        str: The URL of the first thumbnail image of the article, or None if no thumbnail is found.
    """

    image_elements = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "img.size-full"))
    )
    image_url = image_elements.get_attribute("src")

    return image_url


def fake_return_article():
    today_date = datetime.today().strftime("%Y-%m-%d")
    return {
        "date": today_date,
        "article_data": [
            {
                "url": "https://borneobulletin.com.bn/raya-treats-for-the-needy/",
                "title": "Raya treats for the needy",
                "author": "Izah Azahari",
                "content_text": "Network Integrity Assurance Technologies (NiAT) Sdn Bhd organised a charity shopping event titled ‘Shopping Raya with NiAT’ for 10 underprivileged families to support their Raya preparation needs yesterday. Held at the Hua Ho Department Store in OneCity Shopping Centre in Salambigar, the event was organised as part of NiAT’s corporate social responsibility (CSR) initiative this year and promote volunteerism to give back to society by instilling in its employees a caring culture that aids those who are less fortunate. During the event, NiAT covered up to BND300 worth of necessities for each of the selected family. Over 20 NiAT staff members assisted the families with their grocery purchases. NiAT’s Chief Executive Officer Lim Ming Soon said “We believe it is essential to show happiness in the lives of others, and we intend to uphold this belief through the initiative. “It gives us great delight to contribute to the happiness of these families. We are also pleased to provide them with financial assistance and bring them the joy of Hari Raya so that they, too, may enjoy the upcoming festivities as much as everyone else”. The families were identified by Projek Feed, a social enterprise focussing on aiding financially-challenged families.    ",
                "image_url": "",
            },
            {
                "url": "https://borneobulletin.com.bn/promoting-community-spirit-through-donation/",
                "title": "Promoting community spirit through donation",
                "author": "Azlan Othman",
                "content_text": "Forty-four orphans of the Ministry of Religious Affairs (MoRA) workforce received donations yesterday at the ministry’s premises. Minister of Religious Affairs Pehin Udana Khatib Dato Paduka Seri Setia Ustaz Haji Awang Badaruddin bin Pengarah Dato Paduka Haji Awang Othman handed over the donations. The donations were aimed at easing the burden of the less fortunate while instilling good values among the ministry’s workforce through charity work and practices and to build a community within the ministry.  ",
                "image_url": "",
            },
            {
                "url": "https://borneobulletin.com.bn/ministry-holds-tedarus-al-quran-nationwide/",
                "title": "Ministry holds Tedarus Al-Quran nationwide",
                "author": "Daniel Lim & Adib Noor",
                "content_text": "The Ministry of Culture, Youth and Sports (MCYS), through the Youth and Sports Department (JBS) held a youth Tedarus Al-Quran programme across the country to enliven the holy month of Ramadhan. In the Brunei-Muara District, the programme was held at Pintu Malim Mosque. Minister of Culture, Youth and Sports Dato Seri Setia Awang Haji Nazmi bin Haji Mohamad attended as the guest of honour. The event began with the recitation of Surah Al-Fatihah, led by the guest of honour, followed by Tedarus Al-Quran led by Pintu Malim Mosque imam Muhammad Syukri bin Pengiran Haji Sulaiman. Representatives from the Brunei History Centre, members of Bandar Seri Begawan Youth Club, Al-Busyra and alumni members of Asuhan Minda Belia Camp 2023 also participated. The ceremony continued with the recitation of Doa Tahlil, led by National Al-Quran Reading Competition for Youth 1443 Hijrah Qari runner-up Abdul Haziq Syarafuddin bin Abdul Habib. This was followed by Doa Peliharakan Sultan dan Negara Brunei Darussalam and a mass Zohor prayer.     Meanwhile, in the Temburong District, the ceremony was held at Kampong Batu Apoi, attended by Permanent Secretary (Sports) at the MCYS Pengiran Mohd Amirrizal bin Pengiran Haji Mahmud as the guest of honour. The event began with the recitation of Surah Al-Fatihah, led by the guest of honour, followed by Tedarus Al-Quran, led by Muhammad Nur Aziimin bin Shahminan from Belia Permata Hijau. This was followed by the recitation of Doa Tahlil led by Muhammad Zulkhairi bin Azamy from Belia Permata Hijau. The ceremony ended with Doa Peliharakan Sultan dan Negara Brunei Darussalam and a mass Zohor prayer led by the mosque’s imam, Shamsuddin bin Haji Azahari. In the Tutong District, the ceremony was held at Kampong Sinaut Mosque with Acting Director of Museums Pengiran Haji Rosli bin Pengiran Haji Halus attending as the guest of honour. The event began with the recitation of Surah Al-Fatihah led by the guest of honour followed by Tedarus Al-Quran led by the mosque’s imam Pengiran Muhd Fakhrin bin Pengiran Mohd Dani Muhammad. A Doa Tahlil was led by Muhammad Darwisy Afiq bin Jailani from the Tutong Youth Movement (IMPAK). The ceremony concluded with Doa Peliharakan Sultan dan Selamatkan Negara Brunei Darussalam and a mass Zohor prayer. Meanwhile, in the Belait District, the programme was held at Kampong Pandan Mosque. The event was attended by Acting Director of the National Service Division Major (Rtd) Haji Mohammad bin Dollah as the guest of honour. The programme started with the recitation of Surah Al-Fatihah led by the guest of honour, followed by the recitation of Tedarus Al-Quran, led by Haji Abdul Afiq bin Zainuddin from the Brunei Youth Council. The recitation of Doa Tahlil was led by Mohammad Nabil bin Mohammad Nordin from Religious Teachers University College of Seri Begawan (KUPU SB). The recitation of Doa Allah Peliharakan Sultan dan Negara Brunei Darussalam was led by Mosque Affairs Officer Abdul Qayyum bin Haji Aminnuddin. The guest of honour also presented a contribution from the Youth and Sports Department Belait District Branch to Abdul Qayyum. The event concluded with a mass Zohor prayer.  ",
                "image_url": "",
            },
        ],
    }


if __name__ == "__main__":
    main_headline()

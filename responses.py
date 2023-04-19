import random
import scraper


def handle_response(message) -> str:
    p_message = message.lower()

    if "test scraper" in p_message:
        article_data = scraper.fake_return()
        article_1 = article_data[0]["content_text"]
        return article_1

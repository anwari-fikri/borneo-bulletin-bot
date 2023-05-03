# Borneo Bulletin News Bot
This is a Python-based Discord bot that scrapes a Borneo Bulletin website's Headline category, summarizes news articles using GPT-3.5, and posts them in a Discord channel. This bot is designed to provide daily news updates to users in an easy and efficient way.

## Features
- ✅ Scrapes the Headline category of a news website using Python and Selenium. 
- ✅ Retrieves all the headlines for the day. 
- ⬜ Uses GPT-3.5 to summarize news articles.
- ✅ Extracts relevant images and includes them in the summary. 
- ✅ Posts the summary in a Discord channel.
- ✅ Includes a hyperlink to the original article. 
- ✅ Runs automatically at a specific time every day. 

## Usage
* Invite the [Borneo Bulletin Bot](https://discord.com/api/oauth2/authorize?client_id=1097394756985819136&permissions=2147485696&scope=bot) to your Discord server. 
* Type /toggle_scheduled_news in any text channel to get a daily news headlines at the 9am Brunei time.
* Type /fetch_article in any text channel to get the news headlines for the day immeadiately.

## Project Structure

```
bot
├── cogs                    # Contains all the Discord commands organized into separate files
├── scraper                 # Contains scraper functions for extracting data from websites
└── bot.py                  # Main entry point for the bot application
```

## Contributing
Contributions are always welcome! Please feel free to submit a pull request if you have any improvements or new features to add. If you encounter any issues or bugs, please open an issue in the repository.

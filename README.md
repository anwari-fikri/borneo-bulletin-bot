# Preview
![demo](https://github.com/anwari-fikri/borneo-bulletin-bot/assets/50336496/7f430d7b-39c2-43ef-b0e7-f5a729358bfc)


# Borneo Bulletin News Bot
This is a Python-based Discord bot that scrapes the Borneo Bulletin website and posts the news articles in a Discord channel. This bot is designed to provide daily news updates to users in an easy and efficient way.

## Features
- ✅ Scrapes the articles using Python and Selenium.
- ✅ Retrieves the articles for the day from selected categories. (Currently Headlines and National only)
- ✅ Posts the news articles in a Discord channel.
- ✅ Includes a hyperlink to the original article.
- ✅ Runs automatically at a specific time every day.

## Usage
* Invite the Borneo Bulletin Bot to your Discord server.
* Type /toggle_scheduled_national in any text channel to get a daily national news at the 9am Brunei time.
* Type /fetch_national in any text channel to get the national news for the day immediately.

## Project Structure

```
bot
├── cogs                    # Contains all the Discord commands organized into separate files
├── scraper                 # Contains scraper functions for extracting data from websites
└── bot.py                  # Main entry point for the bot application
```

## Contributing
Contributions are always welcome! Please feel free to submit a pull request if you have any improvements or new features to add. If you encounter any issues or bugs, please open an issue in the repository.

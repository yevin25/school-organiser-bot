# run_once.py
# The version of the bot that GitHub runs every 30 minutes.
#
# bot.py stays switched on and waits for messages. This file does one
# quick visit instead: read any new messages, reply, send any summary or
# warning that is due, then stop.
#
# GitHub runs it in two parts:
#   python run_once.py           read messages, reply, update tasks.json
#   python run_once.py confirm   tell Telegram those messages are dealt with
# In between, GitHub saves tasks.json. Doing "confirm" last means that if
# the save fails, the messages are simply handled again on the next visit.

import os
import sys

import bot
from storage import PROJECT_FOLDER

# A scrap of paper for remembering the last message between the two parts.
LAST_MESSAGE_FILE = os.path.join(PROJECT_FOLDER, ".last_update_id")


def read_and_reply():
    """Part one: handle new messages and send anything that is due."""
    updates = bot.call_telegram("getUpdates", {"timeout": 0, "allowed_updates": ["message"]})
    if updates is None:
        print("Could not get messages from Telegram.")
        sys.exit(1)

    handled = 0
    for update in updates:
        message = update.get("message")
        # Ignore everyone except you.
        if message is not None and str(message["chat"]["id"]) == bot.MY_CHAT_ID:
            bot.reply_to(message)
            handled = handled + 1

    # Note down the last message so part two can confirm it.
    if updates:
        with open(LAST_MESSAGE_FILE, "w") as file:
            file.write(str(updates[-1]["update_id"]))

    bot.send_scheduled_messages()
    print("Messages handled: " + str(handled))


def confirm():
    """Part two: tell Telegram the messages are done, so it forgets them."""
    if not os.path.exists(LAST_MESSAGE_FILE):
        print("No messages to confirm.")
        return

    with open(LAST_MESSAGE_FILE) as file:
        last_update_id = int(file.read())

    result = bot.call_telegram("getUpdates", {"offset": last_update_id + 1, "limit": 1, "timeout": 0})
    if result is None:
        print("Could not confirm the messages with Telegram.")
        sys.exit(1)

    os.remove(LAST_MESSAGE_FILE)
    print("Messages confirmed.")


if __name__ == "__main__":
    if not bot.BOT_TOKEN or not bot.MY_CHAT_ID:
        print("The bot token or chat ID is missing. Check the GitHub Secrets.")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "confirm":
        confirm()
    else:
        read_and_reply()

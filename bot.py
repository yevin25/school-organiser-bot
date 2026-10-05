# bot.py
# The school organiser bot.
# This file does the talking to Telegram: it collects your messages and
# sends the replies. The thinking happens in commands.py.

import os
import time
import traceback

import requests
from dotenv import load_dotenv

from commands import handle_message
from reminders import collect_due_messages
from storage import load_data, save_data
from understand import now_in_melbourne

# Find the .env file that sits next to this file and read the secrets from it.
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(PROJECT_FOLDER, ".env")
load_dotenv(ENV_FILE)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
MY_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Every request to Telegram goes to this address.
# It contains the token, so we never print it.
API_URL = "https://api.telegram.org/bot" + BOT_TOKEN


def call_telegram(method, params, wait_seconds=10):
    """Ask Telegram to do something, for example "sendMessage".

    Returns Telegram's answer, or None if something went wrong.
    """
    try:
        response = requests.post(API_URL + "/" + method, json=params, timeout=wait_seconds)
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        # Only print the kind of error. The full error text includes the
        # web address, and the web address includes the secret token.
        print("Could not reach Telegram (" + type(error).__name__ + ").")
        return None

    if not data.get("ok"):
        print("Telegram refused the request: " + str(data.get("description")))
        return None

    return data["result"]


def get_new_messages(next_update_id):
    """Wait up to 30 seconds for new messages and return them as a list."""
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if next_update_id is not None:
        # This tells Telegram which messages we have already handled.
        params["offset"] = next_update_id
    return call_telegram("getUpdates", params, wait_seconds=40)


def send_message(text):
    """Send a message to you, and only you. Returns True if it was sent."""
    # Telegram allows about 4,000 characters per message, so a very long
    # list is sent as several messages.
    pieces = []
    piece = ""
    for line in text.split("\n"):
        if piece and len(piece) + len(line) + 1 > 4000:
            pieces.append(piece)
            piece = ""
        piece = piece + "\n" + line if piece else line
    if piece:
        pieces.append(piece)

    for piece in pieces:
        result = call_telegram("sendMessage", {"chat_id": MY_CHAT_ID, "text": piece})
        if result is None:
            return False
    return True


def send_scheduled_messages():
    """Send the morning summary, warnings or Sunday overview if one is due."""
    data = load_data()
    messages = collect_due_messages(data, now_in_melbourne())
    for message in messages:
        if not send_message(message):
            # Sending failed, so do not record it as sent. The bot will
            # try again the next time it checks.
            return
    if messages:
        save_data(data)


def reply_to(message):
    """Work out the reply to one of your messages and send it."""
    text = message.get("text")
    if text is None:
        send_message("I can only read text messages.")
        return

    try:
        reply = handle_message(text)
    except Exception:
        # Print the full error so it can be fixed, and tell you in
        # Telegram that something broke.
        traceback.print_exc()
        reply = "Something went wrong on my side, so I could not handle that message."

    send_message(reply)


def main():
    # Check the secrets are filled in before starting.
    if not BOT_TOKEN:
        print("The bot token is missing. Paste it into the .env file first.")
        return
    if not MY_CHAT_ID:
        print("Your chat ID is missing. Run find_chat_id.py first.")
        return

    # Ask Telegram who the bot is. This also checks the token works.
    bot_info = call_telegram("getMe", {})
    if bot_info is None:
        print("Could not log in. Check the token in the .env file.")
        return

    print("Bot is running as @" + bot_info["username"] + ".")
    print("Press Control + C to stop it.")

    next_update_id = None

    # Keep checking for new messages until you stop the bot.
    while True:
        # About every 30 seconds, check if a summary or warning is due.
        try:
            send_scheduled_messages()
        except Exception:
            traceback.print_exc()

        updates = get_new_messages(next_update_id)

        if updates is None:
            # Something went wrong (maybe the wifi dropped). Wait, then retry.
            time.sleep(5)
            continue

        for update in updates:
            next_update_id = update["update_id"] + 1

            message = update.get("message")
            if message is None:
                continue

            # Ignore everyone except you.
            if str(message["chat"]["id"]) != MY_CHAT_ID:
                continue

            reply_to(message)


# This part only runs when you start this file directly.
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot stopped.")

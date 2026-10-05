# find_chat_id.py
# A one-time helper. It finds your Telegram chat ID and saves it in .env.
#
# How to use it:
#   1. Open Telegram and send your bot any message, for example "hello".
#   2. Run this file.

from dotenv import set_key

from bot import BOT_TOKEN, ENV_FILE, call_telegram


def main():
    if not BOT_TOKEN:
        print("The bot token is missing. Paste it into the .env file first.")
        return

    # Ask Telegram for the messages people have sent to the bot.
    updates = call_telegram("getUpdates", {})
    if updates is None:
        print("Could not log in. Check the token in the .env file.")
        return

    # Keep only direct messages (not groups).
    messages = []
    for update in updates:
        message = update.get("message")
        if message is not None and message["chat"]["type"] == "private":
            messages.append(message)

    if not messages:
        print("No messages found yet.")
        print("Open Telegram, send your bot a message, then run this again.")
        return

    # Use the newest message.
    chat = messages[-1]["chat"]
    chat_id = str(chat["id"])
    name = chat.get("first_name", "someone")

    # Write the chat ID into .env without showing it on screen.
    set_key(ENV_FILE, "TELEGRAM_CHAT_ID", chat_id, quote_mode="never")

    print("Found a message from " + name + ".")
    print("Saved that chat ID to .env.")
    print("If " + name + " is not you, tell Claude before going further.")


if __name__ == "__main__":
    main()

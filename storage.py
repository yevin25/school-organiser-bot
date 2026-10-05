# storage.py
# Reads and writes tasks.json, the file where your tasks are kept.

import json
import os

# tasks.json sits in the same folder as this file.
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(PROJECT_FOLDER, "tasks.json")


def load_data():
    """Read everything the bot remembers from tasks.json."""
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, encoding="utf-8") as file:
            data = json.load(file)
    else:
        data = {}  # first run: nothing saved yet

    # Fill in anything that is missing with an empty starting value.
    data.setdefault("tasks", [])  # your tasks
    data.setdefault("waiting_for_date", None)  # a task the bot asked "when is it due?" about
    data.setdefault("last_sent", {})  # the days the automatic summaries were last sent
    return data


def save_data(data):
    """Write everything the bot remembers into tasks.json."""
    # Write to a spare file first, then swap it in. This way tasks.json
    # is never left half-written if the laptop is closed at a bad moment.
    spare_file = TASKS_FILE + ".tmp"
    with open(spare_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
    os.replace(spare_file, TASKS_FILE)

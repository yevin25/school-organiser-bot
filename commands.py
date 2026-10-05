# commands.py
# Decides what the bot replies to each message:
# add a task, list, done, delete or help.

from datetime import date

from reminders import build_morning_summary, build_week_ahead, warnings_not_needed
from storage import load_data, save_data
from understand import (
    find_date, how_soon, is_only_a_date, nice_date, today_in_melbourne, understand_task,
)

HELP_TEXT = (
    "Here is what I can do:\n"
    "\n"
    "Add a task: just tell me, for example\n"
    "  maths SAC next Thursday\n"
    "  english essay draft due 14 Oct\n"
    "\n"
    "list - show all your tasks\n"
    "done maths SAC - tick off a finished task (it leaves the list)\n"
    "delete maths SAC - remove a task you no longer need\n"
    "\n"
    "For done and delete you can also use the number from the list, like \"done 2\".\n"
    "\n"
    "morning - show the morning summary now\n"
    "week - show the week-ahead overview now\n"
    "\n"
    "I also message you by myself: a summary at 7am on school days, "
    "a warning 7 days and 2 days before each SAC or test, "
    "and a week-ahead overview at 6pm on Sundays."
)


def describe(task, today):
    """Two lines describing one task."""
    due = date.fromisoformat(task["due"])
    details = nice_date(due, today) + " · " + how_soon(due, today)
    details = details + " · " + task["subject"] + " · " + task["type"]
    return task["name"] + "\n    " + details


def due_date_of(task):
    return task["due"]


def put_in_order(tasks):
    """Sort tasks so the one due soonest comes first."""
    return sorted(tasks, key=due_date_of)


def add_task(data, name, subject, task_type, due, today):
    """Save a new task and return the bot's reply."""
    for task in data["tasks"]:
        if task["name"].lower() == name.lower() and task["due"] == due.isoformat():
            return "You already have that one:\n" + describe(task, today)

    task = {
        "name": name,
        "subject": subject if subject is not None else "General",
        "type": task_type,
        "due": due.isoformat(),
    }
    if task_type in ("SAC", "test"):
        # Remember which warnings there is no point sending for this one.
        task["warned"] = warnings_not_needed(task_type, due, today)
    data["tasks"].append(task)
    data["tasks"] = put_in_order(data["tasks"])

    reply = "Saved:\n" + describe(task, today)
    if due < today:
        reply = reply + "\n\nHeads up: that date has already passed."
    return reply


def list_tasks(data, today):
    """Return the full task list as text."""
    tasks = data["tasks"]
    if not tasks:
        return "You have no tasks. Tell me one, for example \"maths SAC next Thursday\"."

    lines = ["YOUR TASKS"]
    for position, task in enumerate(tasks):
        lines.append(str(position + 1) + ". " + describe(task, today))
    return "\n".join(lines)


def find_tasks(tasks, search):
    """Find tasks by list number or by name. Returns their positions."""
    # A number means the number shown in the list.
    if search.isdigit():
        position = int(search) - 1
        if 0 <= position < len(tasks):
            return [position]
        return []

    # Otherwise every word you typed must appear in the task.
    wanted_words = search.lower().split()
    positions = []
    for position, task in enumerate(tasks):
        searchable = (task["name"] + " " + task["subject"] + " " + task["type"]).lower()
        if all(word in searchable for word in wanted_words):
            positions.append(position)
    return positions


def choose_one(tasks, positions, search, command, today):
    """Check exactly one task matched. Returns a reply if something is wrong."""
    if not positions:
        return "I could not find a task matching \"" + search + "\". Say \"list\" to see your tasks."
    if len(positions) > 1:
        lines = ["More than one task matches \"" + search + "\":"]
        for position in positions:
            lines.append(str(position + 1) + ". " + describe(tasks[position], today))
        lines.append("")
        lines.append("Tell me the number, for example \"" + command + " " + str(positions[0] + 1) + "\".")
        return "\n".join(lines)
    return None


def mark_done(data, search, today):
    """Tick a finished task off, which takes it off the list."""
    if not search:
        return "Which task? For example \"done maths SAC\" or \"done 2\"."

    tasks = data["tasks"]
    positions = find_tasks(tasks, search)
    problem = choose_one(tasks, positions, search, "done", today)
    if problem is not None:
        return problem

    task = tasks.pop(positions[0])
    return "Done: " + task["name"] + " ✅\nNice work. I took it off your list."


def delete_task(data, search, today):
    """Remove a task and return the bot's reply."""
    if not search:
        return "Which task? For example \"delete maths SAC\" or \"delete 2\"."

    tasks = data["tasks"]
    positions = find_tasks(tasks, search)
    problem = choose_one(tasks, positions, search, "delete", today)
    if problem is not None:
        return problem

    task = tasks.pop(positions[0])
    return "Deleted: " + task["name"]


def decide_reply(data, text, today):
    """Look at a message and work out the reply."""
    # Phones type curly apostrophes (’). Swap them for plain ones (').
    text = text.replace("’", "'").replace("‘", "'").strip()
    lower = text.lower()
    first_word = lower.split()[0] if lower else ""
    rest = text[len(first_word):].strip()

    # If the bot asked "when is it due?", this message might be the answer.
    note = ""
    waiting = data["waiting_for_date"]
    if waiting is not None:
        data["waiting_for_date"] = None
        if lower in ("cancel", "no", "never mind", "nevermind"):
            return "OK, I did not save \"" + waiting["name"] + "\"."
        if is_only_a_date(text, today):
            due, leftover = find_date(text, today)
            return add_task(data, waiting["name"], waiting["subject"], waiting["type"], due, today)
        # It was not a date, so treat it as a brand new message.
        note = "I did not save \"" + waiting["name"] + "\" because it had no due date.\n\n"

    if lower in ("help", "/help", "/start"):
        return note + HELP_TEXT

    if first_word in ("list", "/list", "tasks"):
        return note + list_tasks(data, today)

    if lower in ("morning", "summary"):
        return note + build_morning_summary(data["tasks"], today)

    if lower in ("week", "week ahead"):
        return note + build_week_ahead(data["tasks"], today)

    if first_word in ("done", "/done"):
        return note + mark_done(data, rest, today)

    if first_word in ("delete", "/delete", "remove"):
        return note + delete_task(data, rest, today)

    # A question like "what's due tomorrow?" is not a task. Show the list.
    question_words = ("what", "what's", "whats", "when", "when's", "whens", "which", "how")
    if text.endswith("?") or first_word in question_words:
        return (
            note + "That looks like a question, so I did not save it as a task.\n\n"
            + list_tasks(data, today)
        )

    # Anything else is a new task.
    details = understand_task(text, today)

    nothing_recognised = (
        details["due"] is None and details["subject"] is None and details["type"] == "other"
    )
    if details["name"] == "" or nothing_recognised:
        return note + "I'm not sure what you mean.\n\n" + HELP_TEXT

    if details["due"] is None:
        # The task has no date, so remember it and ask.
        data["waiting_for_date"] = {
            "name": details["name"],
            "subject": details["subject"],
            "type": details["type"],
        }
        return (
            note + "When is \"" + details["name"] + "\" due?\n"
            "Tell me a day like \"Friday\", \"next Wednesday\" or \"14 Oct\". "
            "Or say \"cancel\"."
        )

    return note + add_task(
        data, details["name"], details["subject"], details["type"], details["due"], today
    )


def handle_message(text):
    """Work out the reply to a message and save any changes."""
    data = load_data()
    reply = decide_reply(data, text, today_in_melbourne())
    save_data(data)
    return reply

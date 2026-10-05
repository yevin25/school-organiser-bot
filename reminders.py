# reminders.py
# The messages the bot sends by itself:
#   - a morning summary at 7am on school days (Monday to Friday)
#   - a warning 7 days and 2 days before every SAC and test
#   - a week-ahead overview at 6pm on Sundays
#
# To preview what would be sent at a certain time, without sending anything:
#   .venv/bin/python reminders.py 2026-10-08 07:00

import sys
from datetime import date, datetime, timedelta

from storage import load_data
from understand import MELBOURNE, how_soon, nice_date

# How many days before a SAC or test the bot warns you.
WARNING_DAYS = [7, 2]

# When each message is sent, in 24-hour Melbourne time. Each one has a
# "from" hour and an "until" hour. If the bot was not running at the exact
# time, it still sends the message when it next runs inside these hours.
MORNING_FROM, MORNING_UNTIL = 7, 12  # 7am to midday, Monday to Friday
SUNDAY_FROM, SUNDAY_UNTIL = 18, 22   # 6pm to 10pm, Sundays
WARNINGS_FROM, WARNINGS_UNTIL = 7, 22  # 7am to 10pm, every day


def due_date_of(task):
    return date.fromisoformat(task["due"])


def is_sac_or_test(task):
    return task["type"] in ("SAC", "test")


def label(task):
    """The task name, with [SAC] or [test] added if the name does not say so."""
    if is_sac_or_test(task) and task["type"].lower() not in task["name"].lower():
        return task["name"] + " [" + task["type"] + "]"
    return task["name"]


def add_section(lines, heading, items, empty_text):
    """Add a heading and its list of tasks to a message."""
    if items:
        lines.append("")
        lines.append(heading)
        lines.extend(items)
    elif empty_text:
        # Nothing in this section, so say so in one line instead.
        lines.append("")
        lines.append(empty_text)


def build_morning_summary(tasks, today):
    """The 7am message: due today, due this week, upcoming SACs and tests."""
    this_sunday = today + timedelta(days=6 - today.weekday())

    overdue = []
    due_today = []
    this_week = []
    sacs_and_tests = []
    for task in sorted(tasks, key=due_date_of):
        due = due_date_of(task)
        if due < today:
            overdue.append("- " + label(task) + " (" + nice_date(due, today) + ", " + how_soon(due, today) + ")")
        elif due == today:
            due_today.append("- " + label(task))
        elif due <= this_sunday:
            this_week.append("- " + nice_date(due, today) + ": " + label(task))
        if due > today and is_sac_or_test(task):
            sacs_and_tests.append("- " + nice_date(due, today) + " (" + how_soon(due, today) + "): " + task["name"])

    lines = ["Good morning! " + today.strftime("%A") + " " + str(today.day) + " " + today.strftime("%B")]
    add_section(lines, "OVERDUE", overdue, None)
    add_section(lines, "DUE TODAY", due_today, "Nothing due today.")
    add_section(lines, "DUE LATER THIS WEEK", this_week, "Nothing else due this week.")
    add_section(lines, "UPCOMING SACS AND TESTS", sacs_and_tests, "No SACs or tests coming up.")
    return "\n".join(lines)


def build_week_ahead(tasks, today):
    """The Sunday message: everything due next Monday to Sunday, day by day."""
    monday = today + timedelta(days=7 - today.weekday())
    sunday = monday + timedelta(days=6)

    overdue = []
    week = []
    later_sacs_and_tests = []
    last_day_shown = None
    for task in sorted(tasks, key=due_date_of):
        due = due_date_of(task)
        if due < today:
            overdue.append("- " + label(task) + " (" + nice_date(due, today) + ", " + how_soon(due, today) + ")")
        elif monday <= due <= sunday:
            # Show the day as a small heading, once for each day.
            if due != last_day_shown:
                week.append(nice_date(due, today))
                last_day_shown = due
            week.append("- " + label(task))
        elif due > sunday and is_sac_or_test(task):
            later_sacs_and_tests.append("- " + nice_date(due, today) + " (" + how_soon(due, today) + "): " + task["name"])

    lines = ["WEEK AHEAD: " + nice_date(monday, today) + " to " + nice_date(sunday, today)]
    add_section(lines, "DUE THAT WEEK", week, "Nothing due that week.")
    add_section(lines, "SACS AND TESTS AFTER THAT", later_sacs_and_tests, None)
    add_section(lines, "STILL OVERDUE", overdue, None)
    return "\n".join(lines)


def warnings_not_needed(task_type, due, today):
    """For a brand new task: which warnings to skip because that day has
    already come. For example a SAC added 5 days ahead skips the 7-day warning."""
    if task_type not in ("SAC", "test"):
        return []
    days_left = (due - today).days
    return [days for days in WARNING_DAYS if days_left <= days]


def check_warning(task, today):
    """Return a warning message if this SAC or test needs one today."""
    if not is_sac_or_test(task):
        return None

    due = due_date_of(task)
    days_left = (due - today).days
    already_warned = task.setdefault("warned", [])
    when = how_soon(due, today) + " (" + nice_date(due, today) + ")"

    # The 2-day warning. Also covers the last two days if it was missed.
    if 0 <= days_left <= 2 and 2 not in already_warned:
        already_warned.append(2)
        if 7 not in already_warned:
            already_warned.append(7)
        return "⚠️ " + task["name"] + " is " + when + ". Time for final revision."

    # The 7-day warning. Also covers days 6 to 3 if it was missed.
    if 2 < days_left <= 7 and 7 not in already_warned:
        already_warned.append(7)
        return "⚠️ Heads up: " + task["name"] + " is " + when + ". Start revising."

    return None


def collect_due_messages(data, now):
    """Work out which automatic messages should be sent right now.

    This also notes down what has been sent, inside data, so nothing is
    sent twice. The caller saves data after the messages go out.
    """
    today = now.date()
    today_text = today.isoformat()
    tasks = data["tasks"]
    last_sent = data["last_sent"]
    messages = []

    # Morning summary: Monday (0) to Friday (4), once a day.
    is_school_day = today.weekday() <= 4
    if is_school_day and MORNING_FROM <= now.hour < MORNING_UNTIL and last_sent.get("morning") != today_text:
        messages.append(build_morning_summary(tasks, today))
        last_sent["morning"] = today_text

    # Week ahead: Sunday (6), once.
    is_sunday = today.weekday() == 6
    if is_sunday and SUNDAY_FROM <= now.hour < SUNDAY_UNTIL and last_sent.get("week_ahead") != today_text:
        messages.append(build_week_ahead(tasks, today))
        last_sent["week_ahead"] = today_text

    # SAC and test warnings: every day, weekends too.
    if WARNINGS_FROM <= now.hour < WARNINGS_UNTIL:
        for task in tasks:
            warning = check_warning(task, today)
            if warning is not None:
                messages.append(warning)

    return messages


# Preview mode. This part only runs when you start this file directly.
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Give a date and a time, for example:")
        print("  .venv/bin/python reminders.py 2026-10-08 07:00")
        sys.exit()

    try:
        pretend_now = datetime.strptime(sys.argv[1] + " " + sys.argv[2], "%Y-%m-%d %H:%M")
    except ValueError:
        print("I could not read that. Write the date as 2026-10-08 and the time as 07:00.")
        sys.exit()
    pretend_now = pretend_now.replace(tzinfo=MELBOURNE)

    data = load_data()
    data["last_sent"] = {}  # pretend no summaries have been sent yet
    messages = collect_due_messages(data, pretend_now)

    print("Preview for " + pretend_now.strftime("%A %d %B %Y, %I:%M %p") + " Melbourne time.")
    print("Nothing is sent and nothing is saved.")
    if not messages:
        print("\nThe bot would not send anything at that time.")
    for message in messages:
        print("\n----- the bot would send -----")
        print(message)

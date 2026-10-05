# understand.py
# Turns a sentence like "maths SAC next Thursday" into task details:
# the name, the subject, the type and the due date.
# It also knows the Melbourne time and turns dates back into friendly words.

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# Melbourne time. This handles daylight saving by itself.
MELBOURNE = ZoneInfo("Australia/Melbourne")

# Your subjects, and the words that mean each one.
# You can add your own subjects or nicknames here.
SUBJECTS = {
    "Maths": ["maths", "math", "mathematics", "methods", "specialist"],
    "English": ["english", "eng", "literature", "lit"],
    "Science": ["science", "sci"],
    "Biology": ["biology", "bio"],
    "Chemistry": ["chemistry", "chem"],
    "Physics": ["physics"],
    "Psychology": ["psychology", "psych"],
    "Humanities": ["humanities", "hums"],
    "History": ["history"],
    "Geography": ["geography", "geo"],
    "Civics": ["civics"],
    "Commerce": ["commerce"],
    "Economics": ["economics", "eco", "econ"],
    "Business": ["business"],
    "Legal Studies": ["legal studies", "legal"],
    "Accounting": ["accounting"],
    "PE": ["pe", "phys ed", "physical education", "sport"],
    "Health": ["health"],
    "Art": ["art", "visual arts"],
    "Viscom": ["viscom", "vcd", "visual communication"],
    "Music": ["music"],
    "Drama": ["drama"],
    "Media": ["media"],
    "Digital Tech": ["digital tech", "digitech", "digi tech", "computing", "coding"],
    "Design Tech": ["design tech", "woodwork", "textiles", "food tech"],
    "French": ["french"],
    "Japanese": ["japanese"],
    "Chinese": ["chinese", "mandarin"],
    "Italian": ["italian"],
    "German": ["german"],
    "Indonesian": ["indonesian"],
    "Spanish": ["spanish"],
    "Religion": ["religion", "rel ed"],
}

# The task types, and the words that mean each one.
# The order matters: the first type that matches wins, so "SAC" beats "test".
TYPES = {
    "SAC": ["sac", "sacs"],
    "test": ["test", "tests", "exam", "exams", "quiz", "quizzes"],
    "homework": [
        "homework", "hw", "essay", "draft", "worksheet", "assignment",
        "project", "exercise", "exercises", "questions", "reading", "report",
    ],
}

# Little joining words that are not part of a task name.
SMALL_WORDS = ["due", "on", "by", "for", "is", "the"]

# Month and weekday names. We look them up by their first three letters.
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

# Search patterns. These describe what a month name or weekday name looks
# like, including short versions such as "oct" or "thurs".
MONTH_PATTERN = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
WEEKDAY_PATTERN = (
    r"(mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?"
    r"|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
)


def now_in_melbourne():
    """The date and time in Melbourne right now, wherever the bot is running."""
    return datetime.now(MELBOURNE)


def today_in_melbourne():
    """Today's date in Melbourne, wherever the bot is running."""
    return now_in_melbourne().date()


def nice_date(due, today):
    """Turn a date into words like "Thu 15 Oct"."""
    words = due.strftime("%a") + " " + str(due.day) + " " + due.strftime("%b")
    if due.year != today.year:
        words = words + " " + str(due.year)
    return words


def how_soon(due, today):
    """Turn a date into words like "in 3 days" or "2 days overdue"."""
    days = (due - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days > 1:
        return "in " + str(days) + " days"
    if days == -1:
        return "1 day overdue"
    return str(-days) + " days overdue"


def build_date(day, month, year, today):
    """Make a date from numbers. Returns None if it is not a real date."""
    try:
        if year is None:
            # No year given. Use this year, or next year if it has passed.
            due = date(today.year, month, day)
            if due < today:
                due = date(today.year + 1, month, day)
            return due
        if year < 100:
            year = year + 2000  # "26" means 2026
        return date(year, month, day)
    except ValueError:
        return None  # for example 31 February


# Each "find" function below looks for one way of writing a date.
# It returns the date plus where the date words start and end in the
# sentence, or None if it found nothing.

def find_slash_date(text, today):
    """Dates like 14/10 or 14/10/2026 (day first, the Australian way)."""
    match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?\b", text)
    if match is None:
        return None
    year = int(match.group(3)) if match.group(3) else None
    due = build_date(int(match.group(1)), int(match.group(2)), year, today)
    if due is None:
        return None
    return due, match.start(), match.end()


def find_day_then_month(text, today):
    """Dates like "14 Oct", "14th October" or "14th of October 2026"."""
    pattern = r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + MONTH_PATTERN + r"\b(?:\s+(\d{4}))?"
    match = re.search(pattern, text)
    if match is None:
        return None
    month = MONTHS[match.group(2)[:3]]
    year = int(match.group(3)) if match.group(3) else None
    due = build_date(int(match.group(1)), month, year, today)
    if due is None:
        return None
    return due, match.start(), match.end()


def find_month_then_day(text, today):
    """Dates like "Oct 14" or "October 14th, 2026"."""
    pattern = r"\b" + MONTH_PATTERN + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4}))?"
    match = re.search(pattern, text)
    if match is None:
        return None
    month = MONTHS[match.group(1)[:3]]
    year = int(match.group(3)) if match.group(3) else None
    due = build_date(int(match.group(2)), month, year, today)
    if due is None:
        return None
    return due, match.start(), match.end()


def find_relative_day(text, today):
    """Words like "today", "tomorrow" or "in 3 days"."""
    match = re.search(r"\b(today|tonight)\b", text)
    if match is not None:
        return today, match.start(), match.end()

    match = re.search(r"\b(tomorrow|tmrw|tmr)\b", text)
    if match is not None:
        return today + timedelta(days=1), match.start(), match.end()

    match = re.search(r"\bin\s+(\d+|a|an)\s+(day|week)s?\b", text)
    if match is not None:
        amount = 1 if match.group(1) in ("a", "an") else int(match.group(1))
        if match.group(2) == "week":
            amount = amount * 7
        return today + timedelta(days=amount), match.start(), match.end()

    return None


def find_weekday(text, today):
    """Weekdays like "Friday", "next Thursday" or "Thursday next week"."""
    pattern = r"\b(?:(next|this)\s+)?" + WEEKDAY_PATTERN + r"\b(\s+next\s+week\b)?"
    match = re.search(pattern, text)
    if match is None:
        return None

    wanted_day = WEEKDAYS[match.group(2)[:3]]
    said_next = match.group(1) == "next" or match.group(3) is not None

    if said_next:
        # "next Thursday" means the Thursday of next week.
        next_monday = today + timedelta(days=7 - today.weekday())
        due = next_monday + timedelta(days=wanted_day)
    else:
        # "Thursday" means the first Thursday after today.
        days_ahead = (wanted_day - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        due = today + timedelta(days=days_ahead)

    return due, match.start(), match.end()


def remove_small_words_from_end(text):
    """Turn "english essay due on" into "english essay"."""
    words = text.split()
    while words and words[-1].lower().strip(",.:;-") in SMALL_WORDS:
        words.pop()
    return " ".join(words)


def find_date(text, today):
    """Look for a due date in a sentence.

    Returns the date and the sentence with the date words taken out.
    If there is no date, returns None and the sentence unchanged.
    """
    lower = text.lower()
    finders = [
        find_slash_date,
        find_day_then_month,
        find_month_then_day,
        find_relative_day,
        find_weekday,
    ]
    for finder in finders:
        found = finder(lower, today)
        if found is not None:
            due, start, end = found
            before = remove_small_words_from_end(text[:start])
            after = text[end:]
            return due, before + " " + after
    return None, text


def find_subject(text):
    """Work out the subject. Returns None if no subject word is found."""
    lower = text.lower()
    best_subject = None
    best_position = len(lower)
    # If two subjects are mentioned, pick the one that comes first.
    for subject, nicknames in SUBJECTS.items():
        for nickname in nicknames:
            match = re.search(r"\b" + re.escape(nickname) + r"\b", lower)
            if match is not None and match.start() < best_position:
                best_subject = subject
                best_position = match.start()
    return best_subject


def find_type(text):
    """Work out the type: SAC, test, homework or other."""
    lower = text.lower()
    for task_type, type_words in TYPES.items():
        for word in type_words:
            if re.search(r"\b" + re.escape(word) + r"\b", lower):
                return task_type
    return "other"


def tidy_name(text):
    """Clean up what is left of the sentence so it makes a neat task name."""
    text = re.sub(r"\b(next|this)\s+week\b", " ", text, flags=re.IGNORECASE)
    text = " ".join(text.split())  # squash double spaces
    text = text.strip(" ,.:;-!?")
    text = remove_small_words_from_end(text)
    text = re.sub(r"\bsac\b", "SAC", text, flags=re.IGNORECASE)
    if text:
        text = text[0].upper() + text[1:]
    return text


def is_only_a_date(text, today):
    """True if the message is just a date, like "Friday" or "it's due 14 Oct"."""
    due, leftover = find_date(text, today)
    if due is None:
        return False
    ignored = SMALL_WORDS + ["it", "its", "it's"]
    for word in re.findall(r"[a-z']+", leftover.lower()):
        if word not in ignored:
            return False
    return True


def understand_task(text, today):
    """Pull the task details out of a sentence."""
    # Allow "add maths SAC ..." as well as plain "maths SAC ...".
    text = re.sub(r"^\s*add\s+", "", text, flags=re.IGNORECASE)

    due, leftover = find_date(text, today)
    return {
        "name": tidy_name(leftover),
        "subject": find_subject(leftover),
        "type": find_type(leftover),
        "due": due,
    }

from datetime import datetime, timedelta


def answer_time_question(message: str):
    text = message.strip().lower()
    now = datetime.now()

    if not text:
        return None

    if (
        "what time is it" in text
        or "what time it is" in text
        or "what's the time" in text
        or "whats the time" in text
        or "current time" in text
    ):
        return now.strftime("It is currently %-I:%M %p.")

    if (
        "what day is it today" in text
        or "what day is today" in text
        or "what date is it" in text
        or "what is today's date" in text
        or "what is todays date" in text
    ):
        return now.strftime(
            "Today is %A, %B %-d, %Y."
        )

    if "tomorrow" in text:
        tomorrow = now + timedelta(days=1)
        return tomorrow.strftime(
            "Tomorrow is %A, %B %-d, %Y."
        )

    if "yesterday" in text:
        yesterday = now - timedelta(days=1)
        return yesterday.strftime(
            "Yesterday was %A, %B %-d, %Y."
        )

    return None

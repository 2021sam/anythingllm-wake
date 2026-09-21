from dataclasses import dataclass
from typing import Optional
import re


DEFAULT_LOCATION = "Blackhawk"


@dataclass
class CurrentRequest:
    domain: Optional[str] = None
    intent: Optional[str] = None
    location: Optional[str] = None
    date: Optional[str] = None
    destination: Optional[str] = None
    device_key: Optional[str] = None

    def clear(self):
        self.domain = None
        self.intent = None
        self.location = None
        self.date = None
        self.destination = None
        self.device_key = None

    def snapshot(self):
        return {
            "domain": self.domain,
            "intent": self.intent,
            "location": self.location,
            "date": self.date,
            "destination": self.destination,
            "device_key": self.device_key,
        }

    def canonical_text(self):
        if self.domain == "weather":
            if self.intent == "temperature":
                text = (
                    f"What is the temperature in "
                    f"{self.location or DEFAULT_LOCATION}"
                )

                if self.date in ("today", "tomorrow"):
                    text += f" {self.date}"

                return text + "?"

            if self.intent == "precipitation":
                text = (
                    f"Will it rain in "
                    f"{self.location or DEFAULT_LOCATION}"
                )

                if self.date in ("today", "tomorrow"):
                    text += f" {self.date}"

                return text + "?"

        if (
            self.domain == "time"
            and self.intent == "current_time"
        ):
            return "What time is it?"

        return None


def _clean_place(text):
    text = text.strip()
    text = re.sub(r"[?.!,]+$", "", text)
    return text.strip()


def _explicit_weather_location(message):
    match = re.search(
        r"\b(?:temperature|weather|forecast)"
        r"(?:\s+(?:in|for))\s+"
        r"(.+?)(?:\s+(?:today|tomorrow|tonight))?"
        r"[?.!]*$",
        message,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return _clean_place(match.group(1))


def _what_about_value(message):
    match = re.fullmatch(
        r"\s*(?:what|how)\s+about\s+(.+?)\s*[?.!]*\s*",
        message,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return _clean_place(match.group(1))


def update_current_request(current, message):
    text = message.strip()
    lower = text.lower()

    if not text:
        return False

    # Explicit switch to current-time request.
    if (
        "what time is it" in lower
        or "what time it is" in lower
        or "what's the time" in lower
        or "whats the time" in lower
        or "current time" in lower
    ):
        current.clear()
        current.domain = "time"
        current.intent = "current_time"
        return True

    # Explicit temperature request.
    if (
        "temperature" in lower
        or "how hot" in lower
        or "how cold" in lower
    ):
        location = _explicit_weather_location(text)

        current.clear()
        current.domain = "weather"
        current.intent = "temperature"
        current.location = location or DEFAULT_LOCATION
        current.date = (
            "tomorrow"
            if "tomorrow" in lower
            else "today"
        )
        return True

    # Explicit precipitation request.
    if (
        "will it rain" in lower
        or "going to rain" in lower
        or "chance of rain" in lower
    ):
        if current.domain != "weather":
            current.clear()
            current.domain = "weather"
            current.location = DEFAULT_LOCATION
            current.date = "today"

        current.intent = "precipitation"

        if "tomorrow" in lower:
            current.date = "tomorrow"

        return True

    # Contextual edit: "What about X?"
    value = _what_about_value(text)

    if value is not None and current.domain == "weather":
        value_lower = value.lower()

        if value_lower == "tomorrow":
            current.date = "tomorrow"
            return True

        if value_lower in ("today", "tonight"):
            current.date = "today"
            return True

        # Nothing else changed, so replace only location.
        current.location = value
        return True

    return False

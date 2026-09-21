import re


ACTIVE = "active"
PHYSICAL = "physical"


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return " ".join(text.split())


def wants_light_control_explanation(message: str) -> bool:
    """
    Detect a question about how Jarvis can identify/control lights.

    This only requests an explanation of the available methods.
    It must never operate a light by itself.
    """
    text = _normalize(message)

    if not any(
        word in text
        for word in (
            "light",
            "lights",
            "dimmer",
            "dimmers",
            "switch",
            "switches",
        )
    ):
        return False

    patterns = (
        r"\bhow (?:do|can|would) you control\b",
        r"\bhow (?:do|can|would) you identify\b",
        r"\bhow (?:do|can|would) you figure out\b",
        r"\bwhat (?:are|is) (?:my|the) options?\b",
    )

    return any(re.search(pattern, text) for pattern in patterns)


def parse_discovery_option(message: str) -> str | None:
    """
    Resolve a conversational choice between the two discovery methods.
    """
    text = _normalize(message)

    active_patterns = (
        r"\b(?:the )?first (?:one|option)\b",
        r"\boption (?:one|1)\b",
        r"\bcycle through\b",
        r"\btest (?:the )?(?:lights?|dimmers?)\b",
        r"\byou do it\b",
        r"\bautomatic\b",
    )

    physical_patterns = (
        r"\b(?:the )?second (?:one|option)\b",
        r"\boption (?:two|2)\b",
        r"\bphysical switch\b",
        r"\bi(?:'| )?ll flip (?:the )?switch\b",
        r"\bi(?:'| )?ll do it\b",
    )

    if any(re.search(pattern, text) for pattern in active_patterns):
        return ACTIVE

    if any(re.search(pattern, text) for pattern in physical_patterns):
        return PHYSICAL

    return None


def parse_light_state_confirmation(message: str) -> bool | None:
    """
    Parse a natural answer to a contextual light-state question such as
    "Is the light on now?"
    """
    text = _normalize(message)

    yes = {
        "yes",
        "yeah",
        "yep",
        "yup",
        "uh yeah",
        "oh yeah",
        "yes it is",
        "yeah it is",
        "it is",
        "it's on",
        "its on",
        "the light is on",
        "it is on",
        "yeah it's on",
        "yeah its on",
        "yes it's on",
        "yes its on",
    }

    no = {
        "no",
        "nope",
        "nah",
        "uh no",
        "no it isn't",
        "no it isnt",
        "it isn't",
        "it isnt",
        "it's off",
        "its off",
        "the light is off",
        "it is off",
        "no it's off",
        "no its off",
    }

    if text in yes:
        return True

    if text in no:
        return False

    return None


def parse_discovery_confirmation(message: str) -> bool | None:
    text = _normalize(message)

    yes = {
        "yes",
        "yeah",
        "yep",
        "yup",
        "go ahead",
        "start",
        "do it",
        "yes start",
        "yes go ahead",
    }

    no = {
        "no",
        "nope",
        "nah",
        "cancel",
        "never mind",
        "nevermind",
        "don't do it",
        "do not do it",
    }

    if text in yes:
        return True

    if text in no:
        return False

    return None

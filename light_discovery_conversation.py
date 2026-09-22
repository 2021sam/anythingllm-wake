import re


ACTIVE = "active"
PHYSICAL = "physical"
TRAINING = "training"


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return " ".join(text.split())


def wants_light_control_explanation(message: str) -> bool:
    """
    Detect requests for help identifying or using lights.

    Preserve the existing navigation requests, while also making
    HOW + any lighting term a universal entrance to light navigation.

    This only requests navigation/help. It must never operate
    a light by itself.
    """
    text = _normalize(message)
    words = set(text.split())

    lighting_terms = {
        "light",
        "lights",
        "dimmer",
        "dimmers",
        "switch",
        "switches",
    }

    # Broad natural-language entrance:
    # HOW + any lighting term opens the three-option navigation.
    #
    # Specific named-room HOW-to questions are intercepted first by
    # answer_light_how_to(), so a question such as
    # "How do I turn on the Family Room light?" can teach the command
    # without preventing general questions such as
    # "How do you turn on the lights?" from opening navigation.
    if "how" in words and words & lighting_terms:
        return True

    # Preserve the older navigation/capability requests.
    if not words & lighting_terms:
        return False

    patterns = (
        r"\bwhat (?:are|is) (?:my|the) options?\b",
    )

    return any(re.search(pattern, text) for pattern in patterns)



def answer_light_how_to(message: str) -> str | None:
    """
    Answer specific HOW-to-operate-light questions without operating
    the device.

    General questions such as "How do I use the lights?" remain part
    of the three-option light navigation.
    """
    text = _normalize(message)

    if "how" not in text.split():
        return None

    room = None

    if "family room" in text:
        room = "Family Room"
    elif "front left bedroom" in text:
        room = "Front Left Bedroom"

    if room is None:
        return None

    if re.search(r"\bturn (?:the )?(?:light |lights )?on\b", text):
        return f"Just say, 'Turn on the {room} light.'"

    if re.search(r"\bturn on\b", text):
        return f"Just say, 'Turn on the {room} light.'"

    if re.search(r"\bturn (?:the )?(?:light |lights )?off\b", text):
        return f"Just say, 'Turn off the {room} light.'"

    if re.search(r"\bturn off\b", text):
        return f"Just say, 'Turn off the {room} light.'"

    if re.search(r"\b(?:dim|set|brightness|brighten)\b", text):
        return (
            f"You can set the {room} light to a percentage. "
            f"For example, say, "
            f"'Set the {room} light to 50 percent.'"
        )

    return None


def parse_discovery_option(message: str) -> str | None:
    """
    Resolve a conversational choice between the three light-help methods.
    """
    text = _normalize(message)

    active_patterns = (
        r"\b(?:the )?first (?:one|option)\b",
        r"\b(?:option|action) (?:one|1)\b",
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

    training_patterns = (
        r"\b(?:the )?third (?:one|option)\b",
        r"\boption (?:three|3)\b",
        r"\btraining mode\b",
        r"\btraining\b",
        r"\bteach me\b",
    )

    if any(re.search(pattern, text) for pattern in active_patterns):
        return ACTIVE

    if any(re.search(pattern, text) for pattern in physical_patterns):
        return PHYSICAL

    if any(re.search(pattern, text) for pattern in training_patterns):
        return TRAINING

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

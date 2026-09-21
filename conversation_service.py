import re

CASUAL = "casual"
DIRECT = "direct"
ROOM_QUESTION = "room_question"


QUESTION_STARTERS = (
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "which",
    "whose",
    "can",
    "could",
    "would",
    "will",
    "is",
    "are",
    "am",
    "do",
    "does",
    "did",
    "should",
    "may",
)

DIRECT_FOLLOWUP_PREFIXES = (
    "what about ",
    "how about ",
    "and ",
)

DIRECT_REQUEST_PREFIXES = (
    "tell me ",
    "give me ",
    "find ",
    "check ",
    "turn ",
    "set ",
    "dim ",
    "play ",
    "stop ",
    "pause ",
    "resume ",
    "open ",
    "close ",
    "lock ",
    "unlock ",
    "remind ",
    "navigate ",
    "route ",
    "drive ",
)

ROOM_PATTERNS = (
    r"\bdoes anyone know\b",
    r"\bdo you guys know\b",
    r"\bdoes anybody know\b",
    r"\bcan anyone tell me\b",
    r"\bcan anybody tell me\b",
)


def normalize_utterance(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return " ".join(text.split())


def classify_utterance(text, active_conversation=True):
    normalized = normalize_utterance(text)

    if not normalized:
        return CASUAL

    for pattern in ROOM_PATTERNS:
        if re.search(pattern, normalized):
            return ROOM_QUESTION

    if active_conversation:
        if normalized.startswith(DIRECT_FOLLOWUP_PREFIXES):
            return DIRECT

        if normalized.startswith(DIRECT_REQUEST_PREFIXES):
            return DIRECT

        # During an active Jarvis conversation, an ordinary
        # question is treated as a direct follow-up.
        if normalized.startswith(QUESTION_STARTERS):
            return DIRECT

    else:
        if normalized.startswith(QUESTION_STARTERS):
            return ROOM_QUESTION

    return CASUAL

from conversation_service import (
    CASUAL,
    DIRECT,
    ROOM_QUESTION,
    classify_utterance,
)


TESTS = [
    (
        "Oh yeah, it is pretty hot.",
        True,
        CASUAL,
    ),
    (
        "That's pretty hot.",
        True,
        CASUAL,
    ),
    (
        "What about tomorrow?",
        True,
        DIRECT,
    ),
    (
        "And San Francisco?",
        True,
        DIRECT,
    ),
    (
        "How long would it take to drive there?",
        True,
        DIRECT,
    ),
    (
        "Tell me the weather tomorrow.",
        True,
        DIRECT,
    ),
    (
        "Does anyone know how hot it is outside?",
        True,
        ROOM_QUESTION,
    ),
    (
        "How old are you?",
        True,
        DIRECT,
    ),
    (
        "How old are you?",
        False,
        ROOM_QUESTION,
    ),
    (
        "Does anyone know how hot it is in Walnut Creek?",
        False,
        ROOM_QUESTION,
    ),
    (
        "It sure is warm today.",
        False,
        CASUAL,
    ),
]


failed = 0

for text, active, expected in TESTS:
    actual = classify_utterance(
        text,
        active_conversation=active,
    )

    status = "PASS" if actual == expected else "FAIL"

    print(
        f"{status:4} "
        f"active={str(active):5} "
        f"{actual:13} "
        f"{text}"
    )

    if actual != expected:
        print(f"     expected: {expected}")
        failed += 1


print()
print(f"{len(TESTS) - failed}/{len(TESTS)} tests passed.")

if failed:
    raise SystemExit(1)

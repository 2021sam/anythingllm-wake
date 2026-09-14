from current_request import CurrentRequest, update_current_request


r = CurrentRequest()

tests = [
    (
        "What's the temperature?",
        ("weather", "temperature", "Blackhawk", "today"),
    ),
    (
        "What about Walnut Creek?",
        ("weather", "temperature", "Walnut Creek", "today"),
    ),
    (
        "What about Concord?",
        ("weather", "temperature", "Concord", "today"),
    ),
    (
        "What about tomorrow?",
        ("weather", "temperature", "Concord", "tomorrow"),
    ),
    (
        "What about San Francisco?",
        ("weather", "temperature", "San Francisco", "tomorrow"),
    ),
]

for message, expected in tests:
    assert update_current_request(r, message)

    actual = (
        r.domain,
        r.intent,
        r.location,
        r.date,
    )

    print(message)
    print(" ->", r.canonical_text())

    assert actual == expected, (actual, expected)

assert update_current_request(
    r,
    "Is it going to rain there?",
)

assert (
    r.domain,
    r.intent,
    r.location,
    r.date,
) == (
    "weather",
    "precipitation",
    "San Francisco",
    "tomorrow",
)

print("Is it going to rain there?")
print(" ->", r.canonical_text())

assert update_current_request(r, "What time is it?")

assert r.domain == "time"
assert r.intent == "current_time"
assert r.location is None
assert r.date is None

print("What time is it?")
print(" ->", r.canonical_text())

print()
print("ALL CURRENT REQUEST TESTS PASSED")

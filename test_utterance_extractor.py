from utterance_extractor import extract_request, split_sentences


SPLIT_TESTS = [
    (
        "What is two plus two? Two plus nothing. Two plus nothing.",
        [
            "What is two plus two?",
            "Two plus nothing.",
            "Two plus nothing.",
        ],
    ),
    (
        "I'm looking at the sky. It looks blue. Why is it blue?",
        [
            "I'm looking at the sky.",
            "It looks blue.",
            "Why is it blue?",
        ],
    ),
]


EXTRACT_TESTS = [
    (
        "What is two plus two? Two plus nothing. Two plus nothing.",
        "What is two plus two?",
    ),
    (
        "What is two plus two. Two plus nothing. Two plus nothing.",
        "What is two plus two.",
    ),
    (
        "I'm looking at the sky. It looks unusually blue today. "
        "Why does the sky look blue?",
        "I'm looking at the sky. It looks unusually blue today. "
        "Why does the sky look blue?",
    ),
    (
        "My solar hasn't updated in four months. "
        "It has been connected for three days. "
        "Why hasn't it backfilled?",
        "My solar hasn't updated in four months. "
        "It has been connected for three days. "
        "Why hasn't it backfilled?",
    ),
    (
        "It sure is warm today.",
        "It sure is warm today.",
    ),
]


for text, expected in SPLIT_TESTS:
    actual = split_sentences(text)
    assert actual == expected, (actual, expected)


for text, expected in EXTRACT_TESTS:
    actual = extract_request(text)

    print("RAW:      ", text)
    print("EXTRACTED:", actual)
    print()

    assert actual == expected, (actual, expected)


print("ALL UTTERANCE EXTRACTOR TESTS PASSED")

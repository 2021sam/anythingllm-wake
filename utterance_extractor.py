import re


_SENTENCE_RE = re.compile(
    r"""
    .*?
    (?:
        [.!?]+
        (?=\s|$)
        |
        $
    )
    """,
    re.VERBOSE | re.DOTALL,
)


def split_sentences(text):
    """Split a Whisper transcript into sentence-like units."""
    sentences = []

    for match in _SENTENCE_RE.finditer(text.strip()):
        sentence = match.group(0).strip()

        if sentence:
            sentences.append(sentence)

    return sentences


def _normalized_sentence(sentence):
    """Normalize a sentence for conservative repetition detection."""
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        sentence.lower(),
    ).strip()


def extract_request(text):
    """
    Preserve natural multi-sentence speech by default.

    Only trim trailing speech when there is strong evidence that Whisper
    captured repeated trailing mimicry/noise. This deliberately does not
    use the active-conversation classifier because active conversation is
    permissive: ordinary understandable speech is allowed through.
    """
    text = text.strip()

    if not text:
        return ""

    sentences = split_sentences(text)

    if len(sentences) < 3:
        return text

    # Conservative known-noise case:
    #
    #   What is two plus two?
    #   Two plus nothing.
    #   Two plus nothing.
    #
    # If the same nonempty trailing sentence is repeated consecutively,
    # preserve everything before that repeated tail.
    normalized = [
        _normalized_sentence(sentence)
        for sentence in sentences
    ]

    tail = normalized[-1]

    if (
        tail
        and normalized[-2] == tail
    ):
        first_tail_index = len(sentences) - 2

        while (
            first_tail_index > 0
            and normalized[first_tail_index - 1] == tail
        ):
            first_tail_index -= 1

        preserved = sentences[:first_tail_index]

        if preserved:
            return " ".join(preserved).strip()

    return text

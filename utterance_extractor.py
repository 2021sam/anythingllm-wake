import re

from conversation_service import DIRECT, classify_utterance


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


def extract_request(text):
    """
    Extract the first coherent request block from a transcript.

    Commentary immediately before the first actionable sentence is
    preserved as context. Speech after that first actionable sentence
    is excluded for now so unrelated room speech or mimicry does not
    contaminate the request.

    If no actionable sentence can be identified, preserve the original
    transcript rather than risk deleting meaningful speech.
    """
    text = text.strip()

    if not text:
        return ""

    sentences = split_sentences(text)

    if not sentences:
        return text

    request_index = None

    for index, sentence in enumerate(sentences):
        kind = classify_utterance(
            sentence,
            active_conversation=True,
        )

        if kind == DIRECT:
            request_index = index
            break

    if request_index is None:
        return text

    return " ".join(sentences[: request_index + 1]).strip()

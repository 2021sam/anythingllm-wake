from anythingllm_client import ask_anythingllm
from current_request import update_current_request
from time_service import answer_time_question
from weather_service import (
    answer_climate_question,
    answer_weather_question,
)


def answer_question(message, current_request):
    """
    Resolve a new utterance against the current executable request.

    If CurrentRequest understands the utterance, route according to the
    resolved domain so a contextual weather phrase such as "tomorrow"
    cannot accidentally be claimed by the standalone time service.

    Otherwise preserve Jarvis's previous routing behavior.
    """

    if update_current_request(current_request, message):
        canonical = current_request.canonical_text()

        print(
            f"[CURRENT REQUEST] {message!r} "
            f"-> {canonical!r}"
        )

        if current_request.domain == "time":
            return answer_time_question(canonical)

        if current_request.domain == "weather":
            answer = answer_climate_question(canonical)

            if answer is None:
                answer = answer_weather_question(canonical)

            return answer

    # Existing fallback behavior for requests CurrentRequest does not
    # understand yet.
    answer = answer_time_question(message)

    if answer is None:
        answer = answer_climate_question(message)

    if answer is None:
        answer = answer_weather_question(message)

    if answer is None:
        answer = ask_anythingllm(message)

    return answer

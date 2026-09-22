from anythingllm_client import ask_anythingllm
from current_request import update_current_request
from device_control import (
    answer_device_command,
    execute_validated_device_intent,
)
from device_intent import interpret_device_intent
from device_intent_validator import validate_device_intent
from device_registry import DEVICES
from device_training import answer_training_mode_command
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

    # Training Mode is deterministic and must never fall through to
    # device interpretation or AnythingLLM.
    answer = answer_training_mode_command(message)

    if answer is not None:
        return answer

    # Obvious Home Assistant device commands take the deterministic
    # fast path and never need AnythingLLM.
    answer = answer_device_command(
        message,
        current_request,
        allow_natural_fallback=True,
    )

    if answer is not None:
        return answer

    # Natural conversational device requests.
    #
    # Do not invoke the AI device interpreter for every Jarvis question.
    # Only use it when the speech mentions a registered room/device alias,
    # or when an established device context could resolve words such as
    # "it" or "that".
    normalized = message.strip().lower()

    known_device_reference = any(
        alias.lower() in normalized
        for device in DEVICES.values()
        for alias in device.get("aliases", [])
    )

    contextual_device_reference = bool(
        current_request is not None
        and current_request.device_key
        and any(
            word in normalized.split()
            for word in ("it", "them", "that", "light", "lights")
        )
    )

    if known_device_reference or contextual_device_reference:
        proposed = interpret_device_intent(
            message,
            context_device_key=(
                current_request.device_key
                if current_request is not None
                else None
            ),
        )

        print(
            f"[DEVICE INTENT] {message!r} -> {proposed}"
        )

        validated = validate_device_intent(proposed)

        if validated.get("allowed"):
            return execute_validated_device_intent(
                validated,
                current_request,
            )

        if validated.get("reason") == "blocked":
            return (
                "I won't control all the lights at once. "
                "Please name a specific room or light."
            )

        if validated.get("reason") == "low_confidence":
            return (
                proposed.get("clarification")
                or "Which light do you mean?"
            )

        if proposed.get("intent") == "clarify":
            return (
                proposed.get("clarification")
                or "Which light do you mean?"
            )

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

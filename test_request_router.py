from unittest.mock import patch

from current_request import CurrentRequest
from request_router import answer_question


r = CurrentRequest()


def fake_time(message):
    return f"TIME<{message}>"


def fake_climate(message):
    return None


def fake_weather(message):
    return f"WEATHER<{message}>"


def fake_llm(message):
    return f"LLM<{message}>"


with (
    patch(
        "request_router.answer_time_question",
        side_effect=fake_time,
    ) as time_mock,
    patch(
        "request_router.answer_climate_question",
        side_effect=fake_climate,
    ),
    patch(
        "request_router.answer_weather_question",
        side_effect=fake_weather,
    ) as weather_mock,
    patch(
        "request_router.ask_anythingllm",
        side_effect=fake_llm,
    ),
):
    answer = answer_question(
        "What's the temperature?",
        r,
    )
    assert answer == (
        "WEATHER<What is the temperature "
        "in Blackhawk today?>"
    )

    answer = answer_question(
        "What about Walnut Creek?",
        r,
    )
    assert answer == (
        "WEATHER<What is the temperature "
        "in Walnut Creek today?>"
    )

    answer = answer_question(
        "What about Concord?",
        r,
    )
    assert answer == (
        "WEATHER<What is the temperature "
        "in Concord today?>"
    )

    #
    # Critical regression test:
    # "tomorrow" must stay inside WEATHER context.
    #
    answer = answer_question(
        "What about tomorrow?",
        r,
    )
    assert answer == (
        "WEATHER<What is the temperature "
        "in Concord tomorrow?>"
    )

    assert r.location == "Concord"
    assert r.date == "tomorrow"
    assert r.domain == "weather"

    #
    # The time service must NOT have been called by any of the
    # contextual weather turns above.
    #
    assert time_mock.call_count == 0

    answer = answer_question(
        "What about San Francisco?",
        r,
    )
    assert answer == (
        "WEATHER<What is the temperature "
        "in San Francisco tomorrow?>"
    )

    answer = answer_question(
        "Is it going to rain there?",
        r,
    )
    assert answer == (
        "WEATHER<Will it rain in "
        "San Francisco tomorrow?>"
    )

    assert r.intent == "precipitation"
    assert r.location == "San Francisco"
    assert r.date == "tomorrow"

    #
    # Explicit time request starts a genuinely new request.
    #
    answer = answer_question(
        "What time is it?",
        r,
    )

    assert answer == "TIME<What time is it?>"
    assert r.domain == "time"
    assert r.intent == "current_time"
    assert r.location is None
    assert r.date is None

    assert time_mock.call_count == 1


print("ALL REQUEST ROUTER TESTS PASSED")


#
# Training Mode must stay deterministic and never reach AnythingLLM.
#
with (
    patch(
        "request_router.answer_training_mode_command",
        return_value="Training Mode is on.",
    ) as training_mock,
    patch(
        "request_router.answer_device_command",
    ) as device_mock,
    patch(
        "request_router.ask_anythingllm",
    ) as llm_mock,
):
    answer = answer_question(
        "Turn on Training Mode.",
        CurrentRequest(),
    )

    assert answer == "Training Mode is on."
    training_mock.assert_called_once_with(
        "Turn on Training Mode."
    )
    device_mock.assert_not_called()
    llm_mock.assert_not_called()


print("ALL TRAINING MODE ROUTER TESTS PASSED")

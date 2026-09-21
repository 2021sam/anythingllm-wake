from unittest.mock import patch

from current_request import CurrentRequest
from request_router import answer_question


ALL_LIGHTS_RESPONSE = (
    "I won't control all the lights at once. "
    "Please name a specific room or light."
)

UNRESOLVED_RESPONSE = (
    "Which specific room or light would you like me to control?"
)


blocked = [
    "Turn off all the lights.",
    "Turn on all lights.",
    "Turn on every light.",
    "Turn off every light in the house.",
    "Turn off the whole house lights.",
    "Turn on the whole house lights.",
    "Turn the lights off in the whole house.",
]

for message in blocked:
    current = CurrentRequest()

    with patch(
        "request_router.ask_anythingllm"
    ) as llm:
        answer = answer_question(message, current)

    assert answer == ALL_LIGHTS_RESPONSE
    assert not llm.called


current = CurrentRequest()

with patch(
    "request_router.ask_anythingllm"
) as llm:
    answer = answer_question(
        "Turn off while everyone.",
        current,
    )

assert answer == UNRESOLVED_RESPONSE
assert not llm.called


print("ALL DEVICE SAFETY TESTS PASSED")

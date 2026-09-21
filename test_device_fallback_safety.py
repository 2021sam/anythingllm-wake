from device_control import answer_device_command


# Broad home-control wording must never be allowed to fall through
# to AnythingLLM, because the LLM cannot claim or perform HA actions.
for phrase in (
    "control the lights",
    "control the light switches",
    "control the dimmers",
    "operate the lights",
    "operate the light switches",
):
    answer = answer_device_command(
        phrase,
        current_request=None,
        allow_natural_fallback=True,
    )

    assert answer is not None, phrase
    assert "specific" in answer.lower(), (phrase, answer)


# Questions about how Jarvis controls devices are NOT commands.
# They may continue to the dedicated discovery/capability router.
for phrase in (
    "How do you control the lights?",
    "How do you control the light switches?",
    "How do I control the dimmers?",
):
    answer = answer_device_command(
        phrase,
        current_request=None,
        allow_natural_fallback=True,
    )

    assert answer is None, (phrase, answer)


print("ALL DEVICE FALLBACK SAFETY TESTS PASSED")

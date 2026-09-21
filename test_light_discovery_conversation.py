from light_discovery_conversation import (
    ACTIVE,
    PHYSICAL,
    parse_discovery_confirmation,
    parse_discovery_option,
    wants_light_control_explanation,
)


# Asking about capabilities must explain options,
# NOT immediately operate any lights.
for phrase in (
    "How do you control the lights?",
    "How can you control the lights?",
    "How do you identify the light switches?",
    "What are my options for identifying the lights?",
):
    assert wants_light_control_explanation(phrase)


# Option 1 = Jarvis cycles through smart dimmers.
for phrase in (
    "first option",
    "the first one",
    "option one",
    "cycle through them",
    "test the dimmers",
    "you do it",
    "automatic",
):
    assert parse_discovery_option(phrase) == ACTIVE


# Option 2 = person physically operates the switch.
for phrase in (
    "second option",
    "the second one",
    "option two",
    "I'll flip the switch",
    "physical switch",
    "I'll do it",
):
    assert parse_discovery_option(phrase) == PHYSICAL


# Unclear choices must remain unclear.
for phrase in (
    "maybe",
    "I don't know",
    "something else",
):
    assert parse_discovery_option(phrase) is None


for phrase in (
    "yes",
    "yeah",
    "yep",
    "go ahead",
    "start",
    "do it",
):
    assert parse_discovery_confirmation(phrase) is True


for phrase in (
    "no",
    "nope",
    "cancel",
    "never mind",
    "don't do it",
):
    assert parse_discovery_confirmation(phrase) is False


assert parse_discovery_confirmation("maybe") is None

print("ALL LIGHT DISCOVERY CONVERSATION TESTS PASSED")

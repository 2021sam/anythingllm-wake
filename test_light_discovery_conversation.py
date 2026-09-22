from light_discovery_conversation import (
    ACTIVE,
    PHYSICAL,
    TRAINING,
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

# Natural answers to a contextual physical-light state question.
from light_discovery_conversation import parse_light_state_confirmation

for phrase in (
    "Yes",
    "Yeah",
    "Uh, yeah.",
    "Yep",
    "It's on.",
    "The light is on.",
):
    assert parse_light_state_confirmation(phrase) is True, phrase

for phrase in (
    "No",
    "Nope",
    "Uh, no.",
    "It's off.",
    "The light is off.",
):
    assert parse_light_state_confirmation(phrase) is False, phrase

for phrase in (
    "Maybe",
    "I don't know",
):
    assert parse_light_state_confirmation(phrase) is None, phrase

print("ALL PHYSICAL LIGHT STATE RESPONSE TESTS PASSED")

# HOW + lighting terminology must enter light navigation.
for phrase in (
    "How do I use the lights?",
    "How do I control the lights?",
    "How do these lights work?",
    "Can you show me how the lights work?",
    "I don't know how to use these lights.",
    "How do I control the dimmers?",
    "How do the dimmers work?",
    "How do I use this light switch?",
    "How do I control the light switches?",
):
    assert wants_light_control_explanation(phrase), phrase

# These must NOT accidentally enter light navigation.
for phrase in (
    "Turn on the lights.",
    "The lights are on.",
    "How hot is this room?",
    "How do I control the room?",
    "How is the weather?",
):
    assert not wants_light_control_explanation(phrase), phrase

print("ALL HOW + LIGHT NAVIGATION TESTS PASSED")

# Option 3 = Training Mode teaches light voice commands.
for phrase in (
    "third option",
    "the third one",
    "option three",
    "option 3",
    "training mode",
    "training",
    "teach me",
):
    assert parse_discovery_option(phrase) == TRAINING, phrase

print("ALL TRAINING NAVIGATION OPTION TESTS PASSED")


# Specific HOW-to-operate requests should not open identification navigation.
# The broad navigation detector recognizes HOW + lighting terms.
# Named-room HOW-to requests are intercepted first by
# answer_light_how_to() in Jarvis routing.
assert wants_light_control_explanation(
    "How do I turn on the Family Room light?"
)
assert wants_light_control_explanation(
    "How do I turn off the Family Room lights?"
)
assert wants_light_control_explanation(
    "How do I dim the Family Room lights?"
)
assert wants_light_control_explanation(
    "How do I set the Family Room light to 50 percent?"
)

# Preserve general HOW + lighting navigation.
assert wants_light_control_explanation(
    "How do I use the lights?"
)
assert wants_light_control_explanation(
    "How do I control the dimmers?"
)

# Whisper can occasionally transcribe "Option one" as "Action one".
assert parse_discovery_option("Action one.") == ACTIVE

print("ALL LIGHT HELP UX TESTS PASSED")

from light_discovery_conversation import answer_light_how_to

assert answer_light_how_to(
    "How do I turn on the Family Room light?"
) == "Just say, 'Turn on the Family Room light.'"

assert answer_light_how_to(
    "How do I turn off the Family Room light?"
) == "Just say, 'Turn off the Family Room light.'"

assert answer_light_how_to(
    "How do I set the Family Room light to 50 percent?"
) == (
    "You can set the Family Room light to a percentage. "
    "For example, say, "
    "'Set the Family Room light to 50 percent.'"
)

assert answer_light_how_to(
    "Turn on the Family Room light."
) is None

assert answer_light_how_to(
    "How do I use the lights?"
) is None

# General HOW + light action still opens three-option navigation.
assert wants_light_control_explanation(
    "How do you turn on the lights?"
)
assert wants_light_control_explanation(
    "How do I turn off the lights?"
)
assert wants_light_control_explanation(
    "How do I dim the lights?"
)
assert wants_light_control_explanation(
    "How do I set the lights to 50 percent?"
)

# A named-room HOW-to is handled before navigation by
# answer_light_how_to().
assert answer_light_how_to(
    "How do I turn on the Family Room light?"
) == "Just say, 'Turn on the Family Room light.'"

print("ALL GENERAL HOW + LIGHT NAVIGATION REGRESSIONS PASSED")

print("ALL SPECIFIC LIGHT HOW-TO TESTS PASSED")

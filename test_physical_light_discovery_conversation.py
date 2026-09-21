from physical_light_discovery import describe_missed_physical_switch


cases = (
    (
        "Uh, yeah.",
        "Okay. The light is on, but Home Assistant didn't "
        "report the switch change.",
    ),
    (
        "Nope.",
        "Okay. The light is off, but Home Assistant didn't "
        "report the switch change.",
    ),
    (
        "Maybe.",
        "I wasn't sure whether you said the light was on or off.",
    ),
    (
        "",
        "I didn't hear an answer.",
    ),
)

for response, expected in cases:
    actual = describe_missed_physical_switch(response)
    assert actual == expected, (response, actual)

print("ALL PHYSICAL DISCOVERY CONVERSATION TESTS PASSED")

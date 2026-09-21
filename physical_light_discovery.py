from light_discovery_conversation import parse_light_state_confirmation


def describe_missed_physical_switch(response: str) -> str:
    """
    Interpret the person's answer after Home Assistant failed to detect
    a physical light-switch state change.
    """
    if not response:
        return "I didn't hear an answer."

    light_is_on = parse_light_state_confirmation(response)

    if light_is_on is True:
        return (
            "Okay. The light is on, but Home Assistant didn't "
            "report the switch change."
        )

    if light_is_on is False:
        return (
            "Okay. The light is off, but Home Assistant didn't "
            "report the switch change."
        )

    return "I wasn't sure whether you said the light was on or off."

import tempfile
from pathlib import Path
from unittest.mock import patch

import device_training


family_room = {
    "room": "Family Room",
    "name": "Light",
    "domain": "light",
    "entity_id": "light.wall_dimmer_1",
}


assert device_training.brightness_to_percent(191) == 75
assert device_training.brightness_to_percent(255) == 100
assert device_training.brightness_to_percent(128) == 50
assert device_training.brightness_to_percent(None) is None


assert device_training.training_announcement(
    family_room,
    "on",
    {"brightness": 191},
) == (
    "Family Room light is on at 75%. "
    "You can say, 'Set the Family Room light to 100%.'"
)

assert device_training.training_announcement(
    family_room,
    "on",
    {"brightness": 255},
) == (
    "Family Room light is on at 100%. "
    "You can say, 'Turn off the Family Room light.'"
)

assert device_training.training_announcement(
    family_room,
    "off",
    {},
) == (
    "Family Room light is off. "
    "You can say, 'Turn on the Family Room light.'"
)


with tempfile.TemporaryDirectory() as temp_dir:
    mode_file = Path(temp_dir) / "training_mode"

    with patch.object(
        device_training,
        "TRAINING_MODE_FILE",
        mode_file,
    ):
        assert device_training.get_training_mode() == "off"
        assert device_training.training_mode_enabled() is False

        device_training.set_training_mode("short")
        assert device_training.get_training_mode() == "short"
        assert device_training.training_mode_enabled() is True

        device_training.set_training_mode("normal")
        assert device_training.get_training_mode() == "normal"

        device_training.set_training_mode("long")
        assert device_training.get_training_mode() == "long"

        device_training.set_training_mode("off")
        assert device_training.get_training_mode() == "off"
        assert device_training.training_mode_enabled() is False

        # Backward compatibility with the original boolean API.
        device_training.set_training_mode(True)
        assert device_training.get_training_mode() == "normal"

        device_training.set_training_mode(False)
        assert device_training.get_training_mode() == "off"

        # Legacy persisted "on" migrates to normal.
        mode_file.write_text("on\n")
        assert device_training.get_training_mode() == "normal"


print("ALL DEVICE TRAINING CORE TESTS PASSED")


with tempfile.TemporaryDirectory() as temp_dir:
    mode_file = Path(temp_dir) / "training_mode"

    with patch.object(
        device_training,
        "TRAINING_MODE_FILE",
        mode_file,
    ):
        assert device_training.answer_training_mode_command(
            "Turn on Training Mode."
        ) == "Training Mode is normal."

        assert device_training.get_training_mode() == "normal"

        assert device_training.answer_training_mode_command(
            "Switch to short Training Mode."
        ) == "Training Mode is short."

        assert device_training.get_training_mode() == "short"

        assert device_training.answer_training_mode_command(
            "Make the training mode longer."
        ) == "Training Mode is long."

        assert device_training.get_training_mode() == "long"

        assert device_training.answer_training_mode_command(
            "Switch to normal Training Mode."
        ) == "Training Mode is normal."

        assert device_training.answer_training_mode_command(
            "What Training Mode am I using?"
        ) == "Training Mode is normal."

        assert device_training.answer_training_mode_command(
            "Is Training Mode enabled?"
        ) == "Training Mode is enabled."

        assert device_training.answer_training_mode_command(
            "Turn off Training Mode."
        ) == "Training Mode is off."

        assert device_training.get_training_mode() == "off"

        assert device_training.answer_training_mode_command(
            "Start learning mode."
        ) == "Training Mode is normal."

        assert device_training.answer_training_mode_command(
            "Stop giving me light hints."
        ) == "Training Mode is off."

        assert device_training.answer_training_mode_command(
            "What time is it?"
        ) is None


print("ALL TRAINING MODE COMMAND TESTS PASSED")

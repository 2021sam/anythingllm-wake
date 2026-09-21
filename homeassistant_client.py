from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent

HA_URL_FILE = BASE_DIR / ".homeassistant_url"
HA_TOKEN_FILE = BASE_DIR / ".homeassistant_token"


class HomeAssistantClient:
    """Small REST client for Home Assistant."""

    def __init__(self):
        self.ha_url = HA_URL_FILE.read_text().strip().rstrip("/")
        self.token = HA_TOKEN_FILE.read_text().strip()

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_entities(self) -> list[dict]:
        """Return all Home Assistant entity states."""
        response = requests.get(
            f"{self.ha_url}/api/states",
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_state(self, entity_id: str) -> dict:
        """Return the state object for one entity."""
        response = requests.get(
            f"{self.ha_url}/api/states/{entity_id}",
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_lights(self) -> list[dict]:
        """Return all Home Assistant light entities."""
        return [
            entity
            for entity in self.get_entities()
            if entity.get("entity_id", "").startswith("light.")
        ]

    def get_switches(self) -> list[dict]:
        """Return all Home Assistant switch entities."""
        return [
            entity
            for entity in self.get_entities()
            if entity.get("entity_id", "").startswith("switch.")
        ]


    def call_service(
        self,
        domain: str,
        service: str,
        data: dict,
    ) -> dict:
        """Call a Home Assistant service."""
        response = requests.post(
            f"{self.ha_url}/api/services/{domain}/{service}",
            headers=self.headers,
            json=data,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def turn_on(self, entity_id: str) -> dict:
        """Turn on a Home Assistant entity."""
        return self.call_service(
            "light",
            "turn_on",
            {"entity_id": entity_id},
        )

    def turn_off(self, entity_id: str) -> dict:
        """Turn off a Home Assistant entity."""
        return self.call_service(
            "light",
            "turn_off",
            {"entity_id": entity_id},
        )


if __name__ == "__main__":
    client = HomeAssistantClient()

    lights = client.get_lights()

    print(f"Connected to Home Assistant.")
    print(f"Found {len(lights)} light entities.")
    print()

    for light in lights:
        entity_id = light.get("entity_id")
        state = light.get("state")
        attributes = light.get("attributes", {})
        friendly_name = attributes.get("friendly_name", entity_id)

        print(
            f"{entity_id:<45} "
            f"state={state:<12} "
            f"name={friendly_name}"
        )

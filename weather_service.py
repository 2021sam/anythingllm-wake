from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
HA_URL_FILE = BASE_DIR / ".homeassistant_url"
HA_TOKEN_FILE = BASE_DIR / ".homeassistant_token"

WEATHER_ENTITY = "weather.forecast_home"


def _headers():
    token = HA_TOKEN_FILE.read_text().strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_current_weather():
    ha_url = HA_URL_FILE.read_text().strip()

    response = requests.get(
        f"{ha_url}/api/states/{WEATHER_ENTITY}",
        headers=_headers(),
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    attrs = data.get("attributes", {})

    return {
        "condition": data.get("state"),
        "temperature": attrs.get("temperature"),
        "temperature_unit": attrs.get("temperature_unit"),
        "humidity": attrs.get("humidity"),
    }


def get_daily_forecast():
    ha_url = HA_URL_FILE.read_text().strip()

    response = requests.post(
        f"{ha_url}/api/services/weather/get_forecasts?return_response",
        headers=_headers(),
        json={
            "entity_id": WEATHER_ENTITY,
            "type": "daily",
        },
        timeout=10,
    )
    response.raise_for_status()

    return (
        response.json()
        ["service_response"]
        [WEATHER_ENTITY]
        ["forecast"]
    )


def _condition_text(condition):
    if not condition:
        return "unknown conditions"

    return condition.replace("-", " ").replace(
        "partlycloudy",
        "partly cloudy",
    )


def answer_weather_question(message):
    text = message.lower().strip()

    weather_words = (
        "weather",
        "temperature",
        "hot",
        "cold",
        "high",
        "low",
        "forecast",
        "rain",
    )

    if not any(word in text for word in weather_words):
        return None

    current = get_current_weather()
    forecast = get_daily_forecast()

    today = forecast[0]
    tomorrow = forecast[1] if len(forecast) > 1 else None

    unit = current.get("temperature_unit", "°F")

    if "tomorrow" in text and tomorrow:
        condition = _condition_text(tomorrow.get("condition"))
        high = tomorrow.get("temperature")
        low = tomorrow.get("templow")

        return (
            f"Tomorrow will be {condition}, "
            f"with a high of {high} degrees "
            f"and a low of {low} degrees."
        )

    if "high" in text or "how hot" in text:
        return (
            f"Today's high is "
            f"{today.get('temperature')} degrees."
        )

    if (
        "low" in text
        or "tonight" in text
        or "how cold" in text
    ):
        return (
            f"Tonight's low is "
            f"{today.get('templow')} degrees."
        )

    temperature = current.get("temperature")
    condition = _condition_text(current.get("condition"))
    humidity = current.get("humidity")

    return (
        f"It is {temperature} degrees and {condition}. "
        f"Humidity is {humidity} percent."
    )

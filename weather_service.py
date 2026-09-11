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


# ---------------------------------------------------------------------------
# Cached historical climate
# ---------------------------------------------------------------------------

import json
import calendar

CLIMATE_CACHE_FILE = BASE_DIR / "climate_cache.json"

MONTH_NAMES = {
    name.lower(): number
    for number, name in enumerate(calendar.month_name)
    if name
}

SEASONS = {
    "winter": [12, 1, 2],
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "fall": [9, 10, 11],
    "autumn": [9, 10, 11],
}


def _load_climate_cache():
    if not CLIMATE_CACHE_FILE.exists():
        return None

    return json.loads(CLIMATE_CACHE_FILE.read_text())


def _average_months(climate, month_numbers):
    values = [
        climate["months"][str(month)]
        for month in month_numbers
    ]

    return {
        "high": round(
            sum(v["avg_high_f"] for v in values)
            / len(values)
        ),
        "low": round(
            sum(v["avg_low_f"] for v in values)
            / len(values)
        ),
        "precip": round(
            sum(v["avg_precip_in"] for v in values),
            1,
        ),
    }


def answer_climate_question(message):
    text = message.lower().strip()

    climate_words = (
        "usually",
        "typical",
        "typically",
        "average",
        "normally",
        "generally",
    )

    if not any(word in text for word in climate_words):
        return None

    climate = _load_climate_cache()

    if climate is None:
        return None

    for month_name, month_number in MONTH_NAMES.items():
        if month_name in text:
            values = climate["months"][str(month_number)]

            return (
                f"In {month_name.title()}, the typical high is "
                f"around {values['avg_high_f']} degrees and the "
                f"typical low is around {values['avg_low_f']} degrees."
            )

    for season, months in SEASONS.items():
        if season in text:
            values = _average_months(climate, months)

            spoken_season = (
                "fall" if season == "autumn" else season
            )

            return (
                f"In {spoken_season}, typical daytime highs are "
                f"around {values['high']} degrees, with nighttime "
                f"lows around {values['low']} degrees."
            )

    return None

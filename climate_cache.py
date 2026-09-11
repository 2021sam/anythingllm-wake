from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
HA_URL_FILE = BASE_DIR / ".homeassistant_url"
HA_TOKEN_FILE = BASE_DIR / ".homeassistant_token"
CACHE_FILE = BASE_DIR / "climate_cache.json"


def _get_home_coordinates():
    ha_url = HA_URL_FILE.read_text().strip()
    token = HA_TOKEN_FILE.read_text().strip()

    r = requests.get(
        f"{ha_url}/api/states/zone.home",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()

    attrs = r.json().get("attributes", {})
    lat = attrs.get("latitude")
    lon = attrs.get("longitude")

    if lat is None or lon is None:
        raise RuntimeError("Home coordinates unavailable.")

    return lat, lon


def build_climate_cache():
    lat, lon = _get_home_coordinates()

    current_year = date.today().year
    start_year = current_year - 10
    end_year = current_year - 1

    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": (
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_sum"
            ),
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
            "timezone": "auto",
        },
        timeout=60,
    )
    r.raise_for_status()

    daily = r.json()["daily"]

    months = defaultdict(
        lambda: {
            "highs": [],
            "lows": [],
            "precip": [],
        }
    )

    for day, high, low, precip in zip(
        daily["time"],
        daily["temperature_2m_max"],
        daily["temperature_2m_min"],
        daily["precipitation_sum"],
    ):
        month = int(day[5:7])

        if high is not None:
            months[month]["highs"].append(high)
        if low is not None:
            months[month]["lows"].append(low)
        if precip is not None:
            months[month]["precip"].append(precip)

    result = {
        "period": f"{start_year}-{end_year}",
        "months": {},
    }

    for month in range(1, 13):
        values = months[month]

        avg_high = round(
            sum(values["highs"]) / len(values["highs"])
        )
        avg_low = round(
            sum(values["lows"]) / len(values["lows"])
        )

        yearly_precip = []
        for year in range(start_year, end_year + 1):
            total = 0.0
            found = False

            for day, precip in zip(
                daily["time"],
                daily["precipitation_sum"],
            ):
                if (
                    int(day[:4]) == year
                    and int(day[5:7]) == month
                    and precip is not None
                ):
                    total += precip
                    found = True

            if found:
                yearly_precip.append(total)

        avg_precip = round(
            sum(yearly_precip) / len(yearly_precip),
            1,
        )

        result["months"][str(month)] = {
            "avg_high_f": avg_high,
            "avg_low_f": avg_low,
            "avg_precip_in": avg_precip,
        }

    CACHE_FILE.write_text(
        json.dumps(result, indent=2)
    )

    return result


if __name__ == "__main__":
    data = build_climate_cache()

    print("Climate cache created.")
    print("Period:", data["period"])

    for month, values in data["months"].items():
        print(
            month,
            values["avg_high_f"],
            values["avg_low_f"],
            values["avg_precip_in"],
        )

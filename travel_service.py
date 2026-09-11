from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent

API_KEY_FILE = BASE_DIR / ".openrouteservice_api_key"
DEFAULT_LOCATION_FILE = BASE_DIR / ".default_location"

GEOCODE_URL = "https://api.heigit.org/pelias/v1/search"
DIRECTIONS_URL = (
    "https://api.heigit.org/openrouteservice/v2/"
    "directions/driving-car/json"
)


def _api_key():
    return API_KEY_FILE.read_text().strip()


def _default_location():
    return DEFAULT_LOCATION_FILE.read_text().strip()


def _geocode(query, focus=None):
    params = {
        "text": query,
        "size": 1,
        "boundary.country": "USA",
    }

    if focus:
        lat, lon = focus
        params["focus.point.lat"] = lat
        params["focus.point.lon"] = lon

    r = requests.get(
        GEOCODE_URL,
        headers={"Authorization": _api_key()},
        params=params,
        timeout=20,
    )
    r.raise_for_status()

    features = r.json().get("features", [])

    if not features:
        raise ValueError(f"Location not found: {query}")

    return features[0]


def _destination_candidates(query):
    q = query.strip()
    lower = q.lower()

    candidates = [q]

    if "bart" in lower:
        place = (
            lower
            .replace("bart station", "")
            .replace("bart", "")
            .strip(" ,")
        )

        title = place.title()

        candidates.extend([
            f"{title} Station, {title}, CA",
            f"{title} BART Station, {title}, CA",
        ])

        if title == "Dublin":
            candidates.insert(
                1,
                "Dublin/Pleasanton BART Station, Dublin, CA",
            )

    if "airport" in lower:
        place = (
            lower
            .replace("international airport", "")
            .replace("airport", "")
            .strip(" ,")
        )

        title = place.title()

        candidates.extend([
            f"{title} International Airport, {title}, CA",
            f"{title} Airport, {title}, CA",
        ])

    # Preserve order but remove duplicates.
    return list(dict.fromkeys(candidates))


def _important_words(query):
    ignored = {
        "the",
        "to",
        "from",
        "station",
        "international",
    }

    return {
        word
        for word in query.lower().replace("/", " ").split()
        if len(word) > 2 and word not in ignored
    }


def _match_score(query, label):
    query_words = _important_words(query)
    label_lower = label.lower()

    score = sum(
        1
        for word in query_words
        if word in label_lower
    )

    if "bart" in query.lower() and "bart" in label_lower:
        score += 3

    if "airport" in query.lower() and "airport" in label_lower:
        score += 3

    return score


def _geocode_destination(query, focus=None):
    best_feature = None
    best_score = -1

    for candidate in _destination_candidates(query):
        params = {
            "text": candidate,
            "size": 5,
            "boundary.country": "USA",
        }

        if focus:
            lat, lon = focus
            params["focus.point.lat"] = lat
            params["focus.point.lon"] = lon

        r = requests.get(
            GEOCODE_URL,
            headers={"Authorization": _api_key()},
            params=params,
            timeout=20,
        )
        r.raise_for_status()

        for feature in r.json().get("features", []):
            label = (
                feature.get("properties", {}).get("label")
                or ""
            )

            score = _match_score(query, label)

            if score > best_score:
                best_feature = feature
                best_score = score

    if best_feature is None:
        raise ValueError(f"Location not found: {query}")

    if "bart" in query.lower():
        label = (
            best_feature.get("properties", {}).get("label")
            or ""
        )

        if "bart" not in label.lower():
            raise ValueError(
                f"Could not confidently identify BART station: {query}"
            )

    if "airport" in query.lower():
        label = (
            best_feature.get("properties", {}).get("label")
            or ""
        )

        if "airport" not in label.lower():
            raise ValueError(
                f"Could not confidently identify airport: {query}"
            )

    return best_feature


def get_drive_time(destination, origin=None):
    if origin is None:
        origin = _default_location()

    # Resolve explicit origins such as "Dublin BART" using the
    # same smarter place-name handling used for destinations.
    if origin == _default_location():
        start = _geocode(origin)
    else:
        default = _geocode(_default_location())
        default_lon, default_lat = default["geometry"]["coordinates"]

        start = _geocode_destination(
            origin,
            focus=(default_lat, default_lon),
        )

    start_lon, start_lat = start["geometry"]["coordinates"]

    end = _geocode_destination(
        destination,
        focus=(start_lat, start_lon),
    )
    end_lon, end_lat = end["geometry"]["coordinates"]

    r = requests.post(
        DIRECTIONS_URL,
        headers={
            "Authorization": _api_key(),
            "Content-Type": "application/json",
        },
        json={
            "coordinates": [
                [start_lon, start_lat],
                [end_lon, end_lat],
            ]
        },
        timeout=30,
    )
    r.raise_for_status()

    summary = r.json()["routes"][0]["summary"]

    minutes = round(summary["duration"] / 60)
    miles = round(summary["distance"] / 1609.344, 1)

    label = (
        end.get("properties", {}).get("label")
        or destination
    )

    return {
        "destination": label,
        "minutes": minutes,
        "miles": miles,
    }


if __name__ == "__main__":
    result = get_drive_time("Walnut Creek BART")

    print("Destination:", result["destination"])
    print("Drive time:", result["minutes"], "minutes")
    print("Distance:", result["miles"], "miles")


def parse_travel_question(message):
    import re

    text = message.strip()

    # Common Whisper transcription for spoken "BART station".
    text = re.sub(
        r"\bbar station\b",
        "BART station",
        text,
        flags=re.IGNORECASE,
    )

    # Natural phrasing: "How long to drive to X?"
    text = re.sub(
        r"\bto drive to\b",
        "to",
        text,
        flags=re.IGNORECASE,
    )

    # Explicit: "from X to Y"
    match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)[?.!]*$",
        text,
        re.IGNORECASE,
    )

    if match:
        origin = match.group(1).strip()
        destination = match.group(2).strip()

        if origin.lower() in ("here", "home"):
            origin = None

        return origin, destination

    # Default origin: "... to Y"
    match = re.search(
        r"\bto\s+(.+?)[?.!]*$",
        text,
        re.IGNORECASE,
    )

    if match:
        destination = match.group(1).strip()
        return None, destination

    return None


def answer_travel_question(message):
    text = message.lower()

    travel_words = (
        "how long",
        "drive time",
        "driving time",
        "how far",
        "how many minutes",
    )

    if not any(word in text for word in travel_words):
        return None

    parsed = parse_travel_question(message)

    if parsed is None:
        return None

    origin, destination = parsed

    result = get_drive_time(
        destination=destination,
        origin=origin,
    )

    return (
        f"It is about {result['minutes']} minutes "
        f"and {result['miles']} miles by car."
    )

from pathlib import Path
import json
import requests

BASE_URL = "http://localhost:3001"
WORKSPACE_SLUG = "my-workspace"

API_KEY_FILE = Path(__file__).parent / ".anythingllm_api_key"


def interpret_intent(message: str, context: dict | None = None) -> dict:
    """
    Use AI to convert imperfect natural speech into a structured Jarvis intent.

    The AI interprets meaning only. It never performs the action.
    """
    api_key = API_KEY_FILE.read_text().strip()

    context = context or {}

    prompt = f"""
You are the intent interpreter for a local AI home hub named Jarvis.

The speech transcript may contain recognition mistakes.
Interpret the intended meaning using context and common sense.

Important rules:
- Do not claim that you performed an action.
- Return JSON only.
- Do not include markdown.
- Do not invent parameters that do not exist.
- If the intent is ambiguous, return intent "clarify".
- Correct obvious speech recognition errors when the intended command is clear.
- "sit" may mean "set" when used with a known parameter.
- "two three seconds" may represent "to three seconds" when grammar and context strongly support it.

Known parameters:
- room_answer_delay
  Spoken name: "room answer delay"
  Type: seconds
  Valid range: 0 to 30

Supported intents:
- set_parameter
- get_parameter
- list_parameters
- clarify
- unknown

Return exactly this JSON structure:

{{
  "intent": "set_parameter|get_parameter|list_parameters|clarify|unknown",
  "parameter": null,
  "value": null,
  "unit": null,
  "confidence": 0.0,
  "clarification": null
}}

Examples:

Speech:
Set room answer delay to three seconds.

Result:
{{
  "intent": "set_parameter",
  "parameter": "room_answer_delay",
  "value": 3,
  "unit": "seconds",
  "confidence": 0.99,
  "clarification": null
}}

Speech:
Sit room answer delay two three seconds.

Result:
{{
  "intent": "set_parameter",
  "parameter": "room_answer_delay",
  "value": 3,
  "unit": "seconds",
  "confidence": 0.95,
  "clarification": null
}}

Speech:
Change something to three seconds.

Result:
{{
  "intent": "clarify",
  "parameter": null,
  "value": 3,
  "unit": "seconds",
  "confidence": 0.4,
  "clarification": "Which parameter do you want me to change?"
}}

Current context:
{json.dumps(context)}

Speech transcript:
{message}
"""

    response = requests.post(
        f"{BASE_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chat",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "message": prompt,
            "mode": "chat",
            "sessionId": "jarvis-intent",
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()
    text = data["textResponse"].strip()

    # Tolerate an LLM wrapping JSON in a markdown code fence.
    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "intent": "clarify",
            "parameter": None,
            "value": None,
            "unit": None,
            "confidence": 0.0,
            "clarification": (
                "I understood that as a command, "
                "but I couldn't determine exactly what you wanted."
            ),
            "error": f"Invalid intent JSON: {exc}",
            "raw_response": text,
        }

    return result


def ask_anythingllm(message: str) -> str:
    api_key = API_KEY_FILE.read_text().strip()

    response = requests.post(
        f"{BASE_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chat",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "message": message,
            "mode": "chat",
            "sessionId": "jarvis-conversation",
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()
    return data["textResponse"]


if __name__ == "__main__":
    question = input("You: ")
    answer = ask_anythingllm(question)
    print(f"Assistant: {answer}")
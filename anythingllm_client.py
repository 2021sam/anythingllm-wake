from pathlib import Path
import requests

BASE_URL = "http://localhost:3001"
WORKSPACE_SLUG = "my-workspace"

API_KEY_FILE = Path(__file__).parent / ".anythingllm_api_key"


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
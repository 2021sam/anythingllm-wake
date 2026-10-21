from fastapi import FastAPI
from pydantic import BaseModel

from current_request import CurrentRequest
from request_router import answer_question


app = FastAPI(title="Jarvis Home Hub API")

# Persistent conversation context for this first satellite.
current_request = CurrentRequest()


class AskRequest(BaseModel):
    message: str
    device_id: str = "android-1"
    room: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "jarvis-home-hub",
    }


@app.post("/ask")
def ask(request: AskRequest):
    message = request.message.strip()

    if not message:
        return {"answer": ""}

    print(
        f"[ANDROID] device={request.device_id} "
        f"room={request.room} "
        f"message={message!r}",
        flush=True,
    )

    answer = answer_question(
        message,
        current_request,
    )

    print(
        f"[ANDROID] answer={answer!r}",
        flush=True,
    )

    return {
        "answer": answer,
        "device_id": request.device_id,
        "room": request.room,
    }

import json
import logging
import os
import time
from typing import Any, Iterator
from dotenv import load_dotenv
from flask import Blueprint, Response, jsonify, request, stream_with_context
from openai import OpenAI
from vercel.oidc import get_vercel_oidc_token

load_dotenv(".env.local")

api_bp = Blueprint("api", __name__)

logger: logging.Logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@api_bp.post("/api/chat")
def stream_chat_completion() -> Response:
    payload: dict[str, Any] = request.get_json(silent=True) or {}
    messages_input: Any = payload.get("messages")
    messages: list[dict[str, Any]]
    if isinstance(messages_input, list):
        messages = messages_input
    else:
        messages = []

    model: str = payload.get("model", DEFAULT_MODEL)

    if not messages:
        prompt: Any = payload.get("prompt")
        if not prompt:
            return jsonify({"error": "Provide `messages` or `prompt`."}), 400
        messages = [{"role": "user", "content": prompt}]

    try:
        client: OpenAI = OpenAI(
            api_key=get_vercel_oidc_token(),
            base_url="https://ai-gateway.vercel.sh/v1",
        )
    except Exception:
        logger.exception("Failed to acquire AI Gateway credentials")
        return jsonify({"error": "Unable to authenticate with AI Gateway"}), 500

    def event_stream() -> Iterator[str]:
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                payload_chunk: str
                if hasattr(chunk, "model_dump_json"):
                    payload_chunk = chunk.model_dump_json(exclude_unset=True)  # type: ignore[attr-defined]
                elif hasattr(chunk, "model_dump"):
                    payload_chunk = json.dumps(
                        getattr(chunk, "model_dump")(exclude_unset=True)  # type: ignore[attr-defined]
                    )
                else:
                    try:
                        payload_chunk = json.dumps(chunk)  # type: ignore[arg-type]
                    except TypeError:
                        payload_chunk = str(chunk)

                yield f"data: {payload_chunk}\n\n"
        except Exception as exc:
            logger.exception("Error while streaming chat completion")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    headers: dict[str, str] = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return Response(stream_with_context(event_stream()), headers=headers)


@api_bp.get("/api/lorem")
def stream_lorem_ipsum() -> Response:
    logger.info("Received /api/lorem request")

    lorem_text: str = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua."
    )

    def generate() -> Iterator[str]:
        end_time: float = time.monotonic() + 60
        while time.monotonic() < end_time:
            yield lorem_text + "\n"
            time.sleep(1)

    headers: dict[str, str] = {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return Response(stream_with_context(generate()), headers=headers)

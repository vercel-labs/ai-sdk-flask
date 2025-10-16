
import json
import os
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context
from openai import OpenAI, base_url


def _load_env_from_file(filename: str) -> None:
    base_dir = Path(__file__).resolve().parent.parent
    env_path = base_dir / filename
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :]

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


_load_env_from_file(".env.local")
_load_env_from_file(".env")


api_bp = Blueprint("api", __name__)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")



@api_bp.post("/api/chat")
def stream_chat_completion():
    api_key = os.getenv("OPENAI_API_KEY")
    oidc_token = os.getenv("OIDC_TOKEN")
    if not api_key:
        return jsonify({"error": "OpenAI API key is not configured."}), 500
    openai_client = OpenAI(api_key=oidc_token, base_url="https://ai-gateway.vercel.sh/v1")

    payload = request.get_json(silent=True) or {}
    raw_messages = payload.get("messages")
    messages_payload = None

    if raw_messages:
        normalized_messages = []
        for message in raw_messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if isinstance(content, list):
                normalized_content = []
                for item in content:
                    if isinstance(item, dict):
                        normalized_content.append(item)
                    elif isinstance(item, str):
                        normalized_content.append({"type": "text", "text": item})
                    else:
                        normalized_content.append(
                            {"type": "text", "text": json.dumps(item)}
                        )
            elif isinstance(content, str):
                normalized_content = content
            else:
                normalized_content = json.dumps(content)

            normalized_messages.append(
                {
                    "role": role,
                    "content": normalized_content,
                }
            )

        messages_payload = normalized_messages
    else:
        prompt = payload.get("prompt")
        if prompt:
            messages_payload = [{"role": "user", "content": prompt}]
        else:
            return jsonify({"error": "Provide either `messages` or `prompt`."}), 400

    model = payload.get("model", DEFAULT_MODEL)

    def event_stream():
        try:
            stream = openai_client.chat.completions.create(
                model=model,
                messages=messages_payload,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                text = None

                if delta:
                    content = getattr(delta, "content", None)
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if isinstance(item, dict):
                                parts.append(item.get("text", ""))
                            elif isinstance(item, str):
                                parts.append(item)
                            else:
                                parts.append(str(item))
                        text = "".join(parts)
                    elif isinstance(content, str):
                        text = content

                if text:
                    yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"

                if getattr(choice, "finish_reason", None):
                    break

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return Response(stream_with_context(event_stream()), headers=headers)

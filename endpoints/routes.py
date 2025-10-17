import json
import os
from dotenv import load_dotenv
from flask import Blueprint, Response, jsonify, request, stream_with_context
from openai import OpenAI
from vercel.oidc import get_vercel_oidc_token

load_dotenv(".env.local")

api_bp = Blueprint("api", __name__)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@api_bp.post("/api/chat")
def stream_chat_completion():
    openai_client = OpenAI(api_key=get_vercel_oidc_token(), base_url="https://ai-gateway.vercel.sh/v1")
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

import json
import logging
import os
from dotenv import load_dotenv
from flask import Blueprint, Response, jsonify, request, stream_with_context
from openai import OpenAI
from vercel.oidc import get_vercel_oidc_token

load_dotenv(".env.local")

api_bp = Blueprint("api", __name__)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@api_bp.post("/api/chat")
def stream_chat_completion():
    payload = request.get_json(silent=True) or {}
    logger.info("Received /api/chat request with keys=%s", sorted(payload.keys()))

    try:
        api_token = get_vercel_oidc_token()
    except Exception:
        logger.exception("Failed to acquire Vercel OIDC token for chat request")
        return jsonify({"error": "Unable to authenticate with AI Gateway"}), 500

    openai_client = OpenAI(
        api_key=api_token,
        base_url="https://ai-gateway.vercel.sh/v1",
    )

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
            logger.debug("Using fallback prompt payload for chat request")
            messages_payload = [{"role": "user", "content": prompt}]
        else:
            logger.warning("Rejected /api/chat request missing both messages and prompt")
            return jsonify({"error": "Provide either `messages` or `prompt`."}), 400

    model = payload.get("model", DEFAULT_MODEL)
    message_count = len(messages_payload) if isinstance(messages_payload, list) else 1
    logger.info(
        "Preparing chat completion request model=%s message_count=%s",
        model,
        message_count,
    )

    try:
        stream = openai_client.chat.completions.create(
            model=model,
            messages=messages_payload,
            stream=True,
        )
    except Exception:
        logger.exception("OpenAI chat completion request failed to initialize")
        return jsonify({"error": "Unable to initiate model stream"}), 502

    def event_stream():
        try:
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
                    logger.info(
                        "OpenAI stream completed with finish_reason=%s",
                        getattr(choice, "finish_reason", None),
                    )
                    break

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            logger.exception("Error while streaming chat completion tokens")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return Response(stream_with_context(event_stream()), headers=headers)

import os
import json
from flask import Blueprint,  Response, request, stream_with_context
from openai import OpenAI
from dotenv import load_dotenv
from openai.lib.streaming.chat import ChatCompletionStreamManager

load_dotenv(".env.local")

api_bp = Blueprint("api", __name__)

@api_bp.route("/api/chat", methods=["POST"])
def chat():
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    data = request.get_json()
    user_message = data.get("message", "")

    # Create a streaming response
    def generate():
        with client.chat.completions.stream(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for event in stream:
                yield(json.dumps(event))

    return Response(stream_with_context(generate()), content_type="text/plain")

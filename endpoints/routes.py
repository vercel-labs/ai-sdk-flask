from flask import Blueprint,  Response, request, stream_with_context
from openai import OpenAI
from dotenv import load_dotenv
from vercel.oidc import get_vercel_oidc_token

load_dotenv(".env.local")

api_bp = Blueprint("api", __name__)

@api_bp.route("/api/chat", methods=["POST"])
def chat():
    client = OpenAI(api_key=get_vercel_oidc_token(), base_url="https://ai-gateway.vercel.sh/v1")

    data = request.get_json()
    user_message = data.get("message", "")

    # Create a streaming response
    def generate():
        with client.chat.completions.stream(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "why is the sky blue?"}],
        ) as stream:
            for event in stream:
                yield(event.type + "\n")

    return Response(stream_with_context(generate()), content_type="text/plain")

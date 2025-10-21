from flask import Blueprint, Response, request
from openai import OpenAI
from dotenv import load_dotenv
from vercel import oidc

load_dotenv(".env.local")

api_bp = Blueprint("api", __name__)

@api_bp.route("/api/generate", methods=["POST"])
def chat():
    client = OpenAI(api_key=oidc.get_vercel_oidc_token(), base_url="https://ai-gateway.vercel.sh/v1")

    prompt = request.args.get("prompt")
    if not prompt:
        return Response("Missing 'prompt' query parameter.", status=400, content_type="text/plain")

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    message_content = completion.choices[0].message["content"]

    return Response(message_content, content_type="text/plain")

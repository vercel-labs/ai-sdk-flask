from flask import Flask, request
from endpoints import api_bp
from vercel.headers import set_headers


app = Flask(__name__)
app.register_blueprint(api_bp)

@app.before_request
def _vercel_set_headers():
    set_headers(request.headers)

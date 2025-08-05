from flask import Flask, redirect, session, send_from_directory, request, jsonify
from flask_cors import CORS     
from dotenv import load_dotenv
import os
from urllib.parse import urlencode
import secrets
import requests
import hashlib
import hmac as hmac_lib
from database import init_db, get_db
from datetime import datetime

load_dotenv()

APP_CLIENT_ID = os.getenv("APP_CLIENT_ID")
APP_CLIENT_SECRET = os.getenv("APP_CLIENT_SECRET")
APP_REDIRECT_URI = os.getenv("APP_REDIRECT_URI")
APP_SCOPES = os.getenv("APP_SCOPES")
SECRET_KEY = os.getenv("SECRET_KEY")

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
)
CORS(app)
init_db()

# Shopify OAuth (Initial Authorization)
@app.route("/auth")
def auth():
    shop = request.args.get("shop")
    hmac = request.args.get("hmac")
    embedded = request.args.get("embedded")
    if not verify_hmac(request.args, hmac):
        return "Invalid HMAC", 401
    
    if embedded == "1":
        if check_shop(shop):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return "Shop not found", 404
    
    nonce = secrets.token_hex(16)
    session["nonce"] = nonce
    params = {
        "client_id": APP_CLIENT_ID,
        "scope": APP_SCOPES,
        "redirect_uri": APP_REDIRECT_URI,
        "state": nonce
    }   
    return redirect(f"https://{shop}/admin/oauth/authorize?{urlencode(params)}")

# Shopify OAuth (Callback)
@app.route("/auth/callback")
def auth_callback():
    shop = request.args.get("shop")
    host = request.args.get("host")
    hmac = request.args.get("hmac")
    code = request.args.get("code")
    state = request.args.get("state")
    if state != session["nonce"]:
        return "Invalid state", 401
    if not verify_hmac(request.args, hmac):
        return "Invalid HMAC", 401

    params = {
        "client_id": APP_CLIENT_ID,
        "client_secret": APP_CLIENT_SECRET,
        "code": code
    }
    response = requests.post(f"https://{shop}/admin/oauth/access_token", params=params)
    access_token = response.json()["access_token"]
    with get_db() as db:
        if not check_shop(shop):
            db.execute("INSERT INTO shops (shop, access_token, scope, installed_at) VALUES (?, ?, ?, ?)", (shop, access_token, APP_SCOPES, datetime.now()))
            db.commit()
    
    decoded_host = decode_host(host)
    return redirect(f"https://{decoded_host}/apps/{APP_CLIENT_ID}/")

# API Endpoints
@app.route("/api/hello")
def hello():
    return jsonify({"message": "Hello, this is from backend!"})

# Frontend
@app.route('/', defaults={'path': ''})
@app.route('/<string:path>')
@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory(app.static_folder, 'index.html')

# Webhooks
@app.route("/webhooks/uninstalled", methods=['POST'])
def uninstalled():
    headers = request.headers
    shop = headers.get("X-Shopify-Shop-Domain")
    if check_shop(shop):
        with get_db() as db:
            db.execute("DELETE FROM shops WHERE shop = ?", (shop,))
            db.commit()
    return jsonify({"message": "Uninstalled"}), 200

# Error Handling
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

# Helper Functions
def check_shop(shop):
    with get_db() as db:
        cursor = db.execute("SELECT * FROM shops WHERE shop = ?", (shop,))
        shop = cursor.fetchone()
        return shop is not None

def decode_host(host):
    import base64
    try:
        host_padded = host + '=' * (4 - len(host) % 4) if len(host) % 4 else host
        decoded_host = base64.b64decode(host_padded).decode('utf-8')
        return decoded_host
    except Exception as e:
        print(f"Base64 decode error: {e}")
        return None

def verify_hmac(args, received_hmac):
    sorted_params = "&".join(
        f"{k}={v}" for k, v in sorted(args.items()) if k != "hmac"
    )
    calculated_hmac = hmac_lib.new(
        APP_CLIENT_SECRET.encode('utf-8'),
        sorted_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac_lib.compare_digest(received_hmac, calculated_hmac)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
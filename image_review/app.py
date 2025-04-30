#!/usr/bin/env python3
"""
Flask mini-service that

  • lists JPEGs in ./images/
  • serves them to a front-end
  • uploads a chosen file to Google Drive when /api/upload/<file> is hit

First run asks for Drive consent; token.json then keeps a refresh token so
future runs start silently.
"""

from flask import Flask, jsonify, send_from_directory
import pathlib, mimetypes, os, json

# ──────────────── Paths ────────────────
BASE_DIR   = pathlib.Path(__file__).resolve().parent
IMG_DIR    = BASE_DIR / "images"
STATIC_DIR = BASE_DIR / "static"
CREDS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

# ─── Google Drive client ─────────────────────────────────────────────
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from json import JSONDecodeError

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service() -> "googleapiclient.discovery.Resource":
    """Return an authorized Drive service; handle every edge-case gracefully."""
    creds = None

    # 1) Try existing token
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except (JSONDecodeError, RefreshError, ValueError):
            print("[oauth] token.json invalid or revoked → deleting")
            TOKEN_FILE.unlink(missing_ok=True)
            creds = None

    # 2) If no valid creds, run OAuth
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        try:
            # Preferred: automatic browser popup (needs a free port)
            creds = flow.run_local_server(port=8899, open_browser=True)
        except OSError:
            # Port blocked → fall back to manual copy-paste
            print("[oauth] Port 8899 blocked; switching to console flow")
            creds = flow.run_console()
        TOKEN_FILE.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)

drive = get_drive_service()

# ─── Flask app ───────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path=""
)

@app.route("/")
def root():
    return app.send_static_file("index.html")

@app.route("/api/images")
def list_images():
    """List *.jpg files (sorted) in ./images/."""
    files = sorted(p.name for p in IMG_DIR.glob("*.jpg"))
    print("[api] list_images →", len(files), "files")
    return jsonify(files)

@app.route("/images/<path:fname>")
def img_file(fname):
    """Serve a raw JPEG."""
    return send_from_directory(IMG_DIR, fname)

@app.route("/api/upload/<path:fname>", methods=["POST"])
def upload(fname):
    """Upload the given file to Google Drive."""
    fpath = IMG_DIR / fname
    if not fpath.exists():
        return {"error": "file not found"}, 404

    mime_type = mimetypes.guess_type(fname)[0] or "image/jpeg"
    media     = MediaFileUpload(fpath, mimetype=mime_type, resumable=False)
    file_meta = {"name": fname}                # add "parents": ["<folder-ID>"] to target a folder

    try:
        drive.files().create(body=file_meta, media_body=media).execute()
        return {"uploaded": fname}
    except Exception as e:
        return {"error": str(e)}, 500

# ─── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    IMG_DIR.mkdir(exist_ok=True)
    PORT = 8181                       # <-- change here if you want a different port
    app.run(host="0.0.0.0", port=PORT, debug=True)

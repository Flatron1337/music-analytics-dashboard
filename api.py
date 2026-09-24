import os
from flask import Flask, jsonify
from flask_cors import CORS

from api_routes.analytics import analytics_bp
from api_routes.artists import artists_bp
from api_routes.auth_sync import auth_sync_bp
from api_routes.enrich_export import enrich_export_bp
from api_routes.graph import graph_bp
from api_routes.state import get_dataset

app = Flask(__name__)
CORS(app)

app.register_blueprint(analytics_bp)
app.register_blueprint(artists_bp)
app.register_blueprint(graph_bp)
app.register_blueprint(auth_sync_bp)
app.register_blueprint(enrich_export_bp)


@app.route("/", methods=["GET"])
def index():
    df = get_dataset()
    return jsonify({
        "service": "Music Analytics REST API (Yandex Music)",
        "status": "online",
        "tracks_loaded": len(df) if df is not None else 0,
        "is_ready": df is not None and not df.empty,
        "endpoints": [
            "/api/health",
            "/api/overview",
            "/api/genres",
            "/api/timeline",
            "/api/tracks",
            "/api/auth/device-code",
            "/api/auth/poll-token",
            "/api/sync-likes",
            "/api/sync-likes/stream",
            "/api/export-playlist",
            "/api/artist",
            "/api/collaborations-graph",
            "/api/collaborations-graph/export-html",
            "/api/enrich-genres/status",
            "/api/enrich-genres/stream",
            "/api/track-stream/<track_id>",
            "/api/duplicates",
            "/api/audio-features",
            "/api/genre-cache/download",
        ],
    })


@app.route("/api/health", methods=["GET"])
def health():
    df = get_dataset()
    return jsonify({
        "status": "ok",
        "service": "Music Analytics REST API",
        "tracks_loaded": len(df) if df is not None else 0,
        "is_ready": df is not None and not df.empty,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    print("=" * 60, flush=True)
    print(" 🚀 MUSIC ANALYTICS FLUTTER REST API", flush=True)
    print(f" 🌐 Локально:    http://{host}:{port}", flush=True)
    print(f" 📱 Для Android: http://10.0.2.2:{port} (эмулятор)", flush=True)
    print("=" * 60, flush=True)
    app.run(host=host, port=port, debug=False)

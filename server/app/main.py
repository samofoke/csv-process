from flask import Flask, jsonify, request, make_response
from flask_cors import CORS, cross_origin
from strawberry.flask.views import GraphQLView
from app.config.db.connection import init_pool, ping
from app.models.schema import schema 


ALLOWED_ORIGIN = "http://localhost:5173"

def create_app():
    app = Flask(__name__)

    CORS(
        app,
        resources={r"/graphql": {"origins": [ALLOWED_ORIGIN]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Accept"],
        methods=["GET", "POST", "OPTIONS"],
    )

    init_pool()

    app.add_url_rule(
        "/graphql",
        view_func=GraphQLView.as_view(
            "graphql_view",
            schema=schema,
            graphiql=True,
            multipart_uploads_enabled=True,
        ),
        methods=["GET", "POST", "OPTIONS"],
    )

    @app.before_request
    def _graphql_preflight():
        if request.method == "OPTIONS" and request.path == "/graphql":
            resp = make_response("", 204)
            resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            req_headers = request.headers.get(
                "Access-Control-Request-Headers", "content-type,accept"
            )
            resp.headers["Access-Control-Allow-Headers"] = req_headers
            resp.headers["Access-Control-Max-Age"] = "86400"
            return resp
        return None

    # Optional: ensure CORS headers on normal responses too
    @app.after_request
    def _cors_headers(resp):
        if request.path == "/graphql":
            resp.headers.setdefault("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            resp.headers.setdefault("Vary", "Origin")
            resp.headers.setdefault("Access-Control-Allow-Credentials", "true")
        return resp

    @app.get("/health")
    def health_check():
        ok = ping()
        return jsonify(status=("ok" if ok else "degraded"), db=ok), (200 if ok else 503)

    return app


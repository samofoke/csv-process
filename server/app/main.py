from flask import Flask, jsonify
from flask_cors import CORS
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

    @app.get("/health")
    def health_check():
        ok = ping()
        return jsonify(status=("ok" if ok else "degraded"), db=ok), (200 if ok else 503)

    return app

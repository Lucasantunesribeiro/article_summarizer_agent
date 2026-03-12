#!/usr/bin/env python3
"""WSGI entrypoint for the Flask application."""

from __future__ import annotations

import os

from presentation.app_factory import create_app

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=debug, threaded=True)

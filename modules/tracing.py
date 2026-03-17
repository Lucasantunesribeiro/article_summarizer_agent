"""OpenTelemetry tracing setup.

Call setup_tracing(app) from the Flask app factory before registering blueprints.
Set OTEL_ENABLED=true to activate. No-op if the env var is not set or if the
opentelemetry packages are not installed.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def setup_tracing(app=None) -> None:
    """Configure OpenTelemetry SDK and instrument Flask + SQLAlchemy.

    Args:
        app: Flask application instance. Pass before registering blueprints so
             FlaskInstrumentor can wrap the request context correctly.
    """
    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "opentelemetry packages not installed — tracing disabled. "
            "Install with: pip install opentelemetry-sdk opentelemetry-api "
            "opentelemetry-instrumentation-flask opentelemetry-instrumentation-sqlalchemy "
            "opentelemetry-exporter-otlp-proto-grpc"
        )
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "article-summarizer")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OTel OTLP exporter configured → %s", otlp_endpoint)
    except Exception as exc:
        logger.warning("OTel OTLP exporter setup failed: %s — traces will not be exported.", exc)

    trace.set_tracer_provider(provider)

    if app is not None:
        try:
            FlaskInstrumentor().instrument_app(app)
            logger.info("OTel Flask instrumentation active.")
        except Exception as exc:
            logger.warning("OTel Flask instrumentation failed: %s", exc)

    try:
        SQLAlchemyInstrumentor().instrument()
        logger.info("OTel SQLAlchemy instrumentation active.")
    except Exception as exc:
        logger.warning("OTel SQLAlchemy instrumentation failed: %s", exc)

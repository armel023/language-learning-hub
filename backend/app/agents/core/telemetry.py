import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic_ai import Agent
from pydantic_ai.models.instrumented import InstrumentationSettings

from app.config import Settings

logger = logging.getLogger(__name__)

_configured = False


def configure_telemetry(settings: Settings) -> None:
    """Send agent traces (prompts, tool calls, token usage) to a self-hosted OTLP backend.

    With no OTEL_EXPORTER_OTLP_ENDPOINT set, agents still run and token usage is still recorded
    in ai_runs; only the trace export is skipped.
    """
    global _configured
    if _configured:
        return
    _configured = True

    if not settings.otel_exporter_otlp_endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set; agent tracing export disabled")
        return

    # Imported lazily so the app still starts if the optional Phoenix integration is missing.
    from openinference.instrumentation.pydantic_ai import OpenInferenceSpanProcessor

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.otel_service_name}))
    # Order matters: the OpenInference processor rewrites Pydantic AI's gen_ai.* spans into the
    # attributes Phoenix renders (LLM/tool/agent views, token counts) before they are exported.
    provider.add_span_processor(OpenInferenceSpanProcessor())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)))
    trace.set_tracer_provider(provider)

    Agent.instrument_all(
        InstrumentationSettings(tracer_provider=provider, include_content=settings.otel_include_content)
    )
    logger.info("Agent tracing exported to %s", settings.otel_exporter_otlp_endpoint)

"""
Gemini Summarizer — Google Gemini API Integration
==================================================

Generates high-quality article summaries using Google Gemini via the
google-genai SDK (>= 1.x).

Configuration (env vars):
    GEMINI_API_KEY    — required; your Gemini API key.
    GEMINI_MODEL_ID   — default: gemini-2.5-flash-preview-05-20
                        Override with any model available in your project.
                        Refer to the official model list:
                        https://ai.google.dev/gemini-api/docs/models

Usage:
    from modules.gemini_summarizer import GeminiSummarizer
    summarizer = GeminiSummarizer()
    result = summarizer.summarize(processed_data, length="medium")

Note on preview models:
    Model IDs ending in -preview may change. Always validate the model ID
    against the API docs for your region and plan.
"""

from __future__ import annotations

import logging
import textwrap

from config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SDK import — fails loudly if google-genai is not installed
# ---------------------------------------------------------------------------
try:
    import google.genai as genai  # type: ignore[import]
    from google.genai import types as genai_types  # type: ignore[import]

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a professional article summariser.
    Your task is to produce a clear, factual, and neutral summary of the
    provided article text. Do not add opinions or information not present
    in the original text.
""")

_LENGTH_INSTRUCTIONS: dict[str, str] = {
    "short":  "Write a concise summary in 2–3 sentences.",
    "medium": "Write a balanced summary in 4–6 sentences covering the main points.",
    "long":   "Write a detailed summary in 8–10 sentences preserving key details.",
}


class GeminiSummarizer:
    """Summarise text using the Google Gemini API."""

    def __init__(self) -> None:
        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-genai is required for Gemini summarisation. "
                "Install with: pip install 'google-genai>=1.0.0'"
            )

        api_key = config.gemini.api_key
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Obtain a key at https://aistudio.google.com/app/apikey"
            )

        self._client = genai.Client(api_key=api_key)
        self._model_id = config.gemini.model_id
        logger.info("GeminiSummarizer initialised with model %r", self._model_id)

    def summarize(
        self, processed_data: dict, length: str | None = None
    ) -> dict:
        """Generate a summary from processed text data.

        Args:
            processed_data: Output from TextProcessor.process_text().
            length: "short" | "medium" | "long" (overrides config if given).

        Returns:
            Dict with keys: summary, method_used, model_name, input_chars,
            output_chars, usage.
        """
        summary_length = length or config.summarization.summary_length
        length_instruction = _LENGTH_INSTRUCTIONS.get(
            summary_length, _LENGTH_INSTRUCTIONS["medium"]
        )

        clean_text: str = processed_data.get("clean_text", "")
        if not clean_text.strip():
            sentences = processed_data.get("sentences", [])
            clean_text = " ".join(sentences)

        if not clean_text.strip():
            raise ValueError("No text available for summarisation.")

        # Truncate to avoid large billing surprises
        truncated = clean_text[: config.gemini.max_input_chars]
        if len(clean_text) > config.gemini.max_input_chars:
            logger.info(
                "Input truncated from %d to %d chars for Gemini",
                len(clean_text),
                config.gemini.max_input_chars,
            )

        prompt = (
            f"{_SYSTEM_PROMPT}\n"
            f"{length_instruction}\n\n"
            f"Article text:\n\n{truncated}"
        )

        logger.info(
            "Requesting Gemini summary — model=%r length=%r chars=%d",
            self._model_id,
            summary_length,
            len(truncated),
        )

        try:
            response = self._client.models.generate_content(
                model=self._model_id,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=config.gemini.max_output_tokens,
                    temperature=config.gemini.temperature,
                ),
            )
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            raise

        summary_text = response.text.strip() if response.text else ""
        if not summary_text:
            raise ValueError("Gemini returned an empty response.")

        # Usage metadata (may be None depending on SDK version)
        usage: dict = {}
        try:
            meta = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(meta, "prompt_token_count", None),
                "candidates_tokens": getattr(meta, "candidates_token_count", None),
                "total_tokens": getattr(meta, "total_token_count", None),
            }
        except Exception:
            pass

        logger.info(
            "Gemini summary complete — %d output chars, usage=%s",
            len(summary_text),
            usage,
        )

        return {
            "summary": summary_text,
            "method_used": "generative",
            "model_name": self._model_id,
            "input_chars": len(truncated),
            "output_chars": len(summary_text),
            "usage": usage,
        }

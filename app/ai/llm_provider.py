"""LLM provider abstraction.

This module defines a minimal wrapper around a large language model API for
translating natural language problem descriptions into formal optimisation
models.  It uses Pydantic for input validation and JSON schema parsing,
Tenacity for automatic retries, and returns structured model definitions.

The default implementation calls OpenAI's chat completion API but can be
swapped out for other providers by implementing the same interface.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import openai  # type: ignore
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError


class TranslationRequest(BaseModel):
    """Request payload for the LLM translation.

    Attributes:
        prompt: Natural language description of the optimisation problem.
        domain: Optional domain hint (e.g. "supply_chain", "scheduling").
        output_format: Desired output format ("json" or "pyomo").
    """

    prompt: str = Field(..., description="Natural language description of the optimisation problem.")
    domain: Optional[str] = Field(None, description="Optional domain hint (e.g. supply_chain, scheduling).")
    output_format: str = Field("json", description="Output format for the generated model (json or pyomo).")


class LLMProvider:
    """Wrapper around an LLM for translating optimisation problems.

    This class is responsible for constructing prompts, invoking the
    underlying LLM, handling retries, and parsing the returned JSON into
    Python dictionaries.  Downstream callers should catch ``RuntimeError``
    raised by ``translate_to_model`` to handle failures gracefully.
    """

    def __init__(
        self,
        model_name: str = "gpt-4-1106-preview",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        # Allow passing API key explicitly or via environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        openai.api_key = self.api_key

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(3))
    def _call_openai(self, messages: list[dict[str, str]]) -> str:
        """Internal helper to call OpenAI's chat completion API with retries.

        This method returns the content of the first choice.  Retries are
        handled via ``tenacity``.  If the API call repeatedly fails, a
        ``RetryError`` will be raised and caught by the caller.
        """
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
        )
        return response["choices"][0]["message"]["content"]

    def translate_to_model(self, request: TranslationRequest) -> Dict[str, Any]:
        """Translate a natural language problem description into a model.

        Args:
            request: The translation request containing the prompt, domain and
                desired output format.

        Returns:
            A dictionary representation of the optimisation model.  This
            dictionary should conform to the model JSON schema used by the
            platform (see README for an example).

        Raises:
            RuntimeError: If the LLM call fails or the response cannot be
                parsed as valid JSON.
        """
        system_prompt = (
            "You are an optimisation modelling assistant. Given a natural "
            "language description of an optimisation problem, you will output "
            "a JSON object that defines the optimisation model. The JSON must "
            "include keys: name, type, decision_variables, objective, constraints, "
            "and metadata. Do not include any explanatory text."
        )

        user_content = (
            f"Domain: {request.domain}\n"
            f"Output format: {request.output_format}\n"
            f"Problem description: {request.prompt}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            raw_response = self._call_openai(messages)
        except RetryError as exc:
            raise RuntimeError(f"LLM translation failed after retries: {exc}") from exc

        # Attempt to parse the model JSON
        try:
            model_json: Dict[str, Any] = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM response could not be parsed as JSON: {exc}\nResponse: {raw_response}") from exc

        # Optional: validate required fields exist
        required_keys = {"name", "type", "decision_variables", "objective", "constraints"}
        missing = required_keys - model_json.keys()
        if missing:
            raise RuntimeError(f"Translated model is missing required keys: {', '.join(sorted(missing))}")

        return model_json

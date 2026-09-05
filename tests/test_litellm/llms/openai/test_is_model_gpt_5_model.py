"""
Regression tests for is_model_gpt_5_model() in both OpenAI and Azure GPT-5 config
classes.

Background
----------
In v1.82.3 a substring check was introduced::

    return "gpt-5" in model and "gpt-5-chat" not in model

This inadvertently treated versioned chat models like ``gpt-5.3-chat`` and
``gpt-5.1-chat`` as *non*-GPT-5 models, because the string ``"gpt-5-chat"`` is
a substring of ``"gpt-5.3-chat"``.  Those models were then routed through the
regular Azure chat path which does not suppress ``parallel_tool_calls``, causing
Azure to return ``finish_reason="stop"`` together with tool_calls and breaking
n8n AI-agent workflows.

There are two distinct families:

* **gpt-5-chat family** (``gpt-5-chat``, ``gpt-5-chat-latest``,
  ``gpt-5-chat-2025-08-07``, …) — regular chat models that support ``temperature``
  and ``tool_choice`` but NOT ``reasoning_effort``.  Must NOT be on the GPT-5
  reasoning path.

* **Versioned chat models** (``gpt-5.1-chat``, ``gpt-5.2-chat``,
  ``gpt-5.3-chat``, …) — ARE GPT-5 reasoning models and must stay on the GPT-5
  path.

The fix uses a prefix check (``startswith("gpt-5-chat")``) on the normalised model
name instead of a substring check, which correctly distinguishes the two families.
"""

import pytest

from litellm.llms.openai.chat.gpt_5_transformation import OpenAIGPT5Config
from litellm.llms.azure.chat.gpt_5_transformation import AzureOpenAIGPT5Config

# ---------------------------------------------------------------------------
# Parametrized fixtures
# ---------------------------------------------------------------------------

# Models that MUST be classified as GPT-5 (routed through GPT-5 reasoning path)
GPT5_MODELS = [
    "gpt-5",
    "gpt-5.1",
    "gpt-5.2",
    "gpt-5.3",
    "gpt-5.4",
    "gpt-5.5",
    "gpt-5.5-pro",
    "gpt-5.5-2026-04-23",  # dated variant
    "gpt-5.5-pro-2026-04-23",  # dated variant
    "gpt-5.6",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-6",
    "gpt-6-astra",  # the only gpt-6 id OpenAI serves today
    "gpt-5.1-chat",  # versioned chat — THE KEY REGRESSION CASE
    "gpt-5.2-chat",  # versioned chat — also a regression case
    "gpt-5.3-chat",  # versioned chat — THE KEY REGRESSION CASE
    "gpt-5.2-chat-latest",  # versioned chat with date suffix
    "gpt-5.1-codex",
    "gpt-5.1-codex-mini",
    "gpt-5.1-mini",
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-5-codex",
]

# Models that must NOT be classified as GPT-5 (regular chat path)
NON_GPT5_MODELS = [
    "gpt-5-chat",  # gpt-5-chat family — regular chat path
    "gpt-5-chat-latest",  # gpt-5-chat family with alias suffix
    "gpt-5-chat-2025-08-07",  # gpt-5-chat family with date suffix
    "gpt-4",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "o1",
    "o3",
    "o3-mini",
]


# ---------------------------------------------------------------------------
# OpenAIGPT5Config
# ---------------------------------------------------------------------------


class TestOpenAIGPT5ConfigIsModelGpt5Model:

    @pytest.mark.parametrize("model", GPT5_MODELS)
    def test_gpt5_models_are_classified_as_gpt5(self, model: str):
        assert OpenAIGPT5Config.is_model_gpt_5_model(
            model
        ), f"Expected '{model}' to be classified as a GPT-5 model"

    @pytest.mark.parametrize("model", NON_GPT5_MODELS)
    def test_non_gpt5_models_are_not_classified_as_gpt5(self, model: str):
        assert not OpenAIGPT5Config.is_model_gpt_5_model(
            model
        ), f"Expected '{model}' NOT to be classified as a GPT-5 model"

    def test_versioned_chat_models_are_not_excluded_by_prefix(self):
        """Core regression guard: gpt-5-chat prefix must not match versioned models."""
        versioned_chat_models = ["gpt-5.1-chat", "gpt-5.2-chat", "gpt-5.3-chat"]
        for model in versioned_chat_models:
            assert OpenAIGPT5Config.is_model_gpt_5_model(
                model
            ), f"Regression: '{model}' was incorrectly excluded from GPT-5 path"

    def test_gpt5_chat_family_is_excluded(self):
        """gpt-5-chat family should stay on the regular chat path."""
        for model in ["gpt-5-chat", "gpt-5-chat-latest", "gpt-5-chat-2025-08-07"]:
            assert not OpenAIGPT5Config.is_model_gpt_5_model(
                model
            ), f"Expected '{model}' (gpt-5-chat family) NOT to be on the GPT-5 path"


# Models that are gpt-5.4 or newer. main.py gates the automatic switch to the
# /v1/responses bridge (when reasoning_effort is set and tools are passed) on
# is_model_gpt_5_4_plus_model, so the gpt-5.6 family must land on the True side.
GPT5_4_PLUS_MODELS = [
    "gpt-5.4",
    "gpt-5.5",
    "gpt-5.5-pro",
    "gpt-5.6",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "openai/gpt-5.6-sol",
    "gpt-6-astra",
    "openai/gpt-6-astra",
]

GPT5_PRE_5_4_MODELS = [
    "gpt-5",
    "gpt-5.1",
    "gpt-5.2",
    "gpt-5.3",
    "gpt-5.3-chat",
    "gpt-4o",
]


class TestOpenAIGPT5ConfigIsModelGpt54PlusModel:

    @pytest.mark.parametrize("model", GPT5_4_PLUS_MODELS)
    def test_gpt5_4_plus_models_are_classified_as_5_4_plus(self, model: str):
        assert OpenAIGPT5Config.is_model_gpt_5_4_plus_model(
            model
        ), f"Expected '{model}' to be classified as gpt-5.4-or-newer"

    @pytest.mark.parametrize("model", GPT5_PRE_5_4_MODELS)
    def test_pre_5_4_models_are_not_classified_as_5_4_plus(self, model: str):
        assert not OpenAIGPT5Config.is_model_gpt_5_4_plus_model(
            model
        ), f"Expected '{model}' NOT to be classified as gpt-5.4-or-newer"


# ---------------------------------------------------------------------------
# AzureOpenAIGPT5Config
# ---------------------------------------------------------------------------


class TestAzureOpenAIGPT5ConfigIsModelGpt5Model:

    @pytest.mark.parametrize("model", GPT5_MODELS)
    def test_gpt5_models_are_classified_as_gpt5(self, model: str):
        assert AzureOpenAIGPT5Config.is_model_gpt_5_model(
            model
        ), f"Expected Azure '{model}' to be classified as a GPT-5 model"

    @pytest.mark.parametrize("model", NON_GPT5_MODELS)
    def test_non_gpt5_models_are_not_classified_as_gpt5(self, model: str):
        assert not AzureOpenAIGPT5Config.is_model_gpt_5_model(
            model
        ), f"Expected Azure '{model}' NOT to be classified as a GPT-5 model"

    def test_versioned_chat_models_are_not_excluded_by_prefix(self):
        """Core regression guard: gpt-5-chat prefix must not match versioned models."""
        versioned_chat_models = ["gpt-5.1-chat", "gpt-5.2-chat", "gpt-5.3-chat"]
        for model in versioned_chat_models:
            assert AzureOpenAIGPT5Config.is_model_gpt_5_model(
                model
            ), f"Regression: Azure '{model}' was incorrectly excluded from GPT-5 path"

    def test_gpt5_chat_family_is_excluded(self):
        """gpt-5-chat family should stay on the regular chat path."""
        for model in ["gpt-5-chat", "gpt-5-chat-latest", "gpt-5-chat-2025-08-07"]:
            assert not AzureOpenAIGPT5Config.is_model_gpt_5_model(
                model
            ), f"Expected Azure '{model}' (gpt-5-chat family) NOT to be on the GPT-5 path"

    def test_gpt5_series_routing_prefix_is_always_classified_as_gpt5(self):
        """Models using the gpt5_series/ manual-routing prefix must always match."""
        series_models = ["gpt5_series/my-deployment", "gpt5_series/prod"]
        for model in series_models:
            assert AzureOpenAIGPT5Config.is_model_gpt_5_model(
                model
            ), f"Azure '{model}' with gpt5_series/ prefix should be classified as GPT-5"


# ---------------------------------------------------------------------------
# gpt-6
# ---------------------------------------------------------------------------


class TestGpt6IsHandledAsTheReasoningFamily:
    """gpt-6 must inherit the gpt-5 request handling, not the plain chat path.

    The classification above is not the point in itself — these are the two
    request-shaping decisions that hang off it, and they are what a caller
    actually hits. OpenAI rejects `max_tokens` for gpt-6-astra outright
    ("Unsupported parameter: 'max_tokens' is not supported with this model.
    Use 'max_completion_tokens' instead."), and rejects any `temperature`
    other than the default. Both verified against the live API on 5 Sep 2026.

    Before gpt-6 was added to GPT_REASONING_SERIES_MARKERS these tests failed:
    the name matched no marker, the model fell to the plain chat path, and
    every caller passing max_tokens got a 400 from OpenAI.
    """

    def test_max_tokens_is_rewritten_to_max_completion_tokens(self):
        """Go through get_optional_params, the path a real request takes.

        Calling OpenAIGPT5Config().map_openai_params() directly would pass
        even unpatched -- that class always rewrites. What broke is that
        gpt-6 never reached it.
        """
        from litellm.utils import get_optional_params

        params = get_optional_params(
            model="gpt-6-astra", custom_llm_provider="openai", max_tokens=10
        )
        assert params["max_completion_tokens"] == 10
        assert "max_tokens" not in params

    def test_non_default_temperature_is_dropped(self):
        """OpenAI 400s any temperature but the default, so it must not be sent."""
        from litellm.utils import get_optional_params

        params = get_optional_params(
            model="gpt-6-astra",
            custom_llm_provider="openai",
            temperature=0.2,
            drop_params=True,
        )
        assert "temperature" not in params

    def test_gpt_5_chat_exclusion_does_not_leak_into_gpt_6(self):
        """The gpt-5-chat carve-out is keyed on a gpt-5 prefix only."""
        assert OpenAIGPT5Config.is_model_gpt_5_model("gpt-6-chat")


class TestGpt6AstraIsPriced:
    """A model missing from the cost map logs spend at $0 and nobody notices.

    Read the bundled JSON rather than litellm.model_cost: with
    LITELLM_LOCAL_MODEL_COST_MAP unset, litellm fetches the map over the
    network at import and the assertions would pass on upstream's copy
    while this file stayed empty. Our deployment sets that flag to True,
    so the bundled file is the only thing it ever reads.
    """

    def test_gpt_6_astra_has_openai_pricing_and_context_window(self):
        import json
        from pathlib import Path

        import litellm

        bundled = (
            Path(litellm.__file__).parent / "model_prices_and_context_window_backup.json"
        )
        spec = json.loads(bundled.read_text())["gpt-6-astra"]
        assert spec["litellm_provider"] == "openai"
        assert spec["input_cost_per_token"] == 1e-05
        assert spec["output_cost_per_token"] == 5e-05
        assert spec["max_input_tokens"] == 922000
        assert spec["supports_reasoning"] is True

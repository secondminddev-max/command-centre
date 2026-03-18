"""
claudekit.py — ClaudeKit Pro Python Utility Library
====================================================
Drop-in utilities for Claude API builders.
Requires: anthropic >= 0.25.0

Usage:
    from claudekit import ClaudeKit, ModelBenchmark

    kit = ClaudeKit(api_key="sk-ant-...")
    result = kit.summarise("Long article text here...")
    print(result)
"""

from __future__ import annotations

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Generator, Any

try:
    import anthropic
except ImportError:
    raise ImportError("anthropic package required: pip install anthropic")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cost table (USD per million tokens, as of early 2026 — update as needed)
# ---------------------------------------------------------------------------
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":          {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00},
}

# Friendly aliases
MODEL_ALIASES: dict[str, str] = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-6",
}


def _resolve_model(model: str) -> str:
    return MODEL_ALIASES.get(model, model)


# ---------------------------------------------------------------------------
# Cost Tracker
# ---------------------------------------------------------------------------
@dataclass
class CostTracker:
    """Accumulates token usage and estimated USD cost across API calls."""

    _records: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        label: str = "",
    ) -> float:
        """
        Record a single API call and return the estimated cost in USD.

        Args:
            model:         Model ID or alias (e.g. 'sonnet').
            input_tokens:  Number of input/prompt tokens consumed.
            output_tokens: Number of output/completion tokens produced.
            label:         Optional label for grouping (e.g. task name).

        Returns:
            Estimated cost in USD for this call.
        """
        model = _resolve_model(model)
        rates = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
        entry = {
            "model": model,
            "label": label,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 8),
        }
        self._records.append(entry)
        return cost

    def total_cost(self) -> float:
        """Return total accumulated cost in USD."""
        return round(sum(r["cost_usd"] for r in self._records), 6)

    def total_tokens(self) -> dict[str, int]:
        """Return dict with total input and output token counts."""
        return {
            "input":  sum(r["input_tokens"] for r in self._records),
            "output": sum(r["output_tokens"] for r in self._records),
        }

    def summary(self) -> str:
        """Return a human-readable cost summary."""
        totals = self.total_tokens()
        lines = [
            "─── ClaudeKit Cost Summary ───",
            f"  Calls    : {len(self._records)}",
            f"  Input    : {totals['input']:,} tokens",
            f"  Output   : {totals['output']:,} tokens",
            f"  Total    : ${self.total_cost():.6f} USD",
            "─────────────────────────────",
        ]
        return "\n".join(lines)

    def breakdown(self) -> list[dict[str, Any]]:
        """Return full per-call breakdown."""
        return list(self._records)


# ---------------------------------------------------------------------------
# ClaudeKit — Main Utility Class
# ---------------------------------------------------------------------------
class ClaudeKit:
    """
    Production-ready wrapper around the Anthropic Python SDK.

    Features:
    - Automatic retry with exponential backoff
    - Streaming response helper
    - Token count estimator
    - Integrated cost tracking
    - Ready-to-use prompt template methods
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "sonnet",
        max_tokens: int = 2048,
        tracker: CostTracker | None = None,
    ) -> None:
        """
        Initialise ClaudeKit.

        Args:
            api_key:       Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            default_model: Default model alias or ID (default: 'sonnet').
            max_tokens:    Default max output tokens (default: 2048).
            tracker:       Optional CostTracker instance to share across calls.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = _resolve_model(default_model)
        self.max_tokens = max_tokens
        self.tracker = tracker or CostTracker()

    # ── Core: Retry with Backoff ────────────────────────────────────────────

    def retry_with_backoff(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
        max_retries: int = 4,
        base_delay: float = 1.0,
        label: str = "",
    ) -> str:
        """
        Call the Claude API with automatic exponential-backoff retry on rate
        limit (429) and transient server (5xx) errors.

        Args:
            prompt:      User message content.
            system:      Optional system prompt.
            model:       Model ID or alias. Defaults to self.default_model.
            max_tokens:  Max output tokens. Defaults to self.max_tokens.
            max_retries: Maximum number of retry attempts (default: 4).
            base_delay:  Initial backoff delay in seconds (doubles each retry).
            label:       Cost tracker label for this call.

        Returns:
            The assistant's text response.

        Raises:
            anthropic.RateLimitError: If all retries are exhausted.
            anthropic.APIError:       On non-retryable API errors.
        """
        model = _resolve_model(model) if model else self.default_model
        max_tokens = max_tokens or self.max_tokens
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.messages.create(**kwargs)
                self.tracker.record(
                    model=model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    label=label or prompt[:40],
                )
                return response.content[0].text
            except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
                last_exc = exc
                if attempt == max_retries:
                    break
                delay = base_delay * (2 ** attempt)
                logger.warning("ClaudeKit retry %d/%d after %.1fs — %s", attempt + 1, max_retries, delay, exc)
                time.sleep(delay)
            except anthropic.APIError:
                raise

        raise last_exc  # type: ignore[misc]

    # ── Core: Streaming Response ────────────────────────────────────────────

    def stream_response(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """
        Stream the Claude response token-by-token.

        Args:
            prompt:     User message content.
            system:     Optional system prompt.
            model:      Model ID or alias. Defaults to self.default_model.
            max_tokens: Max output tokens. Defaults to self.max_tokens.

        Yields:
            Text chunks as they arrive from the API.

        Example:
            for chunk in kit.stream_response("Tell me a story"):
                print(chunk, end="", flush=True)
        """
        model = _resolve_model(model) if model else self.default_model
        max_tokens = max_tokens or self.max_tokens
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    # ── Core: Token Estimator ───────────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        """
        Estimate the token count for a string without making an API call.

        Uses the ~4 chars/token heuristic which is accurate to within ~10%
        for English prose. For exact counts, use the Anthropic token-counting
        endpoint on your own infrastructure.

        Args:
            text: The text to estimate token count for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        # Rough heuristic: 4 characters ≈ 1 token for English text
        return max(1, len(text) // 4)

    # ── Prompt Templates ────────────────────────────────────────────────────

    def summarise(
        self,
        text: str,
        style: str = "concise",
        model: str | None = None,
    ) -> str:
        """
        Summarise a body of text.

        Args:
            text:  The text to summarise.
            style: One of 'concise' (3-5 sentences), 'bullets' (bullet list),
                   or 'detailed' (comprehensive paragraph).
            model: Model override.

        Returns:
            Summary string.
        """
        style_instructions = {
            "concise":  "Write a concise summary in 3-5 sentences.",
            "bullets":  "Write a bullet-point summary with 5-7 key points, each on a new line starting with '•'.",
            "detailed": "Write a detailed, comprehensive summary in 2-3 paragraphs covering all key points.",
        }
        instruction = style_instructions.get(style, style_instructions["concise"])

        prompt = f"""{instruction}

TEXT TO SUMMARISE:
\"\"\"
{text}
\"\"\""""

        system = (
            "You are a precise summarisation assistant. Output only the summary — "
            "no preamble, no meta-commentary, no apologies."
        )
        return self.retry_with_backoff(prompt, system=system, model=model, label="summarise")

    def classify(
        self,
        text: str,
        categories: list[str],
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Classify text into one of the provided categories.

        Args:
            text:       The text to classify.
            categories: List of category labels (e.g. ['positive','negative','neutral']).
            model:      Model override.

        Returns:
            Dict with keys 'category' (str) and 'confidence' ('high'|'medium'|'low')
            and 'reasoning' (str).
        """
        cats_formatted = "\n".join(f"- {c}" for c in categories)
        prompt = f"""Classify the following text into EXACTLY ONE of these categories:
{cats_formatted}

TEXT:
\"\"\"
{text}
\"\"\"

Respond with valid JSON only, using this exact structure:
{{
  "category": "<chosen category>",
  "confidence": "<high|medium|low>",
  "reasoning": "<one sentence explanation>"
}}"""

        system = (
            "You are a classification engine. Respond with valid JSON only. "
            "Never include markdown fences or extra text."
        )
        raw = self.retry_with_backoff(prompt, system=system, model=model, label="classify")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"category": raw.strip(), "confidence": "low", "reasoning": "Could not parse JSON response."}

    def extract_structured(
        self,
        text: str,
        schema: dict[str, str],
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract structured data from unstructured text according to a schema.

        Args:
            text:   The source text to extract from.
            schema: Dict mapping field names to descriptions.
                    Example: {"name": "full name", "date": "ISO date of event"}
            model:  Model override.

        Returns:
            Dict with extracted values for each schema key. Missing fields are null.

        Example:
            kit.extract_structured(
                "Meeting with Alice on March 5th at 2pm",
                {"person": "name of attendee", "date": "meeting date", "time": "meeting time"}
            )
            # → {"person": "Alice", "date": "2026-03-05", "time": "14:00"}
        """
        schema_lines = "\n".join(f'  "{k}": "{v}"' for k, v in schema.items())
        null_json = json.dumps({k: None for k in schema.keys()}, indent=2)
        prompt = f"""Extract the following fields from the text below. Return ONLY valid JSON.

FIELDS TO EXTRACT:
{{
{schema_lines}
}}

If a field cannot be found, use null.

TEXT:
\"\"\"
{text}
\"\"\"

JSON output:"""

        system = (
            "You are a structured data extraction engine. "
            "Return valid JSON only. No markdown, no explanation."
        )
        raw = self.retry_with_backoff(prompt, system=system, model=model, label="extract_structured")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("extract_structured: could not parse JSON — returning nulls")
            return json.loads(null_json)


# ---------------------------------------------------------------------------
# ModelBenchmark — Compare Models Side-by-Side
# ---------------------------------------------------------------------------
@dataclass
class BenchmarkResult:
    """Result for a single model in a benchmark run."""

    model: str
    output: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float


class ModelBenchmark:
    """
    Run the same prompt across multiple Claude models and compare results.

    Example:
        bench = ModelBenchmark(api_key="sk-ant-...")
        results = bench.compare_models(
            prompt="Explain quantum entanglement in one paragraph.",
            models=["haiku", "sonnet", "opus"],
        )
        bench.print_report(results)
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_tokens: int = 512,
    ) -> None:
        """
        Args:
            api_key:    Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            max_tokens: Max tokens per model response (keep low for fast benchmarks).
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.max_tokens = max_tokens

    def compare_models(
        self,
        prompt: str,
        models: list[str] | None = None,
        system: str = "",
    ) -> list[BenchmarkResult]:
        """
        Run prompt against multiple models sequentially and collect metrics.

        Args:
            prompt:  The prompt to run against all models.
            models:  List of model aliases or IDs to benchmark.
                     Defaults to ['haiku', 'sonnet', 'opus'].
            system:  Optional system prompt to include.

        Returns:
            List of BenchmarkResult, one per model.
        """
        if models is None:
            models = ["haiku", "sonnet", "opus"]

        results: list[BenchmarkResult] = []

        for alias in models:
            model_id = _resolve_model(alias)
            messages = [{"role": "user", "content": prompt}]
            kwargs: dict[str, Any] = {
                "model": model_id,
                "max_tokens": self.max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system

            t0 = time.perf_counter()
            try:
                response = self.client.messages.create(**kwargs)
            except anthropic.APIError as exc:
                logger.error("ModelBenchmark: %s failed — %s", model_id, exc)
                continue
            latency_ms = (time.perf_counter() - t0) * 1000

            in_tok = response.usage.input_tokens
            out_tok = response.usage.output_tokens
            rates = MODEL_COSTS.get(model_id, {"input": 0.0, "output": 0.0})
            cost = (in_tok * rates["input"] + out_tok * rates["output"]) / 1_000_000

            results.append(BenchmarkResult(
                model=model_id,
                output=response.content[0].text,
                latency_ms=round(latency_ms, 1),
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=round(cost, 8),
            ))

        return results

    def print_report(self, results: list[BenchmarkResult]) -> None:
        """
        Print a formatted comparison table to stdout.

        Args:
            results: List of BenchmarkResult from compare_models().
        """
        divider = "─" * 72
        print(f"\n{'ClaudeKit Pro — Model Benchmark Report':^72}")
        print(divider)
        print(f"{'Model':<36} {'Latency':>10} {'Tokens':>10} {'Cost':>12}")
        print(divider)

        for r in results:
            short = r.model.replace("claude-", "").replace("-20251001", "")
            tokens = f"{r.input_tokens}+{r.output_tokens}"
            print(f"{short:<36} {r.latency_ms:>9.0f}ms {tokens:>10} ${r.cost_usd:>11.6f}")

        print(divider)

        # Fastest
        fastest = min(results, key=lambda r: r.latency_ms)
        cheapest = min(results, key=lambda r: r.cost_usd)
        print(f"  Fastest : {fastest.model} ({fastest.latency_ms:.0f}ms)")
        print(f"  Cheapest: {cheapest.model} (${cheapest.cost_usd:.6f})")
        print()

        # Outputs
        for r in results:
            short = r.model.replace("claude-", "").replace("-20251001", "")
            print(f"\n[{short}] Output:")
            print("  " + r.output.replace("\n", "\n  ")[:500])

        print(f"\n{divider}\n")


# ---------------------------------------------------------------------------
# Quick demo (run: python claudekit.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY to run the demo.")
        raise SystemExit(1)

    print("ClaudeKit Pro — Quick Demo")
    print("=" * 40)

    kit = ClaudeKit(api_key=api_key, default_model="haiku")

    # Summarise
    sample = (
        "Anthropic is an AI safety company founded in 2021. Its flagship product "
        "is Claude, a family of large language models designed with safety at the core. "
        "The company raised over $7 billion in funding by 2024 and focuses heavily on "
        "interpretability research and Constitutional AI techniques."
    )
    print("\n[1] Summarise (bullets):")
    print(kit.summarise(sample, style="bullets"))

    # Classify
    print("\n[2] Classify:")
    result = kit.classify("I can't believe how fast this shipped!", ["positive", "negative", "neutral"])
    print(result)

    # Extract
    print("\n[3] Extract Structured:")
    extracted = kit.extract_structured(
        "Invoice #1042 from Acme Corp, due 2026-04-01, total $4,320.00",
        {"invoice_number": "invoice ID", "vendor": "company name", "due_date": "due date (ISO)", "amount": "total amount"},
    )
    print(json.dumps(extracted, indent=2))

    # Cost summary
    print("\n" + kit.tracker.summary())

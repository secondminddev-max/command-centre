# ClaudeKit Pro

**The missing developer toolkit for Claude API builders.**

Stop reinventing the wheel. ClaudeKit Pro ships you everything you need to build production-grade Claude API integrations from day one: a working Python library, 20+ copy-paste prompt templates, a model benchmark harness, and a polished landing page to understand what you're building.

---

## What's Included

| File | What It Is |
|---|---|
| `claudekit.py` | Production Python utility library |
| `prompts.md` | 20 battle-tested prompt templates across 4 domains |
| `landing.html` | Dark-themed product landing page |
| `README.md` | This file |

---

## Quick Start

### 1. Install the dependency

```bash
pip install anthropic
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Drop `claudekit.py` into your project

```python
from claudekit import ClaudeKit, ModelBenchmark

kit = ClaudeKit()  # reads ANTHROPIC_API_KEY from environment
```

---

## Using `claudekit.py`

### ClaudeKit — Core Methods

#### `retry_with_backoff()`

Calls the Claude API with automatic exponential-backoff retry on rate limits and transient errors.

```python
kit = ClaudeKit(default_model="sonnet")

response = kit.retry_with_backoff(
    prompt="What is the capital of France?",
    system="Answer in one word.",
    max_retries=4,
)
print(response)  # "Paris"
```

#### `stream_response()`

Stream tokens as they arrive — ideal for chat UIs or long-form generation.

```python
for chunk in kit.stream_response("Write a haiku about recursion"):
    print(chunk, end="", flush=True)
```

#### `count_tokens()`

Estimate token count without making an API call.

```python
tokens = kit.count_tokens("Hello, world!")
print(tokens)  # ~3
```

#### `cost_tracker` — Track Spend Per Model

Every API call is automatically recorded. Inspect anytime:

```python
print(kit.tracker.summary())
# ─── ClaudeKit Cost Summary ───
#   Calls    : 12
#   Input    : 8,432 tokens
#   Output   : 1,204 tokens
#   Total    : $0.047320 USD
# ─────────────────────────────
```

---

### Prompt Template Methods

#### `summarise(text, style)`

```python
summary = kit.summarise(article_text, style="bullets")
# style options: "concise" | "bullets" | "detailed"
```

#### `classify(text, categories)`

```python
result = kit.classify(
    "I can't believe how fast this shipped!",
    categories=["positive", "negative", "neutral"]
)
# → {"category": "positive", "confidence": "high", "reasoning": "..."}
```

#### `extract_structured(text, schema)`

```python
data = kit.extract_structured(
    "Invoice #1042 from Acme Corp, due 2026-04-01, total $4,320.00",
    schema={
        "invoice_number": "invoice ID",
        "vendor": "company name",
        "due_date": "due date in ISO format",
        "amount": "total dollar amount",
    }
)
# → {"invoice_number": "1042", "vendor": "Acme Corp", "due_date": "2026-04-01", "amount": "$4,320.00"}
```

---

### ModelBenchmark — Compare Models

Run the same prompt across Haiku, Sonnet, and Opus and get latency + cost side-by-side:

```python
from claudekit import ModelBenchmark

bench = ModelBenchmark()
results = bench.compare_models(
    prompt="Explain what a transformer is in one paragraph.",
    models=["haiku", "sonnet", "opus"],
)
bench.print_report(results)
```

Example output:

```
              ClaudeKit Pro — Model Benchmark Report
────────────────────────────────────────────────────────────────────────
Model                                Latency     Tokens         Cost
────────────────────────────────────────────────────────────────────────
haiku-4-5-20251001                      812ms    142+198   $0.000906
sonnet-4-6                             1340ms    142+201   $0.003441
opus-4-6                               2890ms    142+214   $0.018180
────────────────────────────────────────────────────────────────────────
  Fastest : claude-haiku-4-5-20251001 (812ms)
  Cheapest: claude-haiku-4-5-20251001 ($0.000906)
```

---

## Prompt Templates (`prompts.md`)

20 production-tested prompts across 4 domains. Open the file, find the category you need, copy the template, replace `{{placeholders}}`, and send.

| Domain | Prompts |
|---|---|
| **Coding** | Code review, refactor, explain, debug, write tests |
| **Writing** | Summarise, rewrite, tone-shift, expand, condense |
| **Data** | Extract, classify, structure, compare, validate |
| **Business** | Generate ideas, critique plan, write email, create checklist, analyse risk |

---

## Model Reference

| Alias | Model ID | Use Case |
|---|---|---|
| `haiku` | claude-haiku-4-5-20251001 | Fast, cheap — classification, extraction, routing |
| `sonnet` | claude-sonnet-4-6 | Best balance — most production workloads |
| `opus` | claude-opus-4-6 | Highest capability — complex reasoning, long-form |

Pass the alias anywhere a model is accepted:

```python
kit = ClaudeKit(default_model="haiku")          # set default
kit.summarise(text, model="opus")               # override per-call
kit.retry_with_backoff(prompt, model="sonnet")  # override per-call
```

---

## Running the Demo

```bash
ANTHROPIC_API_KEY=sk-ant-... python claudekit.py
```

Runs summarise, classify, and extract_structured on sample data and prints the cost summary.

---

## Requirements

- Python 3.9+
- `anthropic >= 0.25.0`

---

*ClaudeKit Pro — Built for builders.*

# ClaudeKit Pro — 20 Battle-Tested Claude Prompt Templates

Copy-paste ready. Replace `{{placeholders}}` with your content.

---

## CODING (5 prompts)

---

### 1. Code Review

**Description:** Get a thorough, opinionated code review focused on correctness, security, and maintainability — not style.

```
You are a senior software engineer performing a code review. Analyse the following code and provide:

1. **Critical Issues** — Bugs, security vulnerabilities, or logic errors that must be fixed.
2. **Warnings** — Suboptimal patterns, potential edge cases, or risky assumptions.
3. **Suggestions** — Non-blocking improvements for readability or maintainability.

Be concise and direct. Reference specific line numbers where possible.

Language: {{language}}

```{{language}}
{{code}}
```
```

---

### 2. Refactor

**Description:** Refactor existing code to be cleaner, faster, or more idiomatic — without changing behaviour.

```
Refactor the following {{language}} code. Requirements:
- Preserve exact functionality and all edge-case behaviour.
- Improve readability, reduce duplication, and apply idiomatic patterns for {{language}}.
- Do NOT add new features.
- After the refactored code, add a brief "Changes Made" section (bullet points only).

Original code:
```{{language}}
{{code}}
```
```

---

### 3. Explain Code

**Description:** Get a plain-English explanation of what a piece of code does — suitable for the target audience.

```
Explain the following {{language}} code to a {{audience_level}} developer.

Cover:
1. What this code does at a high level (1-2 sentences).
2. How it works step by step.
3. Any non-obvious design decisions or gotchas.

Avoid unnecessary jargon. Use analogies if helpful.

```{{language}}
{{code}}
```
```

---

### 4. Debug

**Description:** Diagnose a bug given the code, error message, and observed behaviour.

```
I have a bug in my {{language}} code. Help me find and fix it.

**Error message:**
```
{{error_message}}
```

**Expected behaviour:** {{expected_behaviour}}

**Actual behaviour:** {{actual_behaviour}}

**Code:**
```{{language}}
{{code}}
```

Provide:
1. Root cause diagnosis (1-2 sentences).
2. Fixed code (full corrected snippet).
3. Brief explanation of what the fix does.
```

---

### 5. Write Tests

**Description:** Generate a comprehensive test suite for a function or class.

```
Write a comprehensive test suite for the following {{language}} code using {{test_framework}}.

Requirements:
- Cover the happy path, edge cases, and expected failure modes.
- Each test must have a descriptive name that explains what it verifies.
- Use mocks/stubs where appropriate for external dependencies.
- Include at least one parametrised/table-driven test if applicable.

Code under test:
```{{language}}
{{code}}
```
```

---

## WRITING (5 prompts)

---

### 6. Summarise

**Description:** Condense a long document into a structured, scannable summary.

```
Summarise the following text. Output format:

**TL;DR** (1 sentence)

**Key Points** (5-7 bullet points)

**Conclusion** (2-3 sentences on implications or next steps)

Be factual. Do not add opinions not present in the source.

TEXT:
"""
{{text}}
"""
```

---

### 7. Rewrite for Clarity

**Description:** Rewrite dense or unclear prose to be clear, direct, and easy to read.

```
Rewrite the following text to be clearer and easier to read.

Rules:
- Use shorter sentences (aim for ≤20 words average).
- Replace jargon with plain English where possible.
- Keep all factual content and meaning intact.
- Do NOT add new information.

TEXT:
"""
{{text}}
"""
```

---

### 8. Tone Shift

**Description:** Adjust the tone of a piece of writing — formal ↔ casual, confident ↔ cautious, etc.

```
Rewrite the following text in a {{target_tone}} tone.

Target tone description: {{tone_description}}

Preserve all factual content and key messages. Only change the voice, register, and style.

ORIGINAL TEXT:
"""
{{text}}
"""
```

---

### 9. Expand

**Description:** Expand a short outline, notes, or bullet points into fully-formed prose.

```
Expand the following notes into a fully-written {{content_type}} (e.g. blog post section, email, report paragraph).

Target length: approximately {{target_word_count}} words.
Audience: {{audience}}
Tone: {{tone}}

Keep every idea from the notes. Add supporting detail, transitions, and examples where appropriate.

NOTES:
"""
{{notes}}
"""
```

---

### 10. Condense

**Description:** Cut a piece of writing to a target length without losing the core message.

```
Condense the following text to approximately {{target_word_count}} words.

Prioritise: core argument, key evidence, actionable conclusions.
Cut: repetition, filler phrases, tangential examples.

Do not change the meaning or omit critical information.

TEXT:
"""
{{text}}
"""
```

---

## DATA (5 prompts)

---

### 11. Extract

**Description:** Pull specific fields out of unstructured text and return them as structured JSON.

```
Extract the following fields from the text below. Return valid JSON only — no markdown, no explanation.

Fields:
{{fields_json_schema}}

If a field is not found, use null.

TEXT:
"""
{{text}}
"""
```

---

### 12. Classify

**Description:** Assign a label from a fixed set to each item in a list.

```
Classify each item in the list below into EXACTLY ONE of these categories: {{categories}}.

For each item return a JSON object with:
- "item": the original text
- "category": the assigned category
- "confidence": "high", "medium", or "low"

Return a JSON array. No markdown, no extra text.

ITEMS:
{{items_list}}
```

---

### 13. Structure Unstructured Data

**Description:** Convert a messy, free-form text document into a clean structured format.

```
Convert the following unstructured text into a well-structured {{output_format}} (e.g. JSON / CSV / Markdown table).

Output columns/fields: {{fields}}

Rules:
- Infer missing values as null or empty string.
- Normalise dates to ISO 8601.
- Normalise currency to numeric with 2 decimal places.
- Do not invent data not present in the source.

TEXT:
"""
{{text}}
"""
```

---

### 14. Compare

**Description:** Produce a structured comparison of two or more items across defined dimensions.

```
Compare the following {{item_type}} across these dimensions: {{dimensions}}.

Output as a Markdown table with one row per item and one column per dimension.
After the table, add a 2-3 sentence "Verdict" recommending the best option for {{use_case}} and why.

ITEMS TO COMPARE:
{{items}}
```

---

### 15. Validate

**Description:** Check data for errors, inconsistencies, or violations of specified rules.

```
Validate the following data against these rules:
{{validation_rules}}

For each issue found, return a JSON object with:
- "row" or "field": where the issue is
- "rule": which rule was violated
- "value": the offending value
- "suggestion": how to fix it

Return a JSON array. If no issues are found, return an empty array [].

DATA:
"""
{{data}}
"""
```

---

## BUSINESS (5 prompts)

---

### 16. Generate Ideas

**Description:** Brainstorm a focused list of practical, actionable ideas for a given challenge.

```
Generate {{count}} specific, actionable ideas for the following challenge.

Challenge: {{challenge}}
Constraints: {{constraints}}
Audience / context: {{context}}

For each idea:
1. **Idea name** (3-6 words)
2. One sentence describing the idea.
3. One sentence on why it fits the constraints.

Number your list. Prioritise originality and feasibility over generality.
```

---

### 17. Critique a Plan

**Description:** Get a rigorous, honest critique of a business or project plan.

```
Critique the following plan. Be direct and specific — this is not a validation exercise.

For each major weakness:
- Name the risk or gap.
- Explain why it matters.
- Suggest a concrete mitigation.

Then provide an overall rating (1-10) with a one-sentence justification.

PLAN:
"""
{{plan}}
"""
```

---

### 18. Write a Professional Email

**Description:** Draft a polished professional email from a brief description of the goal and context.

```
Write a professional email based on the following brief.

From: {{sender_name}}, {{sender_role}}
To: {{recipient_name}}, {{recipient_role}}
Goal: {{goal}}
Key points to include: {{key_points}}
Tone: {{tone}} (e.g. formal, friendly-professional, urgent)

Output only the email — subject line first, then body. No meta-commentary.
```

---

### 19. Create a Checklist

**Description:** Turn a vague task or project description into a concrete, ordered action checklist.

```
Create a complete, ordered checklist for the following task or project.

Task: {{task}}
Context: {{context}}

Requirements:
- Each item must be a single, concrete action (verb-first).
- Group related items under section headers.
- Flag any item that has a hard dependency on a previous step with "(depends on #N)".
- Include no more than {{max_items}} items total.
```

---

### 20. Analyse Risk

**Description:** Identify and score risks in a plan, project, or decision.

```
Perform a risk analysis for the following {{subject}}.

For each risk identified:
1. **Risk**: Short name.
2. **Description**: What could go wrong and how.
3. **Likelihood**: High / Medium / Low.
4. **Impact**: High / Medium / Low.
5. **Risk Score**: Likelihood × Impact (HH=Critical, HM/MH=High, MM/HL/LH=Medium, rest=Low).
6. **Mitigation**: One concrete action to reduce likelihood or impact.

List risks in descending order of Risk Score. Identify at least 5 risks.

SUBJECT:
"""
{{subject}}
"""
```

"""
========================================================
  SEO Meta Description Generator
========================================================
  Product:     SEO Meta Description Generator
  Description: Generate 3 optimized SEO meta descriptions
               from a URL or raw text using Claude AI.
               Each option is within the 155-character
               Google-recommended limit.
  Usage:
    python seo_meta_tool.py --url https://example.com
    python seo_meta_tool.py --text "Your page content here..."
    python seo_meta_tool.py --help
  Requirements:
    pip install anthropic requests
    export ANTHROPIC_API_KEY=your_key_here
  Price:       $9 (available on Gumroad)
  Author:      Command Centre / secondmind
========================================================
"""

import argparse
import os
import sys

import anthropic
import requests


def fetch_url_content(url: str) -> str:
    """Fetch page content from a URL and return cleaned text."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; SEOMetaTool/1.0)"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        # Strip script and style blocks
        for tag in ("script", "style", "head"):
            while f"<{tag}" in html.lower():
                start = html.lower().find(f"<{tag}")
                end = html.lower().find(f"</{tag}>", start)
                if end == -1:
                    break
                html = html[:start] + html[end + len(f"</{tag}>"):]

        # Strip all remaining HTML tags
        result = []
        in_tag = False
        for ch in html:
            if ch == "<":
                in_tag = True
            elif ch == ">":
                in_tag = False
                result.append(" ")
            elif not in_tag:
                result.append(ch)

        text = "".join(result)

        # Collapse whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = " ".join(word for line in lines for word in line.split() if word)

        # Trim to a reasonable input size (~3000 chars)
        return text[:3000]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)


def generate_meta_descriptions(content: str, api_key: str) -> list[str]:
    """Call Claude to generate 3 SEO meta descriptions."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "You are an expert SEO copywriter. Based on the content below, "
        "write exactly 3 SEO meta descriptions.\n\n"
        "Rules:\n"
        "- Each must be a single sentence or two short sentences\n"
        "- Each must be 155 characters or fewer (strictly enforced)\n"
        "- Each must be compelling, include a call to action, and target keywords\n"
        "- Output ONLY the 3 descriptions, one per line, no labels, no numbering, "
        "no extra commentary\n\n"
        f"Content:\n{content}"
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    # Keep only first 3 non-empty lines
    return lines[:3]


def display_results(descriptions: list[str]) -> None:
    """Print numbered list with character counts."""
    print("\nGenerated SEO Meta Descriptions:\n" + "─" * 50)
    for i, desc in enumerate(descriptions, start=1):
        count = len(desc)
        flag = " ⚠ over limit" if count > 155 else ""
        print(f"{i}. {desc}")
        print(f"   [{count} chars{flag}]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="seo_meta_tool",
        description=(
            "SEO Meta Description Generator — "
            "produce 3 optimised meta descriptions via Claude AI."
        ),
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--url",
        metavar="URL",
        help="Web page URL to fetch and analyse",
    )
    source.add_argument(
        "--text",
        metavar="TEXT",
        help="Raw text blob to generate descriptions from",
    )

    args = parser.parse_args()

    # API key check
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY environment variable is not set.\n"
            "Export it before running:\n"
            "  export ANTHROPIC_API_KEY=your_key_here",
            file=sys.stderr,
        )
        sys.exit(1)

    # Gather content
    if args.url:
        print(f"Fetching content from: {args.url}")
        content = fetch_url_content(args.url)
    else:
        content = args.text.strip()
        if not content:
            print("Error: --text input is empty.", file=sys.stderr)
            sys.exit(1)

    print("Generating SEO meta descriptions...")
    descriptions = generate_meta_descriptions(content, api_key)

    if not descriptions:
        print("Error: No descriptions returned from API.", file=sys.stderr)
        sys.exit(1)

    display_results(descriptions)


if __name__ == "__main__":
    main()

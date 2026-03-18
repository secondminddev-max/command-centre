#!/usr/bin/env python3
"""
ColdForge — AI-Powered Cold Email Personalizer
Generates 2 personalized cold email variants per lead using Claude AI.
"""

import argparse
import csv
import sys
import time
import os


MOCK_LEADS = [
    {
        "name": "Sarah Chen",
        "company": "Apex Marketing",
        "role": "Head of Growth",
        "website": "apexmarketing.io",
        "pain_point": "scaling outbound without hiring more SDRs",
    },
    {
        "name": "James Okafor",
        "company": "BuildRight SaaS",
        "role": "Founder",
        "website": "buildrightsaas.com",
        "pain_point": "converting free trial users to paid",
    },
    {
        "name": "Emily Torres",
        "company": "NexGen Consulting",
        "role": "Business Development Manager",
        "website": "nexgenconsulting.co",
        "pain_point": "booking more discovery calls from cold outreach",
    },
]

MOCK_EMAILS = {
    "Sarah Chen": (
        "Subject: Scaling outbound at Apex Marketing — without the headcount\n\n"
        "Hi Sarah,\n\n"
        "Most growth teams at companies like Apex Marketing hit the same wall: outbound "
        "results plateau the moment you stop adding reps. You can't clone your best SDR.\n\n"
        "I work with heads of growth who want pipeline without the payroll. One client "
        "went from 20 to 120 qualified meetings/month — same team, different approach.\n\n"
        "Worth a 15-minute call to see if the same applies to Apex?\n\n"
        "Best,\n[Your Name]",
        "Subject: Apex Marketing + outbound scale — quick idea\n\n"
        "Hi Sarah,\n\n"
        "Noticed Apex Marketing is growing fast. The hard part at your stage isn't "
        "generating leads — it's personalizing outreach at volume without burning out your team.\n\n"
        "I've helped similar growth teams 3x their reply rates without adding headcount. "
        "Happy to share exactly how in a quick call.\n\n"
        "Open Thursday or Friday this week?\n\n"
        "— [Your Name]",
    ),
    "James Okafor": (
        "Subject: BuildRight trial → paid conversion — a pattern I keep seeing\n\n"
        "Hi James,\n\n"
        "Founders building in the SaaS space often tell me the same thing: "
        "free trials are full, conversions are stuck. The gap is almost never the product.\n\n"
        "I've helped SaaS founders like you identify the exact moment users disengage "
        "and fix the conversion path. One client lifted paid conversion by 40% in 6 weeks.\n\n"
        "Would love to show you what that looked like — 20 minutes?\n\n"
        "Best,\n[Your Name]",
        "Subject: Quick question about BuildRight's trial flow\n\n"
        "Hi James,\n\n"
        "Love what you're building at BuildRight. One thing I notice with high-growth "
        "SaaS products: trial-to-paid conversion is the lever most founders underinvest in.\n\n"
        "I specialize in exactly this. If you're seeing drop-off at any stage of the "
        "trial, I can probably pinpoint why in under an hour.\n\n"
        "Want to jump on a quick call this week?\n\n"
        "— [Your Name]",
    ),
    "Emily Torres": (
        "Subject: More discovery calls from cold outreach — here's what's working\n\n"
        "Hi Emily,\n\n"
        "BDMs at consulting firms face a brutal equation: cold outreach volume is up, "
        "but reply rates keep dropping. The old playbooks don't cut through anymore.\n\n"
        "I help business development teams at firms like NexGen rebuild their outbound "
        "approach around personalization at scale. One client doubled their discovery "
        "call bookings in 30 days.\n\n"
        "15 minutes to walk through the approach?\n\n"
        "Best,\n[Your Name]",
        "Subject: NexGen Consulting + cold outreach — a quick idea\n\n"
        "Hi Emily,\n\n"
        "Saw NexGen's work — impressive client base. The challenge at your growth stage "
        "is usually not finding prospects, it's getting them to respond.\n\n"
        "I've helped BDMs at similar consulting firms increase cold email reply rates by "
        "3–5x using a combination of AI personalization and sequencing strategy.\n\n"
        "Happy to share the framework — free. Worth a quick chat?\n\n"
        "— [Your Name]",
    ),
}


def build_prompt(lead: dict) -> str:
    return f"""You are an expert cold email copywriter. Generate exactly 2 distinct cold email variants for the following sales lead.

Lead details:
- Name: {lead['name']}
- Company: {lead['company']}
- Role: {lead['role']}
- Website: {lead['website']}
- Pain point: {lead['pain_point']}

Requirements for each email:
- Subject line included (format: "Subject: ...")
- 3–5 sentences max in the body
- Opens with a specific insight about their pain point or company
- One concrete outcome/result (specific numbers if possible)
- Ends with a low-friction CTA (15-minute call, quick chat, etc.)
- No generic filler phrases ("I hope this finds you well", "My name is...")
- Different angle/approach for each variant

Format your response EXACTLY like this:
EMAIL_1_START
[full email 1 here including subject line]
EMAIL_1_END
EMAIL_2_START
[full email 2 here including subject line]
EMAIL_2_END"""


def parse_claude_response(response_text: str) -> tuple[str, str]:
    email1, email2 = "", ""

    if "EMAIL_1_START" in response_text and "EMAIL_1_END" in response_text:
        start = response_text.index("EMAIL_1_START") + len("EMAIL_1_START")
        end = response_text.index("EMAIL_1_END")
        email1 = response_text[start:end].strip()

    if "EMAIL_2_START" in response_text and "EMAIL_2_END" in response_text:
        start = response_text.index("EMAIL_2_START") + len("EMAIL_2_START")
        end = response_text.index("EMAIL_2_END")
        email2 = response_text[start:end].strip()

    return email1, email2


def generate_emails_live(lead: dict, client, model: str) -> tuple[str, str]:
    prompt = build_prompt(lead)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text
    return parse_claude_response(response_text)


def generate_emails_demo(lead: dict) -> tuple[str, str]:
    if lead["name"] in MOCK_EMAILS:
        return MOCK_EMAILS[lead["name"]]
    email1 = (
        f"Subject: Quick idea for {lead['company']}\n\n"
        f"Hi {lead['name'].split()[0]},\n\n"
        f"Most {lead['role']}s I talk to at companies like {lead['company']} are dealing "
        f"with {lead['pain_point']}. It's one of the most common growth blockers at your stage.\n\n"
        f"I've helped similar teams solve this in weeks, not months. Worth a 15-minute call?\n\n"
        f"Best,\n[Your Name]"
    )
    email2 = (
        f"Subject: {lead['company']} — saw something relevant\n\n"
        f"Hi {lead['name'].split()[0]},\n\n"
        f"Noticed {lead['company']} is pushing hard on growth. The biggest friction point "
        f"at this stage is usually {lead['pain_point']} — and it's more fixable than it looks.\n\n"
        f"Happy to share what's worked for similar {lead['role']}s. Quick chat this week?\n\n"
        f"— [Your Name]"
    )
    return email1, email2


def read_leads(input_path: str) -> list[dict]:
    required_columns = {"name", "company", "role", "website", "pain_point"}
    leads = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("ERROR: Input CSV has no headers.", file=sys.stderr)
            sys.exit(1)
        missing = required_columns - set(reader.fieldnames)
        if missing:
            print(
                f"ERROR: Input CSV is missing required columns: {', '.join(sorted(missing))}",
                file=sys.stderr,
            )
            sys.exit(1)
        for i, row in enumerate(reader, start=2):
            lead = {col: row.get(col, "").strip() for col in required_columns}
            empty = [col for col, val in lead.items() if not val]
            if empty:
                print(
                    f"WARNING: Row {i} has empty fields: {', '.join(empty)}. Skipping.",
                    file=sys.stderr,
                )
                continue
            leads.append(lead)
    return leads


def write_output(output_path: str, results: list[dict]) -> None:
    fieldnames = ["name", "company", "personalized_email_1", "personalized_email_2"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def print_progress(current: int, total: int, name: str) -> None:
    pct = int((current / total) * 40)
    bar = "█" * pct + "░" * (40 - pct)
    print(f"\r  [{bar}] {current}/{total} — {name:<30}", end="", flush=True)


def run_demo() -> None:
    print("\n  ColdForge — DEMO MODE (no API key required)\n")
    print("  Generating emails for 3 sample leads...\n")
    results = []
    total = len(MOCK_LEADS)
    for i, lead in enumerate(MOCK_LEADS, start=1):
        print_progress(i, total, lead["name"])
        email1, email2 = generate_emails_demo(lead)
        results.append(
            {
                "name": lead["name"],
                "company": lead["company"],
                "personalized_email_1": email1,
                "personalized_email_2": email2,
            }
        )
        time.sleep(0.2)
    print("\n")

    for r in results:
        print(f"  ── {r['name']} ({r['company']}) ──")
        print(f"\n  VARIANT 1:\n{r['personalized_email_1']}\n")
        print(f"  VARIANT 2:\n{r['personalized_email_2']}\n")
        print("  " + "─" * 60 + "\n")

    print("  Demo complete. Run with --input leads.csv --api-key YOUR_KEY for live generation.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="coldforge",
        description="ColdForge — AI-Powered Cold Email Personalizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tool_v1.py --demo\n"
            "  python tool_v1.py --input leads.csv --output emails.csv --api-key sk-ant-...\n"
            "  python tool_v1.py --input leads.csv --output emails.csv --api-key $ANTHROPIC_API_KEY\n"
        ),
    )
    parser.add_argument(
        "--input", "-i",
        metavar="FILE",
        help="Path to input CSV file (columns: name, company, role, website, pain_point)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        default="emails_output.csv",
        help="Path to output CSV file (default: emails_output.csv)",
    )
    parser.add_argument(
        "--api-key", "-k",
        metavar="KEY",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with sample data — no API key required",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        default="claude-haiku-4-5-20251001",
        help="Claude model to use (default: claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="Seconds to wait between API calls (default: 0.5)",
    )

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.input:
        parser.error("--input is required unless running --demo mode")

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: No API key provided. Use --api-key or set ANTHROPIC_API_KEY env var.\n"
            "       Run with --demo to test without an API key.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print(
            "ERROR: anthropic package not installed.\n"
            "       Run: pip install anthropic",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  ColdForge — AI Cold Email Personalizer")
    print(f"  Model : {args.model}")
    print(f"  Input : {args.input}")
    print(f"  Output: {args.output}\n")

    leads = read_leads(args.input)
    if not leads:
        print("ERROR: No valid leads found in input file.", file=sys.stderr)
        sys.exit(1)

    print(f"  Found {len(leads)} lead(s). Generating emails...\n")

    client = anthropic.Anthropic(api_key=api_key)
    results = []
    errors = []
    total = len(leads)

    for i, lead in enumerate(leads, start=1):
        print_progress(i, total, lead["name"])
        try:
            email1, email2 = generate_emails_live(lead, client, args.model)
            results.append(
                {
                    "name": lead["name"],
                    "company": lead["company"],
                    "personalized_email_1": email1,
                    "personalized_email_2": email2,
                }
            )
        except Exception as e:
            errors.append({"name": lead["name"], "error": str(e)})
            results.append(
                {
                    "name": lead["name"],
                    "company": lead["company"],
                    "personalized_email_1": f"ERROR: {e}",
                    "personalized_email_2": f"ERROR: {e}",
                }
            )

        if i < total:
            time.sleep(args.rate_limit)

    print("\n")

    write_output(args.output, results)

    success = total - len(errors)
    print(f"  Done. {success}/{total} emails generated successfully.")
    if errors:
        print(f"  {len(errors)} error(s):")
        for err in errors:
            print(f"    - {err['name']}: {err['error']}")
    print(f"  Output written to: {args.output}\n")


if __name__ == "__main__":
    main()

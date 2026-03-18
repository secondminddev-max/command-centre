# ColdForge — AI-Powered Cold Email Personalizer

**Generate 100 personalized cold emails in 60 seconds using Claude AI.**

Built for freelancers and sales teams who need high-quality, personalized outreach at scale — without the manual grind.

---

## Installation

```bash
pip install anthropic
```

Python 3.9+ required. No other dependencies.

---

## Usage

### Basic usage

```bash
python tool_v1.py --input leads.csv --output emails.csv --api-key YOUR_ANTHROPIC_KEY
```

### Using environment variable (recommended)

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python tool_v1.py --input leads.csv --output emails.csv
```

### Demo mode (no API key required)

```bash
python tool_v1.py --demo
```

---

## CSV Format

Your input CSV must have exactly these columns (header row required):

| Column      | Description                                      | Example                              |
|-------------|--------------------------------------------------|--------------------------------------|
| `name`      | Lead's full name                                 | Sarah Chen                           |
| `company`   | Company name                                     | Apex Marketing                       |
| `role`      | Lead's job title                                 | Head of Growth                       |
| `website`   | Company website                                  | apexmarketing.io                     |
| `pain_point`| Their main business challenge (1 sentence)       | scaling outbound without more SDRs   |

### Example `leads.csv`

```csv
name,company,role,website,pain_point
Sarah Chen,Apex Marketing,Head of Growth,apexmarketing.io,scaling outbound without hiring more SDRs
James Okafor,BuildRight SaaS,Founder,buildrightsaas.com,converting free trial users to paid
Emily Torres,NexGen Consulting,Business Development Manager,nexgenconsulting.co,booking more discovery calls from cold outreach
```

### Output CSV columns

| Column                | Description                     |
|-----------------------|---------------------------------|
| `name`                | Lead's full name                |
| `company`             | Company name                    |
| `personalized_email_1`| First email variant (with subject line) |
| `personalized_email_2`| Second email variant (different angle)  |

---

## All Options

```
--input,  -i FILE      Input CSV file path (required unless --demo)
--output, -o FILE      Output CSV file path (default: emails_output.csv)
--api-key,-k KEY       Anthropic API key
--demo                 Run demo with sample data, no API key needed
--model  MODEL         Claude model (default: claude-haiku-4-5-20251001)
--rate-limit SECONDS   Delay between API calls (default: 0.5)
```

---

## Demo Mode

Run `--demo` to see example output for 3 sample leads with no API key or CSV required:

```bash
python tool_v1.py --demo
```

This prints 2 email variants per lead directly to stdout so you can evaluate quality before purchasing an API key.

---

## Pricing

- **$29 one-time** — full source code, no subscription, no usage limits beyond your Anthropic API costs
- Claude Haiku API cost: approximately **$0.001 per lead** (2 emails)
- 100 leads ≈ $0.10 in API costs

---

## License

MIT License. Use it, modify it, sell emails with it. No restrictions.

---

*ColdForge uses Anthropic's Claude AI. You need an Anthropic API key from console.anthropic.com.*

# Marketing Campaign Automation System

An end-to-end AI-powered outbound marketing pipeline. Finds leads, enriches contact data, generates personalised cold emails, sends them via SMTP, and tracks responses — all orchestrated through natural language via Claude Desktop.

## What It Does

| Stage | Tool | Description |
|-------|------|-------------|
| Lead Discovery | Apollo.io MCP | Search for companies by location, industry, size |
| Lead Enrichment | `enrich_leads.ps1` / `lead_enricher.py` | Fetch verified emails, LinkedIn, company data |
| Email Validation | `email_validator.py` | Multi-layer syntax + MX + SMTP validation |
| Message Generation | `intelligence/message_generator.py` | AI-crafted personalised cold emails |
| Email Sending | `campaign-mcp` / `email_sender.py` | SSL SMTP batch sending with rate limiting |
| WhatsApp Outreach | `whatsapp-mcp` | Automated WhatsApp follow-up via Go bridge |
| Analytics | `pipeline-dashboard` | Flask dashboard at `localhost:5050` |

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | For the intelligence pipeline & MCP servers |
| Node.js | 18+ | For `apollo-mcp` TypeScript server |
| Go | 1.21+ | For `whatsapp-mcp` bridge binary |
| uv | latest | Python package manager for `campaign-mcp` |
| Claude Desktop | latest | MCP server host |

Install `uv`: https://docs.astral.sh/uv/getting-started/installation/

---

## Quick Setup

### 1. Clone & configure environment

```bash
git clone https://github.com/biyapod-create/marketing-campaign-automation.git
cd marketing-campaign-automation

cp .env.example .env
# Open .env and fill in all values (see Environment Variables section below)
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Apollo MCP server (TypeScript)

```bash
cd apollo-mcp
npm install
npm run build
cd ..
```

### 4. Set up Campaign MCP server (Python)

```bash
cd campaign-mcp
uv sync
cd ..
```

### 5. Set up WhatsApp bridge

```bash
cd whatsapp-mcp/whatsapp-bridge
go build -o whatsapp-bridge .
cd ../..
```

### 6. Configure campaign database

```bash
cp campaign_database.example.json campaign_database.json
# Edit campaign_database.json with your company details, target audience, and pricing
```

---

## Environment Variables

All secrets are loaded from a `.env` file in the project root. **Never commit this file.**

| Variable | Required | Description |
|----------|----------|-------------|
| `APOLLO_IO_API_KEY` | ✅ | Apollo.io API key — [get it here](https://app.apollo.io/#/settings/api) |
| `SMTP_HOST` | ✅ | Your mail server hostname (e.g. `mail.yourdomain.com`) |
| `SMTP_PORT` | ✅ | SMTP port — typically `465` (SSL) or `587` (TLS) |
| `SMTP_USER` | ✅ | Your outgoing email address (e.g. `info@yourdomain.com`) |
| `SMTP_PASS` | ✅ | SMTP password or app-specific password |
| `SENDER_NAME` | ✅ | Display name used in email signatures |
| `SENDER_PHONE` | optional | Phone number for email signatures |
| `SENDER_WEBSITE` | optional | Website URL for email signatures |
| `ANTHROPIC_API_KEY` | ✅ for WhatsApp bot | Claude API key — [get it here](https://console.anthropic.com) |


---

## Running the System

### Pipeline Dashboard (recommended starting point)

```bash
cd pipeline-dashboard
python app.py
```

Open **http://localhost:5050** in your browser. The dashboard lets you manage leads, trigger sends, and view campaign analytics.

---

### Master Orchestrator (natural language interface)

```python
from master_orchestrator import CampaignOrchestrator

campaign = CampaignOrchestrator()

# Find leads
campaign.execute("find 30 SMEs in Lagos that need websites")

# Check status
campaign.status()
```

---

### Email Validation

Validate a single email before sending:

```bash
python email_validator.py info@example.com
```

Validate a full leads CSV (three modes):

```bash
# Light — syntax + MX only (fast)
python validate_leads_workflow.py leads/leads_database.csv --light

# Medium — syntax + MX + basic SMTP ping
python validate_leads_workflow.py leads/leads_database.csv --medium

# Deep — full SMTP handshake validation (slow, most accurate)
python validate_leads_workflow.py leads/leads_database.csv --deep
```

---

### Lead Enrichment Script

The `enrich_leads.ps1` PowerShell script batch-enriches company domains via the Apollo.io API. It loads your API key from `.env` automatically:

```powershell
# Edit the $rawLeads array at the top of enrich_leads.ps1 with your target companies
.\enrich_leads.ps1
```

Output is written to `leads/leads_database.csv`.

---

### Sending Emails

**Dry run first** (logs sends without actually sending — always start here):

```python
from campaign-mcp.main import send_batch_emails

# Dry run — safe to test
result = send_batch_emails(limit=10, dry_run=True)
print(result)
```

**Go live** (set `dry_run=False`):

```python
result = send_batch_emails(limit=10, dry_run=False, delay_seconds=5.0)
```

> ⚠️ Start with small batches (10–20) to warm up your sending domain and avoid spam flags.

---

## Connecting MCP Servers to Claude Desktop

Add both MCP servers to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apollo": {
      "command": "node",
      "args": ["C:/path/to/marketing-campaign-automation/apollo-mcp/dist/index.js"],
      "env": {
        "APOLLO_IO_API_KEY": "your_key_here"
      }
    },
    "campaign": {
      "command": "uv",
      "args": [
        "run",
        "--project", "C:/path/to/marketing-campaign-automation/campaign-mcp",
        "python", "C:/path/to/marketing-campaign-automation/campaign-mcp/main.py"
      ]
    }
  }
}
```

Config file location:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

After saving, restart Claude Desktop. You can then say things like:

> *"Find 20 restaurant businesses in Abuja with no website"*
> *"Send a dry-run batch of 10 emails"*
> *"What's the campaign status?"*

---

## WhatsApp Bot

The WhatsApp MCP server uses a Go bridge to connect to WhatsApp Web.

```bash
# 1. Start the bridge (will show QR code to scan on first run)
cd whatsapp-mcp/whatsapp-bridge
./whatsapp-bridge

# 2. Scan the QR code with your WhatsApp mobile app

# 3. Start the MCP server
cd ../whatsapp-mcp-server
uv run main.py
```

Add to `claude_desktop_config.json`:

```json
"whatsapp": {
  "command": "uv",
  "args": [
    "run",
    "--project", "C:/path/to/marketing-campaign-automation/whatsapp-mcp/whatsapp-mcp-server",
    "python", "main.py"
  ],
  "env": {
    "ANTHROPIC_API_KEY": "your_key_here"
  }
}
```

---

## Project Structure

```
marketing-campaign-automation/
├── .env.example                    # Template — copy to .env and fill in secrets
├── campaign_database.example.json  # Template — copy to campaign_database.json
├── requirements.txt                # Python dependencies
│
├── intelligence/                   # Core AI pipeline
│   ├── apollo_semantic_router.py   # NL → Apollo API translation
│   ├── decision_router.py          # Lead classification & angle selection
│   ├── message_generator.py        # Cold email copy generation
│   ├── lead_enricher.py            # Apollo.io enrichment
│   ├── campaign_orchestrator.py    # End-to-end pipeline controller
│   └── performance_tracker.py      # SQLite analytics
│
├── apollo-mcp/                     # TypeScript MCP server — Apollo.io
│   ├── src/index.ts
│   └── package.json
│
├── campaign-mcp/                   # Python MCP server — email & campaign tools
│   └── main.py
│
├── whatsapp-mcp/                   # WhatsApp outreach
│   ├── whatsapp-bridge/            # Go binary (WhatsApp Web connection)
│   └── whatsapp-mcp-server/        # Python MCP server
│
├── pipeline-dashboard/             # Flask web UI (localhost:5050)
│   └── app.py
│
├── emails/templates/               # Email copy templates
│   ├── initial_outreach.txt
│   ├── follow_up_1.txt
│   └── follow_up_2.txt
│
├── master_orchestrator.py          # Natural language campaign entry point
├── email_validator.py              # Email validation utility
├── validate_leads_workflow.py      # Lead CSV filtering
├── enrich_leads.ps1                # Apollo batch enrichment (PowerShell)
└── find_contacts.ps1               # Contact discovery script
```

---

## Security Notes

- All API keys and credentials live in `.env` only — never hardcoded
- `.env` is excluded from git via `.gitignore`
- Lead data CSVs (real contact info) are excluded from git
- `campaign_database.json` (contains your company details) is excluded from git
- Run `git status` before every push to verify no sensitive files are staged

---

## License

MIT — see `LICENSE` for details.

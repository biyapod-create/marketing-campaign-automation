# Allennetic Marketing Campaign System

An end-to-end outbound marketing pipeline for Allennetic Ltd, targeting Nigerian SMEs with professional digital services.

## Architecture

```
Marketing Campaign/
├── intelligence/           # Core Python AI pipeline
│   ├── apollo_semantic_router.py   # NL → Apollo API parameter translation
│   ├── decision_router.py          # Lead classification & angle selection
│   ├── message_generator.py        # Cold email copy generation
│   ├── lead_enricher.py            # Apollo.io enrichment integration
│   ├── campaign_orchestrator.py    # End-to-end pipeline controller
│   └── performance_tracker.py      # SQLite-backed analytics
├── apollo-mcp/             # TypeScript MCP server for Apollo.io API
├── campaign-mcp/           # Python MCP server exposing campaign tools to Claude
├── whatsapp-mcp/           # WhatsApp outreach bridge
├── pipeline-dashboard/     # Flask web dashboard (localhost:5050)
├── emails/templates/       # Email template library
├── master_orchestrator.py  # Natural language campaign entry point
├── email_validator.py      # Multi-layer email validation
└── validate_leads_workflow.py  # Lead CSV filtering workflow
```

## Quick Start

### 1. Setup environment
```bash
cp .env.example .env
# Fill in your SMTP and Apollo.io credentials in .env
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the pipeline dashboard
```bash
cd pipeline-dashboard
python app.py
# Open http://localhost:5050
```

### 4. Use the master orchestrator
```python
from master_orchestrator import CampaignOrchestrator

campaign = CampaignOrchestrator()
campaign.execute("find 30 SMEs in Abuja that need websites")
campaign.status()
```

### 5. Validate leads before sending
```bash
python validate_leads_workflow.py leads/leads_database.csv --medium
```

## Apollo MCP Server (TypeScript)

```bash
cd apollo-mcp
npm install
npm run build
npm start
```

## Campaign MCP Server (Python)

```bash
cd campaign-mcp
uv run main.py
# or: python main.py
```

## Environment Variables

See `.env.example` for required configuration:
- `APOLLO_IO_API_KEY` — Apollo.io API key for lead enrichment
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` — Email sending credentials

## Target Market

Nigerian SMEs including early-stage startups, digitizing businesses, solopreneurs, e-commerce sellers, service businesses, and NGOs — primarily in Abuja, Lagos, and Port Harcourt.

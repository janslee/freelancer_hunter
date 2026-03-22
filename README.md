# freelancer_hunter

Python-based OpenClaw skill scaffold for scanning freelance marketplaces, scoring projects, drafting bids, and preparing an approval workflow.

## Current scope

- Python project scaffold
- CLI entrypoints
- YAML config loading
- SQLite bootstrap
- Domain models
- Scoring engine
- Pricing engine
- Proposal draft generation
- Initial workflows

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
python -m freelance_hunter init-db
python -m freelance_hunter seed-mock-projects
python -m freelance_hunter evaluate-projects
python -m freelance_hunter draft-bids
```

## Next steps

- Implement real platform connectors
- Add Telegram notifier
- Add approval commands
- Add bid submission flow

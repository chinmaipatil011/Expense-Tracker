# Tool-Using Expense Assistant

A Flask API for a LangChain-powered assistant that can save expenses, summarize spending by category, and perform safe arithmetic using Python tools and SQLite.

## Features
- `POST /chat`: accepts `{"message":"..."}` and returns an answer plus tool names used.
- `GET /health`: simple service health check.
- Provider switch: `PROVIDER=gemini` or `PROVIDER=ollama`.
- SQLite persistence, validated tool inputs, bounded agent steps, clean API errors.
- Pytest tests with a mocked LLM for endpoint tests.
- `eval.py`: 20 prompts, measured tool-use accuracy, response time and errors; writes `results.json`.

## Setup
Python 3.10+ recommended. From this folder:
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
```
Add your Google AI Studio key to `.env` as `GOOGLE_API_KEY=...`. Do not commit `.env`. The default model is configured in `.env.example`; model availability and free-tier limits depend on Google's current offering. Avoid sending real personal or financial details to hosted models.

## Run
```bash
python app.py
```
Then:
```bash
curl http://127.0.0.1:5000/health
curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d "{\"message\":\"I spent 450 on lunch, save it\"}"
curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d "{\"message\":\"Summarize my expenses for the last 7 days\"}"
```
PowerShell alternative:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:5000/chat -Method Post -ContentType application/json -Body '{"message":"I spent 450 on lunch, save it"}'
```

## Ollama
Install Ollama locally, pull a tool-capable model (for example `ollama pull qwen2.5:3b`), ensure Ollama is running, then set `PROVIDER=ollama` in `.env`. Gemini and Ollama use the same agent/tool code. Confirm the selected model supports tool calling in your installed Ollama version.

## Tests and evaluation
```bash
pytest -q
python eval.py
```
Evaluation calls the selected live provider and may be affected by rate limits, model behavior and network conditions. `results.json` contains the measured run. Re-run separately for each provider and retain each results file before comparing.

| Provider | Accuracy | Average response time | Tool-call errors |
|---|---:|---:|---:|
| Gemini | Not measured yet | Not measured yet | Not measured yet |
| Ollama | Not measured yet | Not measured yet | Not measured yet |

No benchmark numbers are pre-filled; populate this table only from actual `results.json` runs.

## Architecture
`POST /chat` → Flask validates JSON → LangChain model chooses a tool → Python executes the tool → SQLite reads/writes data → model generates final response → Flask returns JSON. The agent has a configurable maximum number of tool-call rounds.

## Safety notes
This is a learning project, not financial software. It stores expense data locally in SQLite. Keep `.env` private, do not send real personal information to hosted models, and do not expose the Flask development server publicly.

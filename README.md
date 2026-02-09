# WA School Compare

Washington state school and district comparison tool. Compare demographics, achievement, staffing, and spending across schools and districts using public OSPI data.

Built with Streamlit, Plotly, and the Socrata Open Data API.

## Pages

- **Home** - Overview and quick stats
- **Comparison** - Compare up to 5 schools or districts side-by-side
- **Explorer** - Deep-dive into a single school or district
- **Chat** - Ask questions about school data using Gemini AI
- **Correlations** - Scatter plots exploring relationships between district-level metrics

## Setup

### Prerequisites

- Python 3.11+
- A [Socrata API token](https://data.wa.gov/profile/edit/developer_settings) (free, increases rate limits)
- A [Google AI API key](https://aistudio.google.com/apikey) (for the chat feature)

### Install

```bash
# Clone and enter the project
cd school-compare

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `SOCRATA_APP_TOKEN` | Recommended | data.wa.gov API token for higher rate limits |
| `GOOGLE_API_KEY` | For chat | Google AI API key for Gemini chatbot |
| `ANTHROPIC_API_KEY` | No | Reserved for future multi-provider support |
| `OPENAI_API_KEY` | No | Reserved for future multi-provider support |

### Run

```bash
streamlit run app.py
```

## Data Sources

- **Assessment, Demographics, Graduation, Staffing**: [Washington State Report Card](https://reportcard.ospi.k12.wa.us) via [data.wa.gov](https://data.wa.gov) Socrata API
- **Spending (F-196)**: OSPI F-196 Financial Reporting Data (included in `data/f196/`)

### Data Availability by Year

| Metric | Default Year | Notes |
|---|---|---|
| Assessment (SBA/WCAS) | 2023-24 | ELA, Math, Science proficiency |
| Graduation rates | 2023-24 | 4-year and 5-year cohort rates |
| Demographics/Enrollment | 2024-25 | Released ahead of assessment data |
| Staffing | 2024-25 | Released ahead of assessment data |
| Spending (F-196) | 2024-25 | District-level only, 10-year trend available |

## Tests

```bash
pytest tests/ -v
```

## Deployment

### Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click "New app" and select your forked repo
4. Set the main file path to `app.py`
5. Under "Advanced settings", add your secrets:

```toml
SOCRATA_APP_TOKEN = "your_token_here"
GOOGLE_API_KEY = "your_key_here"
```

- `GOOGLE_API_KEY` is optional — the chat page gracefully degrades if not set
- `SOCRATA_APP_TOKEN` is optional — the app works without it, but API requests are rate-limited

See `.streamlit/secrets.toml.example` for the template.

## Troubleshooting

- **Wrong Python version**: Ensure `python --version` shows 3.11+. If not, install via `brew install python@3.11` or [pyenv](https://github.com/pyenv/pyenv), then recreate your venv: `python3.11 -m venv .venv`
- **API rate limits / timeout errors**: Register for a free [Socrata app token](https://data.wa.gov/profile/edit/developer_settings) and add it to your `.env`
- **Chat not working**: Verify `GOOGLE_API_KEY` is set in `.env` or Streamlit secrets. The chat page will show an error message if the key is missing.
- **Stale data warnings on first load**: Cached dataset validation may show warnings on the initial page load. Refresh the page to clear them.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Project Structure

```
school-compare/
├── app.py                 # Streamlit entry point
├── pages/                 # Streamlit pages (comparison, explorer, chat, correlations)
├── src/
│   ├── data/
│   │   ├── client.py      # Socrata API client
│   │   ├── models.py      # Data models (dataclasses)
│   │   └── combined.py    # Batch district queries for correlations
│   ├── chat/
│   │   ├── agent.py       # Gemini chat agent with function calling
│   │   ├── tools.py       # Tool definitions and execution
│   │   └── prompts.py     # System prompts
│   └── viz/
│       └── charts.py      # Plotly chart functions
├── config/
│   ├── settings.py        # App settings and env var loading
│   └── datasets.yaml      # Socrata dataset IDs
├── data/f196/             # F-196 spending data (CSV/XLSX)
└── tests/                 # Unit tests
```

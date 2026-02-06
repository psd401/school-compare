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

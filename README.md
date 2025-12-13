# MacroWide

Stock analysis and economic indicator visualization dashboard

## Features

### Dashboard
- Real-time market indicators (KOSPI, KOSDAQ, S&P500, NASDAQ, FX rates, Crypto)
- US Federal Funds Rate (EFFR) display

### US Liquidity Dashboard
- **Fed Balance Sheet** (WALCL) - Federal Reserve Total Assets
- **TGA** (WDTGAL) - Treasury General Account
- **RRP** (RRPONTSYD) - Reverse Repo Facility
- **Net Liquidity** calculation: `WALCL - (WDTGAL + RRPONTSYD)`
- **Liquidity Pipeline** visualization (Sankey-style flow diagram)
- **Net Liquidity vs S&P 500** correlation chart (2000-present)

### Stock Analysis
- Stock search and selection
- Current price, change, volume, market cap display

## Tech Stack

- **Framework**: [Reflex](https://reflex.dev/) (Python)
- **Charts**: Plotly
- **Data Sources**: 
  - [FRED API](https://fred.stlouisfed.org/) (Federal Reserve Economic Data)
  - [yfinance](https://github.com/ranaroussi/yfinance) (Stock/Index data)
  - [NY Fed API](https://markets.newyorkfed.org/) (Interest rate data)
- **Styling**: Tailwind CSS v4
- **Hosting**: Reflex Cloud

## Installation & Running

### Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended)
- FRED API Key (free): https://fred.stlouisfed.org/docs/api/api_key.html

### Installation

```bash
# Clone repository
git clone https://github.com/kilkoon/macro-dashboard.git
cd macro-dashboard

# Install dependencies
uv sync
```

### Environment Setup

Create `.env` file in project root:

```bash
FRED_API_KEY=your_api_key_here
```

### Run Development Server

```bash
uv run reflex run
```

Open http://localhost:3000 in your browser

### Deployment

```bash
# Deploy to Reflex Cloud (with environment variables)
uv run reflex deploy --env FRED_API_KEY=your_api_key_here
```

## Project Structure

```
macro_wide/
├── macro_wide/
│   ├── __init__.py
│   ├── macro_wide.py           # Main app (pages, components)
│   └── services/
│       ├── __init__.py
│       ├── market_data.py      # yfinance/NY Fed data
│       └── fred_data.py        # FRED API integration
├── assets/
│   ├── favicon.ico
│   └── refresh.svg
├── .env                        # Environment variables (gitignored)
├── pyproject.toml              # Project configuration
├── uv.lock                     # Dependency lock file
└── rxconfig.py                 # Reflex configuration
```

## Data Sources

| Indicator | FRED Series ID | Description |
|-----------|----------------|-------------|
| Fed Assets | WALCL | Federal Reserve Total Assets (millions USD) |
| TGA | WDTGAL | Treasury General Account (millions USD) |
| RRP | RRPONTSYD | Reverse Repo (billions USD) |
| S&P 500 | SP500 | S&P 500 Index |

### Net Liquidity Formula

```
Net Liquidity = WALCL - (WDTGAL + RRPONTSYD)
```

Measures the actual liquidity circulating in the market.

## Screenshots

- **Dashboard**: Real-time market indicators
- **Indicators**: US Liquidity Dashboard
- **Stocks**: Individual stock details

## License

MIT License

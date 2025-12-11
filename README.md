# MacroWide

Stock analysis and economic indicator visualization dashboard

## Features

- Real-time market indicators (KOSPI, KOSDAQ, S&P500, NASDAQ, etc.)
- Interactive chart visualization
- Dark/Light theme support

## Tech Stack

- **Framework**: [Reflex](https://reflex.dev/) (Python)
- **Charts**: Recharts, Plotly
- **Styling**: Tailwind CSS
- **Hosting**: Reflex Cloud

## Installation & Running

### Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended)

### Installation

```bash
# Install dependencies
uv sync

# Run development server
uv run reflex run
```

### Deployment

```bash
uv run reflex deploy
```

## Project Structure

```
macro_wide/
├── macro_wide/
│   ├── __init__.py
│   └── macro_wide.py    # Main app code
├── assets/
│   └── favicon.ico
├── pyproject.toml       # Project configuration
├── uv.lock              # Dependency lock file
└── rxconfig.py          # Reflex configuration
```

## License

MIT License

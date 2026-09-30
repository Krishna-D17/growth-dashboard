# 🚀 SocialScope

> **Self-Hosted Social Media Intelligence & Growth Analytics Platform**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Bundled-336791.svg)](https://www.postgresql.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-green.svg)](https://www.selenium.dev/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)

SocialScope is a privacy-first, self-hosted social media intelligence platform designed to track, collect, analyze, and visualize profile and post metrics across **Instagram**, **X (Twitter)**, and **Facebook**.

It features automated background metric collectors, engagement rate calculation, growth velocity tracking, content anomaly detection, comparative analytics, and an interactive React dashboard.

SocialScope is available as both a **standalone Windows Desktop Application (`SocialScope.exe` / `SocialScope-Setup.exe`)** with zero external dependencies and a **local development stack**.

---

## 🎯 What SocialScope Can Do & Practical Use Cases

### 💡 Capabilities & Core Functionality

- **Automated Background Metric Collection**:
  - Periodically collects public metrics (follower counts, post counts, likes, comments, shares, views, reposts, creation timestamps) without requiring official social media API developer accounts.
- **Historical Snapshot Persistence**:
  - Stores time-stamped profile snapshots (`ProfileSnapshot`) and post metrics (`PostSnapshot`), creating an immutable historical record of account growth over time.
- **Growth Velocity & Trend Analysis**:
  - Automatically computes net growth rates, engagement rates per post, average interactions, and performance benchmarks over customizable timeframes.
- **Statistical Anomaly & Viral Spike Detection**:
  - Uses Z-score statistical algorithms to instantly flag top-performing viral content, sudden follower surges, or unexpected engagement drops.
- **Multi-Account & Competitor Benchmarking**:
  - Provides a unified side-by-side comparative dashboard allowing you to compare multiple profiles and creators regardless of platform (Instagram vs. X vs. Facebook).
- **AI-Powered Executive Summaries**:
  - Synthesizes complex historical analytics into actionable natural language growth insights, audience trend reports, and content recommendations.
- **100% Local Data Ownership & Privacy**:
  - Fully self-hosted on your local machine. All database records are stored in a private, application-managed PostgreSQL engine. No cloud subscriptions, no tracking, and no third-party data leakage.

---

### 🚀 Practical Use Cases

- 📈 **Content Creators & Influencer Analytics**:
  - Track audience growth velocity, discover which content formats produce peak engagement rates, and fine-tune posting schedules.
- 🔍 **Competitive Intelligence & Brand Benchmarking**:
  - Monitor competitor profiles side-by-side, analyze rival content strategies, and identify emerging audience trends.
- 💼 **Marketing Agencies & Social Media Managers**:
  - Monitor multiple client profiles across Instagram, X, and Facebook, and generate CSV/JSON metrics exports for client reports.
- 🔬 **Researchers & Data Analysts**:
  - Gather long-term historical social metrics to analyze public sentiment trends, engagement dynamics, and viral mechanics.
- 🛡️ **Privacy-Conscious Users**:
  - Enjoy enterprise-grade social media intelligence without paying monthly SaaS subscriptions or giving third parties access to your data.

---

## ✨ Key Features

- **🌐 Multi-Platform Social Media Intelligence**:
  - **Instagram**: Track profile follower growth, post engagement counts, publish timestamps, and permalink metrics.
  - **X (Twitter)**: Extract profile metrics, follower tracking, post-level likes, reposts, comments, and normalized engagement.
  - **Facebook**: Public profile analytics, post discovery, creation times, and interaction data.
- **🖥️ Standalone Windows Desktop App**:
  - **Zero-Dependency Setup**: Bundles an application-managed PostgreSQL engine (runs locally on port `5433`). No manual database installation, Docker, Python, or Node.js required for end users.
  - **One-Click Launch**: Automated desktop launcher initializes local data, executes database migrations, launches FastAPI backend, and opens the dashboard in your default browser.
  - **Persistent Local Storage**: Stores all database clusters, logs, configurations, and exports safely in `%LOCALAPPDATA%\SocialScope\`.
- **📊 Advanced Growth Analytics**:
  - **Engagement & Velocity**: Track engagement rates per post and follower growth trends over customizable time ranges (7d, 30d, 90d, custom).
  - **Anomaly Detection**: Automatically flag viral spikes or unusual metric drops using statistical Z-score thresholds.
  - **Target Comparison**: Compare multiple creators/competitors side-by-side on unified metrics.
- **🤖 Built-in AI Insights**:
  - Generate natural language growth executive summaries and content recommendations using a zero-config Mock Provider or OpenAI GPT integrations.
- **💾 Comprehensive Exports**:
  - Export profile histories, post metrics, and analytics to structured CSV and JSON files anytime.

---

## 💻 Windows Desktop Application Installation

### Pre-Built Installer (`SocialScope-Setup.exe`)

1. Download `SocialScope-Setup.exe` directly from the repository root or the [GitHub Releases](../../releases) page.
2. Run `SocialScope-Setup.exe` and follow the setup wizard.
3. Launch **SocialScope** from your Start Menu or Desktop shortcut.
4. SocialScope automatically starts its bundled database, executes database migrations, launches the server, and opens your browser to `http://127.0.0.1:8000/`.

---

## 🛠️ Developer Setup & Building from Source

### Prerequisites

- **Python**: 3.12+
- **Node.js**: 18+ & `npm`
- **PostgreSQL**: 14+ (or Docker for development)
- **Windows OS** (for PyInstaller & Inno Setup builds)

---

### 1. Repository Setup & Virtual Environment

```powershell
# Clone the repository
git clone https://github.com/your-username/SocialScope.git
cd SocialScope

# Create and activate Python virtual environment
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend\requirements.txt
```

---

### 2. Database Setup (Development Mode)

Option A: **Docker Container**
```powershell
docker compose up -d
```

Option B: **Local PostgreSQL**
Ensure PostgreSQL is running locally on port `5432` with a database named `socialscope`.

Run Alembic database migrations:
```powershell
$env:PYTHONPATH='backend'
backend\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
```

---

### 3. Run Development Servers

**Backend (FastAPI)**:
```powershell
$env:PYTHONPATH='backend'
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```

**Frontend (React + Vite)**:
```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/` in your browser.

---

### 4. Running Tests

```powershell
# Run backend test suite (150+ unit and integration tests)
$env:PYTHONPATH='backend'
backend\.venv\Scripts\pytest.exe backend/tests
```

---

### 5. Packaging Standalone Windows Desktop App (`.exe`)

To package SocialScope into a self-contained executable with bundled PostgreSQL:

```powershell
# 1. Build React frontend bundle
npm --prefix frontend run build

# 2. Package desktop executable via PyInstaller
powershell -ExecutionPolicy Bypass -File scripts/build_desktop_app.ps1
```

The compiled standalone application will be generated in `dist/SocialScope/SocialScope.exe`.

---

### 6. Building the Windows Installer (`SocialScope-Setup.exe`)

To create the one-click Windows installer:

```powershell
# Compile with Inno Setup Compiler
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer/SocialScope.iss
```

The setup installer `SocialScope-Setup.exe` will be generated under `installer/Output/`.

---

## 🏗️ Project Architecture

```
SocialScope/
├── backend/
│   ├── alembic/              # Database migration scripts & env
│   ├── app/
│   │   ├── ai/               # Mock & OpenAI insight generators
│   │   ├── analytics/        # Engagement, velocity & anomaly algorithms
│   │   ├── api/              # FastAPI routers & endpoints
│   │   ├── collectors/       # Selenium 4.x social media collectors
│   │   │   ├── browser/      # Driver factory & chrome setup
│   │   │   ├── instagram/    # Instagram profile & post scrapers
│   │   │   ├── x/            # X (Twitter) profile & post scrapers
│   │   │   └── facebook/     # Facebook profile & post scrapers
│   │   ├── database/         # SQLAlchemy session & models
│   │   ├── desktop/          # Bundled PostgreSQL & migration managers
│   │   ├── scheduler/        # APScheduler background collection jobs
│   │   ├── services/         # Target, metric & export services
│   │   ├── config.py         # App configuration settings
│   │   ├── main.py           # FastAPI entry point
│   │   └── paths.py          # Portable runtime path resolver
│   └── tests/                # Comprehensive pytest suite
├── desktop_launcher.py       # Desktop app bootstrapper & lifecycle manager
├── SocialScope.spec          # PyInstaller bundle specification
├── scripts/
│   └── build_desktop_app.ps1 # Automated Windows build pipeline
├── installer/
│   └── SocialScope.iss       # Inno Setup installer script
├── frontend/                 # React 19 + Vite + TypeScript dashboard SPA
├── docker-compose.yml        # Dev PostgreSQL container definition
└── README.md
```

---

## 📁 User Data & Runtime Storage Layout

When running the packaged Windows application, user data is isolated from installation binaries and stored securely in `%LOCALAPPDATA%\SocialScope\`:

| Directory | Purpose |
| :--- | :--- |
| `%LOCALAPPDATA%\SocialScope\data\postgresql\` | Bundled PostgreSQL database cluster & tables |
| `%LOCALAPPDATA%\SocialScope\config\config.env` | App configuration & AI provider settings |
| `%LOCALAPPDATA%\SocialScope\logs\` | Application startup logs (`startup.log`) & PostgreSQL logs |
| `%LOCALAPPDATA%\SocialScope\exports\` | User-generated CSV/JSON data exports |
| `%LOCALAPPDATA%\SocialScope\backups\` | Automated database backups |

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).



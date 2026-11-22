# Verbly AI

### AI-Powered Website Content Intelligence and Quality Analysis Platform

Verbly AI is an AI-powered website analysis platform designed to evaluate and improve website content through automated quality assessment and intelligent recommendations.

It helps users understand how effectively their websites communicate by analysing readability, SEO, grammar, content quality, and other important content characteristics.

---

## Overview

Website content plays an important role in user engagement, accessibility, and search engine visibility. Identifying content quality issues manually can be time-consuming.

Verbly AI simplifies this process by bringing multiple website content analysis capabilities together in one platform.

Users can submit a website URL and receive structured insights into its content, along with AI-generated recommendations and improvements.

## Key Features

| Feature | Description |
|---|---|
| Website Scraping | Extracts website content for analysis. |
| Readability Analysis | Evaluates how easy website content is to understand. |
| SEO Analysis | Examines content-related SEO factors. |
| Grammar Analysis | Identifies grammatical issues and provides corrections. |
| AI Content Analysis | Evaluates topics, concepts, entities, intent and content quality. |
| AI Rewrite | Generates improved versions of website content. |
| AI Suggestions | Provides recommendations for improving website content. |
| Confusion Heatmap | Visualises content clarity and potential areas of confusion. |
| Location Intelligence | Planned capability for location-aware insights. |

## Technology Stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend
- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL

### AI Integration
- Groq API — Primary AI provider
- Cloudflare Workers AI — Backup AI provider

### Additional Technologies
- Redis
- Alembic
- Docker
- Pytest

## System Architecture

Verbly AI consists of two primary components.

**Frontend**
- Provides the user interface.
- Accepts website URLs.
- Displays analysis results and recommendations.
- Communicates with backend APIs.

**Backend**
- Extracts website content.
- Performs deterministic content analysis.
- Coordinates AI-powered analysis.
- Processes rewrite and suggestion requests.
- Returns structured results to the frontend.

## Repository Structure

```text
verbly-ai/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/manasachandarkar8-droid/verbly-ai.git
cd verbly-ai
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -e ".[dev]"
```

Create your environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required environment variables in `.env`.

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

### 3. Frontend Setup

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

`http://localhost:3000/verbly-ai`

## AI Provider Strategy

Verbly AI uses a primary and backup AI provider strategy for API-powered analysis.

- **Primary:** Groq — `openai/gpt-oss-120b`
- **Backup:** Cloudflare Workers AI — `@cf/google/gemma-4-26b-a4b-it`

Provider credentials are configured through environment variables and must never be committed to the repository.

## Security

- API credentials are stored in environment variables.
- Environment files containing secrets must not be committed.
- Backend endpoints validate incoming requests.
- Website extraction incorporates protections against unsafe requests.
- Credentials must never be included in screenshots or source control.

## Development and Testing

Run backend tests from the backend directory:

```bash
pytest -q
```

Build the frontend:

```bash
npm run build
```

## Project Status

Verbly AI is under active development, with a focus on modular architecture, reliable AI integration, content analysis, and user experience.

## Contributors

Verbly AI is developed collaboratively by:

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/manasachandarkar8-droid">
        <strong>Manasa Chandarkar</strong>
      </a><br/>
      Project Developer
    </td>
    <td align="center">
      <a href="https://github.com/Mounika085B">
        <strong>Mounika</strong>
      </a><br/>
      Project Developer
    </td>
  </tr>
</table>

We thank everyone who contributed their time, ideas, and efforts towards building Verbly AI.

*Verbly AI — Making website content clearer, smarter, and more effective.*
# VentureAI — AI Startup Incubation & Mentorship Platform

> **An end-to-end, AI-powered platform for Founders, Mentors, and Admins.**  
> VentureAI accelerates early-stage startup development by generating AI startup assets (Idea Validation, 9-Block Lean Canvas, 10-Slide Investor Pitch Decks, Executive Business Plans) and connecting founders with domain mentors via real-time WebSocket chat.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features & Implementation Logic](#-key-features--implementation-logic)
- [Tech Stack](#-tech-stack)
- [Project Architecture](#-project-architecture)
- [Step-by-Step Installation & Setup Guide](#-step-by-step-installation--setup-guide)
  - [Prerequisites](#1-prerequisites)
  - [1. Clone Repository](#2-clone-repository)
  - [2. Database Setup](#3-database-setup)
  - [3. Backend Setup](#4-backend-setup)
  - [4. Frontend Setup](#5-frontend-setup)
  - [5. Running the Application](#6-running-the-application)
- [Environment Variables](#-environment-variables)
- [API Endpoints Reference](#-api-endpoints-reference)

---

## 🌟 Overview

Starting a new business requires strategic planning, market validation, investor collateral, and domain guidance. **VentureAI** streamlines this journey into an integrated, interactive workspace:

1. **AI Co-Pilot**: Evaluates pitch viability, builds 9-block Lean Canvases, generates complete `.pptx` PowerPoint decks, and crafts comprehensive business plans.
2. **Mentorship Network**: Enables founders to discover experienced mentors, send connection requests, and communicate instantly through secure real-time messaging.

---

## ⚙️ Key Features & Implementation Logic

### 1. 🔐 Authentication & Role-Based Access Control (RBAC)
- **Summary**: Secure user registration and login for `Founder`, `Mentor`, and `Admin` roles using JWT tokens stored in `HttpOnly`, `SameSite=Strict` cookies.
- **Logic**: Passwords are hashed with Bcrypt. FastAPI dependencies (`require_role()`) enforce role authorization on protected backend routes, while `route-guard.js` handles client-side route authorization before rendering views.

### 2. 💡 AI Idea Validation Engine
- **Summary**: Analyzes startup pitch submissions, producing a Viability Score (0–100), risk breakdown, and strategic recommendations.
- **Logic**: Evaluates pitches across 5 core pillars (*Market Demand, Competitive Advantage, Monetization, Execution Feasibility, Risk Factors*) using Google Gemini API (`google.genai` / LangGraph). Features automatic fallback model rotation upon 429 quota limits.

### 3. 📊 AI Business Model Canvas (BMC) Tool
- **Summary**: Interactive 9-block Lean Canvas generator with section-by-section regeneration, audit feedback, and PDF export.
- **Logic**: Populates the 9 Lean Canvas building blocks (*Problem, Solution, Value Proposition, Unfair Advantage, Customer Segments, Channels, Key Metrics, Cost Structure, Revenue Streams*). Calculates canvas completeness score (%) based on field quality density.

### 4. 📈 AI Investor Pitch Deck Generator
- **Summary**: Generates a complete 10-slide investor pitch deck with slide-by-slide AI editing and direct `.pptx` PowerPoint presentation export.
- **Logic**: Constructs slide structures (*Problem, Solution, Market, Business Model, Traction, Competition, Team, Ask*) and utilizes `python-pptx` to programmatically build native PowerPoint files with custom layouts and speaker notes.

### 5. 📄 AI Executive Business Plan Generator
- **Summary**: Automated generation of multi-section business plans linked directly to startup workspace metadata.
- **Logic**: Synthesizes workspace metrics into structured chapters (*Executive Summary, Market Analysis, Marketing Strategy, Financial Projections*) with section regeneration capabilities.

### 6. 🤝 Mentor Discovery & Matching Network
- **Summary**: Mentors toggle discoverability and list expertise tags. Founders search, filter, and send mentorship requests.
- **Logic**: Requests transition from `pending` → `accepted` / `rejected`. Accepting a request automatically creates an active mentorship link and initializes a private chat thread.

### 7. 💬 Real-Time Mentor-Founder Chat System
- **Summary**: Private, real-time messaging interface with file attachments (PDF/images), read receipts (`✓/✓✓`), typing indicators, and online presence indicators.
- **Logic**: Dual transport via WebSockets (`/mentor/chat/{id}`) and REST APIs. Features client-side message ID deduplication to prevent duplicate message rendering, and a flexbox layout pinned with `flex-shrink: 0` and `min-height: 0` scroll containers.

### 8. 📊 Interactive Workspace Dashboards
- **Summary**: Custom dashboards (`founder-dashboard.html`, `mentor-dashboard.html`, `admin-dashboard.html`, `startup-workspace.html`).
- **Logic**: Renders custom UI components according to the logged-in user profile (`/auth/me`), tracking workspace progress, pending requests, and activity logs.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy ORM, Alembic, Pydantic v2, WebSockets, Uvicorn
- **Database**: PostgreSQL (`psycopg2`)
- **AI Integrations**: Google Gemini API (`google.genai` / LangGraph)
- **Document Generation**: `python-pptx`, PDF utilities
- **Frontend**: HTML5, Vanilla CSS (Custom Design System with Inter font), JavaScript ES6+
- **Authentication**: JWT Cookies (`HttpOnly`, `SameSite=Strict`), Passlib (Bcrypt)

---

## 🏗️ Project Architecture

```
VentureAI/
├── backend/
│   ├── app/
│   │   ├── auth/              # JWT auth, dependencies, password hashing
│   │   ├── bmc/               # Business Model Canvas API & service
│   │   ├── chat/              # WebSocket manager, chat models & router
│   │   ├── founder/           # Founder profiles & workspace services
│   │   ├── idea_validation/   # Gemini AI idea validation pipeline
│   │   ├── mentor/            # Mentor discovery & profile services
│   │   ├── mentorship/        # Connection requests & status management
│   │   ├── notifications/     # In-app notifications
│   │   ├── pitch_deck/        # AI deck generator & pptx builder
│   │   ├── startup/           # Startup metadata & management
│   │   ├── users/             # User & Role database models
│   │   ├── config.py          # Centralized Pydantic settings
│   │   ├── main.py            # FastAPI application entrypoint
│   │   ├── seed.py            # System roles seeder (Founder, Mentor, Admin)
│   │   └── seed_mentors.py    # Seed mock mentor profiles
│   ├── migrations/            # Alembic database migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── css/                   # Modular CSS stylesheets (chat.css, style.css, etc.)
│   ├── js/                    # Client-side scripts (auth.js, chat.js, route-guard.js)
│   ├── index.html             # Landing page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── chat.html              # Real-time chat interface
│   ├── founder-dashboard.html # Founder main workspace
│   ├── mentor-dashboard.html  # Mentor main workspace
│   ├── mentor-discovery.html  # Search & find mentors
│   ├── pitch-deck.html        # Pitch deck editor & PPTX exporter
│   ├── bmc.html               # Lean Business Model Canvas
│   ├── business-plan.html     # Business Plan generator
│   └── server.py              # Clean URL Python HTTP server
├── .gitignore
└── README.md
```

---

## 🚀 Step-by-Step Installation & Setup Guide

Follow these steps to set up and run **VentureAI** on your local machine.

### 1. Prerequisites
Ensure you have the following installed on your machine:
- **Python**: Version 3.11 or higher ([Download Python](https://www.python.org/downloads/))
- **PostgreSQL**: Version 14 or higher ([Download PostgreSQL](https://www.postgresql.org/download/))
- **Git**: ([Download Git](https://git-scm.com/))

---

### 2. Clone Repository

Open your terminal or command prompt and run:

```bash
git clone https://github.com/aditya-students/VentureAI---AI-Startup-Advisor-Platform.git
cd VentureAI---AI-Startup-Advisor-Platform
```

---

### 3. Database Setup

1. Start your PostgreSQL service.
2. Create a new database named `ventureai` and a user with access credentials:

```sql
CREATE DATABASE ventureai;
CREATE USER ventureai_user WITH PASSWORD 'VentureAI_pass';
GRANT ALL PRIVILEGES ON DATABASE ventureai TO ventureai_user;
```

---

### 4. Backend Setup

Navigate to the `backend` folder:

```bash
cd backend
```

#### Create Virtual Environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### Install Dependencies:
```bash
pip install -r requirements.txt
```

#### Configure Environment Variables:
Copy `.env.example` to `.env`:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and verify your configuration:
```env
DATABASE_URL=postgresql+psycopg2://ventureai_user:VentureAI_pass@localhost:5432/ventureai
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
GEMINI_API_KEY=your_google_gemini_api_key_here
```

#### Seed Initial Database Roles & Mentors:
Run the seeding scripts to populate default roles and mock mentors:

```bash
# Seed default roles (Founder, Mentor, Admin)
python -m app.seed

# Seed mock mentors for discovery
python -m app.seed_mentors
```

---

### 5. Frontend Setup

In a new terminal window, navigate to the `frontend` directory:

```bash
cd frontend
```

No npm installation is required! The frontend uses native Web standards and plain JavaScript.

---

### 6. Running the Application

#### Step A: Start Backend Server
From the `backend` folder (with `venv` activated):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- **Backend API Base**: `http://127.0.0.1:8000`
- **Interactive Swagger API Docs**: `http://127.0.0.1:8000/docs`

#### Step B: Start Frontend Server
From the `frontend` folder:

```bash
python server.py
```
- **Frontend URL**: [http://127.0.0.1:5500](http://127.0.0.1:5500)

> 💡 **Important**: Always access the application via `http://127.0.0.1:5500` so that `SameSite=Strict` authentication cookies match between frontend and backend.

---

## 🔑 Environment Variables Reference

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://...` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret String | Key used to sign auth JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Auth access cookie expiration |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh cookie expiration |
| `COOKIE_SECURE` | `false` | Set `true` in production with HTTPS |
| `CORS_ORIGINS` | `http://127.0.0.1:5500` | Allowed origins for cross-origin requests |
| `GEMINI_API_KEY` | Secret String | Google Gemini AI API key |

---

## 📡 API Endpoints Reference

| Module | Method | Endpoint | Auth | Description |
|---|---|---|---|---|
| **Auth** | POST | `/auth/register` | No | Register Founder or Mentor |
| **Auth** | POST | `/auth/login` | No | Verify credentials & set HttpOnly cookies |
| **Auth** | GET | `/auth/me` | Yes | Get currently authenticated user |
| **Auth** | POST | `/auth/logout` | Yes | Clear auth cookies |
| **Idea** | POST | `/idea-validation/validate` | Yes | Run AI idea evaluation pipeline |
| **BMC** | POST | `/bmc/generate` | Yes | Generate 9-block Lean Canvas |
| **Pitch Deck** | POST | `/pitch-deck/generate` | Yes | Generate 10-slide pitch deck |
| **Pitch Deck** | GET | `/pitch-deck/download-pptx` | Yes | Download deck as `.pptx` presentation |
| **Mentor** | GET | `/mentor/discover` | Yes | Search & filter discoverable mentors |
| **Mentorship** | POST | `/mentorship/request` | Yes | Send connection request to mentor |
| **Mentorship** | POST | `/mentorship/requests/{id}/accept` | Yes | Accept request & initialize chat |
| **Chat** | GET | `/mentor/conversations` | Yes | List active chat conversations |
| **Chat** | POST | `/mentor/conversations/{id}/messages` | Yes | Send text message |
| **Chat** | WS | `/mentor/chat/{id}` | Yes | WebSocket endpoint for instant messaging |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

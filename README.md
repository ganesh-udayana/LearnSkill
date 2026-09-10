# PathPulse AI — Personalized Learning Roadmap Generator

> **An adaptive AI mentor that turns ambitious learning goals into structured, milestone-based roadmaps with free curated resources, dynamic progress check-ins, intelligent re-planning, and learning-style branching.**

---

## 🌟 Overview & Problem Context

Self-learners often know *what* they want to become (e.g., *"Data Analyst"*, *"Full-Stack Web Developer"*, *"Machine Learning Engineer"*), but get stuck in **tutorial hell**, decision fatigue, and conflicting online advice. Static roadmap diagrams don't adapt to an individual's background, available hours, or preferred learning style.

**PathPulse AI** solves this by acting like a **personal AI mentor**:
1. Generates a tailored milestone-by-milestone curriculum calibrated to your available hours and timeframe.
2. Attaches 100% free, reputable resources (from freeCodeCamp, MDN, Kaggle, Khan Academy, Coursera free-audit, and YouTube).
3. Periodically checks in on your progress and pace.
4. **Dynamically adjusts remaining milestones** when you're ahead, behind, or struggling with specific topics—and clearly explains **what changed and why**!
5. Offers seamless branching between **Project-Based** (hands-on building) and **Theory-First** (deep CS/math foundations) philosophies.

---

## 🚀 Key Features

### 1. Core Features (Must-Have)
- **Goal Input Form**: Natural language goal input (e.g. *"become a data analyst in 3 months"*) with skill-level selection (Beginner, Intermediate, Advanced), hours/week commitment slider, and target timeframe.
- **AI-Generated Roadmap**: Structured phases and sequential milestones, each with duration in days/hours, tangible deliverable, skill checklist, and free curated resource links.
- **Three Visualization Modes**:
  - **Timeline / Stepper**: Connected vertical roadmap with glowing status nodes, expandable resource cards, and checklist items.
  - **Kanban Board**: Drag-and-drop / one-click transition board (Not Started ➔ In Progress ➔ Completed).
  - **Phase Summary**: High-level phase breakdown with time commitment analytics.
- **Progress Check-in Flow**: Periodic on-demand check-in modal to record completed milestones, report pace (*Ahead*, *On Track*, *Behind*), and log topics you struggle with.
- **AI Roadmap Adjustment**: Reorganizes upcoming milestones when you fall behind (adds targeted reinforcement drills, extends timelines, compresses electives) or pull ahead (unlocks advanced capstones). Provides an **explicit Mentor Explanation of what changed and why**.
- **Learning Style Toggle**: Instant one-click toggle between **Project-Based** (build-first) and **Theory-First** (principles-first) curricula.
- **Persistent Storage**: Full SQLite backend persistence + LocalStorage sync. Saved roadmaps can be switched, updated, or reloaded at any time.

### 2. Stretch Features (Good-to-Have)
- **Resource Quality Ranking**: Automated tags for difficulty (*Beginner*, *Intermediate*, *Advanced*), format (*Interactive*, *Video*, *Course*, *Documentation*), and estimated completion time (*"3 hours"*, *"10 hours"*).
- **Milestone-Level Notes / Journal**: Integrated reflection notes for every milestone to document portfolio artifacts, key breakthroughs, or blockers, which feed directly into AI adjustments.
- **Shareable Public View & Export**:
  - Instant public read-only link.
  - One-click Markdown export (`.md` file download).
  - Clean printable / PDF stylesheet.
- **Gamified Streaks & Badges**:
  - Daily learning streak counter.
  - Unlockable achievement badges (🎯 *Roadmap Initiated*, ⚡ *First Step Taken*, 🚀 *Halfway Hero*, 🛡️ *Resilient Learner*, 📝 *Reflective Scholar*, 🔄 *Style Explorer*, 🎓 *Mastery Unlocked*).
  - Confetti animations upon achieving milestones!

---

## 🛠️ Architecture & Tech Stack

- **Backend**: Python 3.14 + **FastAPI** + **Uvicorn** + **SQLite**.
- **AI Orchestration**:
  - **Google Gemini API** (`gemini-2.5-flash` via `google-genai`).
  - **OpenAI API** (`gpt-4o-mini` via `httpx`).
  - **Intelligent Local Knowledge Engine**: Built-in, zero-config generative engine providing rich, verified tech curricula and live links with zero external API dependencies required.
- **Frontend**: Lightweight, responsive Single-Page Application (SPA) built with Semantic HTML5, **Tailwind CSS**, **Lucide Icons**, and **Canvas-Confetti**. Zero `npm` build step needed!

---

## ⚡ Quickstart Guide

### Prerequisites
- Python 3.10+ installed.

### 1. Installation
Clone or unzip the project folder and navigate to it:
```bash
cd ai-learning-roadmap-generator
pip install -r requirements.txt
```

### 2. Run the Web Application
```bash
python main.py
```
Or with Uvicorn directly:
```bash
uvicorn app.main:app --reload --port 8000
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### 3. (Optional) Configure Custom AI Keys
PathPulse AI works **100% out of the box** using its intelligent zero-config local engine. If you want to connect live LLMs:
1. Click the ⚙️ **Settings** icon in the top header.
2. Select your provider (**Google Gemini** or **OpenAI**).
3. Enter your API key and click **Save Preferences**.
*(Keys are stored strictly in your local browser session).*

---

## 🗄️ Connecting Supabase (Postgres) as the Database

This app uses SQLAlchemy, so it already speaks Postgres — you just need to point it at your Supabase project instead of the default local SQLite file.

1. **Create a project** at [supabase.com](https://supabase.com) (free tier is enough).
2. In your project, go to **Project Settings → Database → Connection string → URI**.
   - Use the **Session pooler** string (port `6543`) — this works from most hosts (Render, Railway, Vercel functions, etc.).
   - Use the **direct connection** string (port `5432`) if your host keeps a long-lived process (e.g. a VM or container that stays running).
3. Copy that string into the `.env` file's `DATABASE_URL` line, replacing `[YOUR-PASSWORD]` and `[YOUR-PROJECT-REF]` with your actual values:
   ```
   DATABASE_URL=postgresql://postgres.abcdefghijk:MyStrongPassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
4. That's it — no manual schema setup needed. On startup, the app automatically creates the `roadmaps`, `checkins`, and `app_settings` tables in your Supabase database via `init_db()`.
5. Leave `DATABASE_URL` blank to keep using local SQLite instead (good for quick local testing).

> Note: This app talks to Postgres directly through SQLAlchemy (not the Supabase JS client/REST API), so no Supabase project API key is required for the database connection — only the connection string above.

---

## 🔑 Adding AI Provider Keys (optional)

The app works fully offline with zero keys via its built-in "Intelligent Knowledge Engine." To use a live LLM instead, put a key in `.env`:
```
GEMINI_API_KEY=your-key-here
# or
OPENAI_API_KEY=your-key-here
# or
ANTHROPIC_API_KEY=your-key-here
```
You can also paste a key directly in the app's ⚙️ Settings panel per-session instead of editing `.env`.

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest tests/test_api.py -v
```

All 6 core tests will run, validating:
- Sample presets endpoint
- Schema conformance of AI roadmap generation
- Check-in workflow, progress tracking, and badge awarding
- AI adjustment logic, duration recalibration, and mentor explanations
- Project-based vs. Theory-first curriculum distinction
- Markdown export and public share endpoints

## Deploying to Vercel

This project includes a Vercel FastAPI entry point in `api/index.py` and routing configuration in `vercel.json`.

1. Import the repository into Vercel.
2. Add these environment variables in **Project Settings -> Environment Variables**:
   ```
   DATABASE_URL
   NEXT_PUBLIC_SUPABASE_URL
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
   GEMINI_API_KEY
   ```
3. Deploy with the dashboard or CLI:
   ```bash
   npm install -g vercel
   vercel
   vercel --prod
   ```
4. Add the deployed Vercel domain to Supabase Authentication redirect URLs.

Do not upload `.env`; configure secrets in Vercel instead.

---

## 🎬 How to Rehearse a Winning Demo

1. **Step 1: Goal Generation**:
   - Type in: `"become a data analyst in 10 weeks"`
   - Select: `10 hrs/week`, `Beginner` level, `Project-Based` style.
   - Click **Generate Personalized Roadmap**.
   - Watch the structured curriculum render with clear phases, deliverables, and free resource links (Kaggle, freeCodeCamp, MDN).

2. **Step 2: Progress Check-in**:
   - Click **Progress Check-in**.
   - Mark Milestone 1 (*Excel & Google Sheets*) as **Completed**.
   - Select Milestone 2 (*SQL Querying*), report pace as **Behind**, and enter roadblock: `"Struggling with SQL window functions and subqueries"`.
   - Submit check-in and observe the progress bar update + celebratory confetti!

3. **Step 3: Adaptive AI Re-Planning**:
   - Accept the prompt to adjust or click **AI Adjust**.
   - Watch the AI mentor reorganize the upcoming path:
     - It extends the SQL milestone duration.
     - Adds a dedicated targeted interactive practice drill for SQL window functions.
     - Streamlines subsequent milestones to preserve the overall target deadline.
     - Automatically pops up the **Mentor Change Log** explaining *what changed and why*!

4. **Step 4: Style Branching**:
   - In the top action bar, click the **Theory-First** button.
   - Observe the roadmap dynamically transform from practical mini-projects into deep academic foundations (Probability distributions, Relational Algebra, Normalization, Inferential Statistics).

5. **Step 5: Badges & Export**:
   - Click the 🔥 **Streak** / 🏆 **Badges** button in the header to view unlocked achievements.
   - Click **Markdown** to download a formatted `.md` syllabus.
   - Click **Share** to view the public read-only link.

---

## 📂 Project Structure

```
ai-learning-roadmap-generator/
│
├── main.py                     # Root executable script (starts Uvicorn & opens browser)
├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, Pydantic, etc.)
├── sample_roadmaps.json        # Pre-configured demo roadmaps for quick instant load
├── README.md                   # Complete documentation and setup guide
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI REST application & route handlers
│   ├── schemas.py              # Pydantic data contracts (Roadmap, Milestone, Checkin)
│   ├── database.py             # SQLite persistence layer
│   ├── ai_engine.py            # AI orchestrator (Gemini/OpenAI/Zero-Config Fallback)
│   └── static/                 # Production-ready SPA frontend
│       ├── index.html          # Responsive HTML5 layout & modals
│       ├── style.css           # Custom timeline styling & glowing node animations
│       └── app.js              # Client state, dynamic rendering & check-in controller
│
└── tests/
    └── test_api.py             # Automated pytest suite (6/6 tests passing)
```

---

## 📜 License
MIT License. Built for self-directed learners everywhere.

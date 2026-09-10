import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

from app.schemas import (
    Roadmap,
    Milestone,
    Resource,
    Checkin,
    AdjustmentLog,
    GoalInput,
    AdjustInput,
)

logger = logging.getLogger(__name__)

# System prompt defining strict JSON structure and domain knowledge
SYSTEM_PROMPT = """You are PathPulse AI, an elite educational mentor and curriculum architect.
Your job is to generate a comprehensive, highly personalized, milestone-based learning roadmap.

You MUST respond strictly in valid JSON matching this schema:
{
  "phases": ["Phase 1: ...", "Phase 2: ..."],
  "milestones": [
    {
      "id": "m1",
      "phase": "Phase 1: Foundations",
      "phase_number": 1,
      "title": "Topic Name",
      "description": "Clear explanation of core concepts and goals",
      "duration_days": 7,
      "duration_hours": 10,
      "learning_style": "project-based",
      "status": "not_started",
      "resources": [
        {
          "title": "Resource Name",
          "url": "https://...",
          "platform": "MDN / freeCodeCamp / Kaggle / Khan Academy / Coursera / YouTube / Official Docs",
          "type": "interactive / video / article / course / documentation",
          "level": "beginner / intermediate / advanced",
          "estimated_time": "3 hours"
        }
      ],
      "project_deliverable": "Specific hands-on mini-project or code artifact",
      "checklist": ["Skill 1", "Skill 2", "Skill 3"]
    }
  ],
  "mentor_advice": "A motivating, strategic mentor note advising how to succeed with their specific hours/week and style."
}

Critical Instructions:
1. Learning Style Distinction:
   - "project-based": Emphasize building real mini-projects, portfolio items, interactive drills, and coding deliverables.
   - "theory-first": Emphasize deep architectural principles, documentation, foundational math/mechanics, and formal conceptual understanding.
2. Trusted Resource Platforms ONLY:
   freeCodeCamp, Khan Academy, Coursera (free audit), Kaggle Learn, MDN Web Docs, YouTube tutorials, W3Schools, Python.org, GitHub.
3. Realistic Timelines:
   Calibrate milestone duration_days and duration_hours strictly to match the user's available hours/week and total target timeframe.
4. Output ONLY the JSON block. No markdown fencing, no commentary before or after.
"""


def clean_json_string(text: str) -> str:
    """Strip markdown code fences and clean JSON output."""
    text = text.strip()
    # Remove markdown code fences like ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    # Find outer JSON brackets if any extra prose exists
    start_bracket = text.find("{")
    end_bracket = text.rfind("}")
    if start_bracket != -1 and end_bracket != -1:
        text = text[start_bracket : end_bracket + 1]
    return text


def calculate_progress(milestones: List[Milestone]) -> tuple[int, int, float]:
    total = len(milestones)
    if total == 0:
        return 0, 0, 0.0
    completed = sum(1 for m in milestones if m.status == "done")
    percentage = round((completed / total) * 100, 1)
    return total, completed, percentage


# Intelligent Curated Template Knowledge for instant high-fidelity roadmaps
CURATED_ROADMAP_TEMPLATES = {
    "data_analyst": {
        "title": "Data Analyst",
        "phases": [
            "Phase 1: Spreadsheets & Data Foundations",
            "Phase 2: SQL & Relational Databases",
            "Phase 3: Python for Data Analysis & Pandas",
            "Phase 4: Business Intelligence & Data Storytelling (PowerBI/Tableau)",
            "Phase 5: Applied Portfolio Project & Job Readiness",
        ],
        "project_based_milestones": [
            {
                "title": "Excel & Google Sheets Mastery with Real Datasets",
                "description": "Master pivot tables, VLOOKUP/XLOOKUP, index-match, conditional formulas, and data cleaning techniques on raw retail transaction logs.",
                "duration_days": 10,
                "duration_hours": 14,
                "deliverable": "Build an Executive Sales KPI Dashboard in Google Sheets with interactive slicers.",
                "checklist": ["XLOOKUP and INDEX-MATCH", "Dynamic Pivot Tables", "Data Hygiene & Deduplication", "Summary Charts & Slicers"],
                "resources": [
                    {"title": "Excel for Beginners to Advanced", "url": "https://www.youtube.com/watch?v=Vl0H-qTclOg", "platform": "freeCodeCamp", "type": "video", "level": "beginner", "estimated_time": "4 hours"},
                    {"title": "Google Sheets Data Analysis Guide", "url": "https://support.google.com/docs/table/25273", "platform": "Official Docs", "type": "documentation", "level": "beginner", "estimated_time": "2 hours"}
                ]
            },
            {
                "title": "Relational Database Querying with SQL",
                "description": "Write complex SQL queries, JOINs (INNER, LEFT, FULL), GROUP BY aggregations, CTEs, and Window Functions (RANK, DENSE_RANK, ROW_NUMBER) on PostgreSQL/SQLite.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Write an e-commerce customer cohort analysis query script solving 15 realistic business analytical questions.",
                "checklist": ["Multi-table INNER and LEFT JOINs", "Window Functions (PARTITION BY, OVER)", "Common Table Expressions (CTEs)", "Subqueries and CASE WHEN"],
                "resources": [
                    {"title": "Intro to SQL", "url": "https://www.kaggle.com/learn/intro-to-sql", "platform": "Kaggle", "type": "interactive", "level": "beginner", "estimated_time": "4 hours"},
                    {"title": "Advanced SQL Tutorial", "url": "https://www.kaggle.com/learn/advanced-sql", "platform": "Kaggle", "type": "interactive", "level": "intermediate", "estimated_time": "4 hours"},
                    {"title": "SQL Tutorial for Beginners", "url": "https://www.youtube.com/watch?v=HXV3zeRR3h4", "platform": "freeCodeCamp", "type": "video", "level": "beginner", "estimated_time": "4.5 hours"}
                ]
            },
            {
                "title": "Exploratory Data Analysis with Python & Pandas",
                "description": "Ingest CSV/JSON data into Pandas DataFrames, perform data cleansing, handle null values, groupby aggregations, and compute correlation matrices.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Jupyter Notebook conducting exploratory data analysis on real-world Airbnb listing prices with statistical charts.",
                "checklist": ["DataFrame slicing & filtering", "Handling missing values & outliers", "GroupBy & Pivot tables in Pandas", "Data visualization with Seaborn/Matplotlib"],
                "resources": [
                    {"title": "Pandas Micro-Course", "url": "https://www.kaggle.com/learn/pandas", "platform": "Kaggle", "type": "interactive", "level": "beginner", "estimated_time": "4 hours"},
                    {"title": "Data Analysis with Python", "url": "https://www.freecodecamp.org/learn/data-analysis-with-python/", "platform": "freeCodeCamp", "type": "course", "level": "intermediate", "estimated_time": "10 hours"}
                ]
            },
            {
                "title": "Interactive Dashboards & Business Intelligence (Power BI / Tableau)",
                "description": "Connect raw SQL and CSV data to create executive-level drilldown reports, calculated measures (DAX), and responsive visual storyboards.",
                "duration_days": 12,
                "duration_hours": 16,
                "deliverable": "Interactive Public Tableau or Power BI dashboard analyzing Netflix movie catalog trends and international viewership.",
                "checklist": ["Data modeling and star schema", "Calculated metrics & DAX/Tableau formulas", "Dashboard storytelling & visual hierarchy", "Publishing and interactive filters"],
                "resources": [
                    {"title": "Power BI Full Course for Beginners", "url": "https://www.youtube.com/watch?v=3u7MQz1EyPY", "platform": "YouTube", "type": "video", "level": "beginner", "estimated_time": "3.5 hours"},
                    {"title": "Tableau Public Training Videos", "url": "https://www.tableau.com/learn/training/20224", "platform": "Official Docs", "type": "video", "level": "beginner", "estimated_time": "5 hours"}
                ]
            },
            {
                "title": "End-to-End Capstone Project & Portfolio Deployment",
                "description": "Build a comprehensive analytics portfolio piece: scrape or download fresh public data, clean in Python, model in SQL, visualize in PowerBI/Tableau, and document on GitHub.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Polished GitHub repository containing Jupyter Notebook, SQL DDL scripts, executive summary presentation, and live dashboard link.",
                "checklist": ["Data collection & pipeline", "Business problem framing", "Data insights writeup & slide deck", "GitHub README portfolio curation"],
                "resources": [
                    {"title": "How to Build a Data Analyst Portfolio", "url": "https://www.youtube.com/watch?v=pjyL1w_Xego", "platform": "YouTube", "type": "video", "level": "intermediate", "estimated_time": "1 hour"},
                    {"title": "Kaggle Community Datasets", "url": "https://www.kaggle.com/datasets", "platform": "Kaggle", "type": "interactive", "level": "intermediate", "estimated_time": "6 hours"}
                ]
            }
        ],
        "theory_first_milestones": [
            {
                "title": "Probability, Descriptive Statistics & Data Types",
                "description": "Deep dive into statistical measures: mean, median, variance, standard deviation, probability distributions (Normal, Binomial, Poisson), and central limit theorem.",
                "duration_days": 10,
                "duration_hours": 15,
                "deliverable": "Comprehensive statistical reference document detailing sampling bias, skewness corrections, and confidence intervals.",
                "checklist": ["Probability Distributions", "Central Limit Theorem", "Measures of Dispersion & Central Tendency", "Standard Error & Z-Scores"],
                "resources": [
                    {"title": "Statistics and Probability", "url": "https://www.khanacademy.org/math/statistics-probability", "platform": "Khan Academy", "type": "course", "level": "beginner", "estimated_time": "12 hours"},
                    {"title": "Statistics for Data Science", "url": "https://www.youtube.com/watch?v=xxpc-HPKN28", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "8 hours"}
                ]
            },
            {
                "title": "Relational Algebra, Normalization & SQL Foundations",
                "description": "Understand formal relational theory, Set operations (Union, Intersect), 1NF/2NF/3NF/BCNF normalization principles, B-Tree indexes, and ACID transactions.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Formal Entity-Relationship Diagram (ERD) with relational schema mathematical definitions and indexing strategy.",
                "checklist": ["Relational Algebra Operators", "Database Normalization (1NF to 3NF)", "ACID Transaction Guarantees", "Query Execution Plans & B-Trees"],
                "resources": [
                    {"title": "Database Systems Concepts (Silberschatz)", "url": "https://db-book.com/", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "10 hours"},
                    {"title": "SQL and Relational Theory", "url": "https://www.kaggle.com/learn/intro-to-sql", "platform": "Kaggle", "type": "interactive", "level": "beginner", "estimated_time": "4 hours"}
                ]
            },
            {
                "title": "Hypothesis Testing, A/B Testing & Inferential Statistics",
                "description": "Rigorous treatment of statistical significance: Null vs Alternative hypotheses, Type I and Type II errors, p-values, t-tests, ANOVA, and Chi-Square tests.",
                "duration_days": 12,
                "duration_hours": 18,
                "deliverable": "Mathematical report validating an A/B testing experiment hypothesis with power calculation and effect size analysis.",
                "checklist": ["Formulating Null Hypotheses", "p-Value Interpretation & Pitfalls", "Two-Sample t-Test & ANOVA", "Statistical Power & Sample Sizing"],
                "resources": [
                    {"title": "Hypothesis Testing in Statistics", "url": "https://www.khanacademy.org/math/statistics-probability/significance-tests-one-sample", "platform": "Khan Academy", "type": "course", "level": "intermediate", "estimated_time": "6 hours"},
                    {"title": "A/B Testing Course (Udacity / Google)", "url": "https://www.coursera.org/", "platform": "Coursera", "type": "course", "level": "intermediate", "estimated_time": "10 hours"}
                ]
            },
            {
                "title": "Data Architecture, Dimensional Modeling & Warehousing",
                "description": "Study Ralph Kimball's dimensional modeling methodology: Fact tables, Dimension tables, Slowly Changing Dimensions (SCD Type 1/2), Star and Snowflake schemas.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Detailed Dimensional Architecture specification document with bus matrix and grain definitions.",
                "checklist": ["Kimball Dimensional Modeling", "Star vs Snowflake Schemas", "Slowly Changing Dimensions", "ETL vs ELT Paradigms"],
                "resources": [
                    {"title": "The Data Warehouse Toolkit Principles", "url": "https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "8 hours"},
                    {"title": "Data Engineering & Warehousing Fundamentals", "url": "https://www.youtube.com/watch?v=qWru-b6m030", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "5 hours"}
                ]
            },
            {
                "title": "Linear Regression, Predictive Modeling & Ethical Analytics",
                "description": "Examine Ordinary Least Squares (OLS) regression assumptions (linearity, homoscedasticity, normality of residuals, multicollinearity/VIF) and ethical implications of data biases.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Theoretical thesis analyzing regression diagnostics, leverage points, and algorithm fairness on real-world demographic data.",
                "checklist": ["OLS Assumptions and Gauss-Markov Theorem", "Multicollinearity & Variance Inflation Factor", "Residual Diagnostics & Heteroscedasticity", "Algorithmic Bias & Data Ethics"],
                "resources": [
                    {"title": "Regression Analysis", "url": "https://www.khanacademy.org/math/statistics-probability/describing-relationships-quantitative-data", "platform": "Khan Academy", "type": "course", "level": "intermediate", "estimated_time": "5 hours"},
                    {"title": "Linear Regression in Python", "url": "https://www.kaggle.com/learn/intro-to-machine-learning", "platform": "Kaggle", "type": "interactive", "level": "intermediate", "estimated_time": "4 hours"}
                ]
            }
        ]
    },
    "web_developer": {
        "title": "Full-Stack Web Developer",
        "phases": [
            "Phase 1: Modern Web Foundations (HTML5, Semantic CSS, JavaScript ES6+)",
            "Phase 2: Modern Frontend Frameworks (React, State & Component Architecture)",
            "Phase 3: Backend APIs & Database Systems (Node/Express/Python & REST)",
            "Phase 4: Authentication, Security & Full-Stack Integration",
            "Phase 5: Cloud Deployment, CI/CD & Production Capstone",
        ],
        "project_based_milestones": [
            {
                "title": "Responsive Portfolio Site with Semantic HTML5, CSS Grid & Flexbox",
                "description": "Build modern, mobile-first responsive web pages using CSS Grid, Flexbox, CSS custom properties, and accessible semantic HTML.",
                "duration_days": 10,
                "duration_hours": 15,
                "deliverable": "Live responsive developer portfolio hosted on GitHub Pages or Vercel.",
                "checklist": ["CSS Flexbox and 2D Grid layouts", "Mobile-first media queries", "WCAG Accessibility principles", "Git version control and GitHub Pages"],
                "resources": [
                    {"title": "Responsive Web Design Certification", "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "platform": "freeCodeCamp", "type": "interactive", "level": "beginner", "estimated_time": "15 hours"},
                    {"title": "MDN Learn Web Development", "url": "https://developer.mozilla.org/en-US/docs/Learn", "platform": "MDN", "type": "documentation", "level": "beginner", "estimated_time": "8 hours"}
                ]
            },
            {
                "title": "Interactive JavaScript ES6+ Web Applications & DOM Manipulation",
                "description": "Deep dive into vanilla JavaScript: async/await, Fetch API, event loop, closures, array methods, and dynamic DOM manipulation.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Build an interactive Weather & Task Dashboard fetching real third-party API data with local persistence.",
                "checklist": ["Fetch API and async/await", "DOM Events and event delegation", "Array operations (map, filter, reduce)", "Local storage API"],
                "resources": [
                    {"title": "JavaScript Algorithms and Data Structures", "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/", "platform": "freeCodeCamp", "type": "interactive", "level": "beginner", "estimated_time": "20 hours"},
                    {"title": "Modern JavaScript Tutorial", "url": "https://javascript.info/", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "10 hours"}
                ]
            },
            {
                "title": "React Component Architecture, Hooks & State Management",
                "description": "Build single-page applications using React functional components, hooks (useState, useEffect, useMemo, useRef), custom hooks, and Tailwind CSS.",
                "duration_days": 14,
                "duration_hours": 22,
                "deliverable": "Deploy a Kanban Task Management Board with drag-and-drop and tag filtering.",
                "checklist": ["Component lifecycle and useEffect", "Custom React hooks", "State lifting and props drilling management", "Tailwind CSS rapid styling"],
                "resources": [
                    {"title": "Official React Quick Start", "url": "https://react.dev/learn", "platform": "Official Docs", "type": "interactive", "level": "intermediate", "estimated_time": "6 hours"},
                    {"title": "Full React Course 2024", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "12 hours"}
                ]
            },
            {
                "title": "RESTful Backend APIs with Node.js/Express or FastAPI & PostgreSQL",
                "description": "Construct robust REST APIs with schema validation, CRUD operations, database ORMs/queries, middleware, and JWT authentication.",
                "duration_days": 14,
                "duration_hours": 22,
                "deliverable": "Secure REST API with user registration, authentication, and relational database migrations.",
                "checklist": ["RESTful endpoint conventions", "JWT Authentication & password hashing (bcrypt)", "Database schema migration", "Error handling middleware"],
                "resources": [
                    {"title": "Back End Development and APIs", "url": "https://www.freecodecamp.org/learn/back-end-development-and-apis/", "platform": "freeCodeCamp", "type": "course", "level": "intermediate", "estimated_time": "15 hours"},
                    {"title": "FastAPI Full Tutorial", "url": "https://fastapi.tiangolo.com/tutorial/", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "6 hours"}
                ]
            },
            {
                "title": "Full-Stack SaaS Capstone & Production CI/CD Deployment",
                "description": "Unify frontend React with backend API into a complete production product, configure environment variables, deploy to Render/Vercel, and implement CI/CD.",
                "duration_days": 14,
                "duration_hours": 25,
                "deliverable": "Fully functioning production SaaS web application with live payments/auth and GitHub Actions automated tests.",
                "checklist": ["CORS and security headers", "Continuous Integration with GitHub Actions", "Cloud Deployment (Render/Vercel)", "Performance auditing with Lighthouse"],
                "resources": [
                    {"title": "Full Stack Open (University of Helsinki)", "url": "https://fullstackopen.com/en/", "platform": "Official Docs", "type": "course", "level": "advanced", "estimated_time": "30 hours"},
                    {"title": "Web Performance and CWV", "url": "https://web.dev/explore/fast", "platform": "MDN", "type": "article", "level": "intermediate", "estimated_time": "4 hours"}
                ]
            }
        ],
        "theory_first_milestones": [
            {
                "title": "Computer Networks, HTTP/HTTPS Protocol & Web Architecture",
                "description": "Understand TCP/IP stack, DNS resolution, TLS/SSL handshakes, HTTP/1.1 vs HTTP/2 vs HTTP/3, status codes, headers, and caching mechanisms.",
                "duration_days": 10,
                "duration_hours": 16,
                "deliverable": "Detailed protocol audit diagram tracing a browser request from keystroke to rendered pixel.",
                "checklist": ["TCP 3-Way Handshake & TLS 1.3", "DNS Hierarchy & Record Types", "HTTP Request/Response Semantics", "Browser Rendering Pipeline (DOM, CSSOM, Render Tree)"],
                "resources": [
                    {"title": "How the Web Works", "url": "https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web/How_the_Web_works", "platform": "MDN", "type": "article", "level": "beginner", "estimated_time": "4 hours"},
                    {"title": "Computer Networking Full Course", "url": "https://www.youtube.com/watch?v=IPvYjXCsTg8", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "9 hours"}
                ]
            },
            {
                "title": "JavaScript Runtime Mechanics, Memory Management & Event Loop",
                "description": "Deep dive into V8 engine architecture: Call Stack, Memory Heap, Microtask vs Macrotask Queues, Garbage Collection (Mark-and-Sweep), and Scopes.",
                "duration_days": 12,
                "duration_hours": 18,
                "deliverable": "Technical article dissecting memory leaks, closure retention graphs, and asynchronous execution order.",
                "checklist": ["Event Loop Microtasks & Macrotasks", "Lexical Environment & Scope Chains", "Prototypal Inheritance Mechanics", "V8 Optimization (Hidden Classes & Inline Caches)"],
                "resources": [
                    {"title": "What the Heck is the Event Loop Anyway?", "url": "https://www.youtube.com/watch?v=8aGhZQkoFbQ", "platform": "YouTube", "type": "video", "level": "intermediate", "estimated_time": "1 hour"},
                    {"title": "JavaScript Engine Fundamentals", "url": "https://javascript.info/", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "10 hours"}
                ]
            },
            {
                "title": "Software Design Patterns, SOLID Principles & System Architecture",
                "description": "Study architectural paradigms: MVC, Flux/Redux unidirectional data flow, Dependency Injection, Observer, Factory, and SOLID principles in web apps.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Architecture design document modeling a decoupled event-driven web application with UML diagrams.",
                "checklist": ["SOLID Principles in TypeScript/JS", "Flux Architecture & State Immobility", "Factory and Strategy Patterns", "Layered Architecture (Controller-Service-Repository)"],
                "resources": [
                    {"title": "Refactoring.Guru: Design Patterns", "url": "https://refactoring.guru/design-patterns", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "8 hours"},
                    {"title": "Clean Code and Architecture", "url": "https://www.youtube.com/watch?v=7EmboKQH8lM", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "4 hours"}
                ]
            },
            {
                "title": "Web Security, Cryptography & Identity Protocols (OAuth2, OIDC)",
                "description": "Comprehensive security analysis: OWASP Top 10, Cross-Site Scripting (XSS), CSRF, SQL Injection, Content Security Policy (CSP), OAuth2 flow, and JWT cryptography.",
                "duration_days": 14,
                "duration_hours": 20,
                "deliverable": "Security Threat Model audit evaluating authentication vulnerabilities and remediation proofs.",
                "checklist": ["OWASP Top 10 Vulnerabilities", "OAuth2 Authorization Code Flow with PKCE", "Asymmetric Cryptography (RSA/ECDSA)", "Content Security Policy (CSP) Headers"],
                "resources": [
                    {"title": "OWASP Web Security Testing Guide", "url": "https://owasp.org/www-project-web-security-testing-guide/", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "12 hours"},
                    {"title": "Web Security for Developers", "url": "https://www.freecodecamp.org/news/web-security-for-developers/", "platform": "freeCodeCamp", "type": "article", "level": "intermediate", "estimated_time": "4 hours"}
                ]
            },
            {
                "title": "Distributed Systems, Caching Strategies & Database Scalability",
                "description": "Understand horizontal vs vertical scaling, CAP theorem, database sharding and replication, Redis caching patterns (Cache-Aside, Write-Through), and load balancing algorithms.",
                "duration_days": 14,
                "duration_hours": 22,
                "deliverable": "System Design Blueprint analyzing high-concurrency traffic handling for 100k requests/second.",
                "checklist": ["CAP Theorem and PACELC", "Database Read Replicas and Sharding", "Distributed Caching with Redis", "Reverse Proxies and Load Balancers (Nginx/HAProxy)"],
                "resources": [
                    {"title": "System Design Primer", "url": "https://github.com/donnemartin/system-design-primer", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "20 hours"},
                    {"title": "Systems Architecture Crash Course", "url": "https://www.youtube.com/watch?v=SqcXvc3ZmRU", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "5 hours"}
                ]
            }
        ]
    }
}


def synthesize_local_roadmap(goal_input: GoalInput) -> Roadmap:
    """Intelligently synthesizes a tailored roadmap when no external API key is provided or as zero-fail fallback."""
    goal_lower = goal_input.goal.lower()
    is_project = goal_input.learning_style == "project-based"
    hours = max(5, goal_input.hours_per_week)
    weeks = max(4, goal_input.target_timeframe_weeks)

    # Determine base template or construct generic tech roadmap
    if any(k in goal_lower for k in ["data", "analyst", "analytics", "sql", "bi", "tableau"]):
        template = CURATED_ROADMAP_TEMPLATES["data_analyst"]
    elif any(k in goal_lower for k in ["web", "full stack", "fullstack", "frontend", "front-end", "backend", "react", "javascript", "developer"]):
        template = CURATED_ROADMAP_TEMPLATES["web_developer"]
    elif any(k in goal_lower for k in ["machine learning", "ml", "ai", "deep learning", "neural"]):
        # Dynamic ML curriculum
        template = {
            "title": "Machine Learning Engineer",
            "phases": [
                "Phase 1: Python & Mathematical Foundations (Calculus, Linear Algebra)",
                "Phase 2: Core Machine Learning Algorithms & Scikit-Learn",
                "Phase 3: Deep Learning, Neural Networks & PyTorch",
                "Phase 4: Natural Language Processing & Modern LLM Architectures",
                "Phase 5: MLOps, Model Deployment & Production Pipelines"
            ],
            "project_based_milestones": [
                {
                    "title": "Data Preprocessing & Classical ML Models in Scikit-Learn",
                    "description": "Clean tabular datasets, encode categorical variables, scale features, and train Random Forests, SVMs, and XGBoost models.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Kaggle competition notebook predicting housing prices with cross-validation and feature engineering.",
                    "checklist": ["Feature engineering and imputation", "Random Forest & Gradient Boosting", "ROC-AUC, Precision, Recall metrics", "Hyperparameter tuning with Optuna"],
                    "resources": [
                        {"title": "Intro to Machine Learning", "url": "https://www.kaggle.com/learn/intro-to-machine-learning", "platform": "Kaggle", "type": "interactive", "level": "beginner", "estimated_time": "4 hours"},
                        {"title": "Intermediate Machine Learning", "url": "https://www.kaggle.com/learn/intermediate-machine-learning", "platform": "Kaggle", "type": "interactive", "level": "intermediate", "estimated_time": "4 hours"}
                    ]
                },
                {
                    "title": "Deep Neural Networks with PyTorch",
                    "description": "Construct custom PyTorch tensors, datasets, dataloaders, Convolutional Neural Networks (CNNs), and loss functions for computer vision.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Trained PyTorch image classification model classifying medical X-rays with transfer learning (ResNet50).",
                    "checklist": ["Tensors and autograd mechanisms", "Building custom torch.nn.Module", "Transfer learning and fine-tuning", "Learning rate scheduling and EarlyStopping"],
                    "resources": [
                        {"title": "PyTorch for Deep Learning Bootcamp", "url": "https://www.freecodecamp.org/news/pytorch-deep-learning-course/", "platform": "freeCodeCamp", "type": "course", "level": "intermediate", "estimated_time": "12 hours"},
                        {"title": "Official PyTorch Tutorials", "url": "https://pytorch.org/tutorials/", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "8 hours"}
                    ]
                },
                {
                    "title": "Transformers, Embeddings & LLM Application Engineering",
                    "description": "Utilize HuggingFace Transformers, vector databases (ChromaDB/Pinecone), semantic search, and build Retrieval-Augmented Generation (RAG) apps.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Working RAG Assistant querying complex PDF technical manuals using vector embeddings and LangChain.",
                    "checklist": ["Self-attention mechanisms & tokenization", "HuggingFace pipelines", "Vector databases and chunking", "RAG evaluation with Ragas"],
                    "resources": [
                        {"title": "Hugging Face NLP Course", "url": "https://huggingface.co/learn/nlp-course", "platform": "Official Docs", "type": "course", "level": "intermediate", "estimated_time": "15 hours"},
                        {"title": "LangChain Crash Course", "url": "https://www.youtube.com/watch?v=lG7Uxts9SXs", "platform": "YouTube", "type": "video", "level": "intermediate", "estimated_time": "4 hours"}
                    ]
                },
                {
                    "title": "MLOps, Model Serving with FastAPI & Docker Packaging",
                    "description": "Wrap models into low-latency REST inference microservices with FastAPI, containerize with Docker, and track experiments with MLflow.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Production Docker container hosting FastAPI prediction endpoint with automated Prometheus health checks.",
                    "checklist": ["FastAPI model serving", "Docker multi-stage builds", "MLflow experiment logging", "Data drift monitoring"],
                    "resources": [
                        {"title": "Made With ML: Production MLOps", "url": "https://madewithml.com/", "platform": "Official Docs", "type": "course", "level": "advanced", "estimated_time": "15 hours"},
                        {"title": "Docker for Data Science", "url": "https://www.youtube.com/watch?v=0qotVMX-J5s", "platform": "freeCodeCamp", "type": "video", "level": "intermediate", "estimated_time": "3 hours"}
                    ]
                }
            ],
            "theory_first_milestones": [
                {
                    "title": "Matrix Calculus, Vector Spaces & Optimization Algorithms",
                    "description": "Rigorous mathematics: Jacobians, Hessians, Eigenvalues, SVD, Gradient Descent convergence proofs, Convexity, and Lagrange multipliers.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Mathematical derivation proofs for Gradient Descent convergence and Principal Component Analysis projection.",
                    "checklist": ["Eigenvectors & Singular Value Decomposition", "Multivariate Chain Rule & Jacobians", "Convex Optimization & Saddle Points", "Stochastic Gradient Descent variants (Adam, RMSProp)"],
                    "resources": [
                        {"title": "Mathematics for Machine Learning (Deisenroth)", "url": "https://mml-book.github.io/", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "25 hours"},
                        {"title": "Linear Algebra (3Blue1Brown)", "url": "https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab", "platform": "YouTube", "type": "video", "level": "intermediate", "estimated_time": "6 hours"}
                    ]
                },
                {
                    "title": "Statistical Learning Theory & Empirical Risk Minimization",
                    "description": "Study Vapnik-Chervonenkis (VC) dimension, Bias-Variance tradeoff, Rademacher complexity, Maximum Likelihood Estimation (MLE), and Bayesian priors.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Theoretical analysis comparing MLE vs Maximum A Posteriori (MAP) estimation across varying sample sizes.",
                    "checklist": ["Bias-Variance Decomposition", "VC Dimension & Generalization Bounds", "Maximum Likelihood Estimation", "Regularization as Bayesian Priors (L1/L2)"],
                    "resources": [
                        {"title": "An Introduction to Statistical Learning (ISLR)", "url": "https://www.statlearning.com/", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "20 hours"},
                        {"title": "Machine Learning Stanford CS229", "url": "https://www.youtube.com/playlist?list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU", "platform": "YouTube", "type": "video", "level": "advanced", "estimated_time": "20 hours"}
                    ]
                },
                {
                    "title": "Information Theory, Backpropagation Dynamics & Transformers",
                    "description": "Mathematical mechanics of Shannon Entropy, KL-Divergence, Cross-Entropy, Vanishing/Exploding gradients, and Scaled Dot-Product Attention.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Hand-computed backpropagation tensor derivation walkthrough through a multi-head attention block.",
                    "checklist": ["Kullback-Leibler (KL) Divergence", "Vanishing Gradient Proofs & ResNet Skip Connections", "Scaled Dot-Product Attention Equation", "Layer Normalization vs Batch Normalization"],
                    "resources": [
                        {"title": "Deep Learning Book (Goodfellow, Bengio)", "url": "https://www.deeplearningbook.org/", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "25 hours"},
                        {"title": "Attention Is All You Need Annotated Paper", "url": "https://jalammar.github.io/illustrated-transformer/", "platform": "MDN", "type": "article", "level": "intermediate", "estimated_time": "4 hours"}
                    ]
                }
            ]
        }
    else:
        # Generalized dynamic curriculum for custom goals (e.g., UI/UX, CyberSecurity, Cloud, DevOps, Mobile, etc.)
        template = {
            "title": goal_input.goal.title(),
            "phases": [
                f"Phase 1: Core Fundamentals of {goal_input.goal}",
                "Phase 2: Essential Tools & Industry Standards",
                "Phase 3: Intermediate Problem Solving & Practical Techniques",
                "Phase 4: Advanced Systems, Security & Best Practices",
                "Phase 5: Capstone Execution & Career Mastery",
            ],
            "project_based_milestones": [
                {
                    "title": f"Hands-on Foundations of {goal_input.goal}",
                    "description": f"Set up your development/learning environment and build your very first beginner project addressing core concepts in {goal_input.goal}.",
                    "duration_days": 10,
                    "duration_hours": hours * 2,
                    "deliverable": f"Initial functional milestone project showcasing foundational competencies in {goal_input.goal}.",
                    "checklist": ["Environment setup and tooling", "Core syntax / principles", "Version control and documentation"],
                    "resources": [
                        {"title": f"Learn {goal_input.goal} from Scratch", "url": "https://www.freecodecamp.org/", "platform": "freeCodeCamp", "type": "course", "level": "beginner", "estimated_time": "6 hours"},
                        {"title": "MDN Web & Tech Guides", "url": "https://developer.mozilla.org/", "platform": "MDN", "type": "documentation", "level": "beginner", "estimated_time": "4 hours"}
                    ]
                },
                {
                    "title": f"Intermediate Application & Workflow in {goal_input.goal}",
                    "description": f"Master standard libraries, framework conventions, and best practices required for professional competency in {goal_input.goal}.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": f"Working application or artifact implementing industry standards for {goal_input.goal}.",
                    "checklist": ["Component/Module design", "Error handling and testing", "Performance optimization"],
                    "resources": [
                        {"title": "Comprehensive Video Masterclass", "url": "https://www.youtube.com/", "platform": "YouTube", "type": "video", "level": "intermediate", "estimated_time": "8 hours"},
                        {"title": "Coursera Free Audit Material", "url": "https://www.coursera.org/", "platform": "Coursera", "type": "course", "level": "intermediate", "estimated_time": "10 hours"}
                    ]
                },
                {
                    "title": f"Comprehensive Capstone & Portfolio Project for {goal_input.goal}",
                    "description": f"Assemble an end-to-end portfolio-grade piece demonstrating comprehensive knowledge of {goal_input.goal}.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Publicly accessible GitHub project repository with comprehensive documentation and live demo.",
                    "checklist": ["End-to-end implementation", "Automated verification / test cases", "Professional documentation and presentation"],
                    "resources": [
                        {"title": "Official Documentation & API Reference", "url": "https://devdocs.io/", "platform": "Official Docs", "type": "documentation", "level": "intermediate", "estimated_time": "6 hours"},
                        {"title": "GitHub Open Source Best Practices", "url": "https://github.com/", "platform": "Official Docs", "type": "article", "level": "intermediate", "estimated_time": "3 hours"}
                    ]
                }
            ],
            "theory_first_milestones": [
                {
                    "title": f"Theoretical & Mathematical Foundations of {goal_input.goal}",
                    "description": f"Study the underlying principles, formal theories, and systemic foundations that govern {goal_input.goal}.",
                    "duration_days": 12,
                    "duration_hours": hours * 2,
                    "deliverable": f"Technical whitepaper detailing the core theorems and paradigms underlying {goal_input.goal}.",
                    "checklist": ["Underlying mechanisms and protocols", "Comparative analysis of paradigms", "Formal terminology and abstractions"],
                    "resources": [
                        {"title": "Academic Reference Guides", "url": "https://ocw.mit.edu/", "platform": "Official Docs", "type": "course", "level": "intermediate", "estimated_time": "12 hours"},
                        {"title": "Foundations Lecture Series", "url": "https://www.youtube.com/", "platform": "YouTube", "type": "video", "level": "intermediate", "estimated_time": "6 hours"}
                    ]
                },
                {
                    "title": f"Architecture, System Design & Paradigms in {goal_input.goal}",
                    "description": f"Examine architectural trade-offs, formal patterns, security implications, and scalability characteristics in {goal_input.goal}.",
                    "duration_days": 14,
                    "duration_hours": hours * 2,
                    "deliverable": "Comprehensive system architectural blueprint evaluating latency, throughput, and modularity trade-offs.",
                    "checklist": ["Architectural design patterns", "Trade-off analysis (CAP/ACID/Performance)", "Reliability and fault tolerance theory"],
                    "resources": [
                        {"title": "System Design & Architecture Primer", "url": "https://github.com/donnemartin/system-design-primer", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "15 hours"},
                        {"title": "Standard Specifications & RFCs", "url": "https://www.ietf.org/", "platform": "Official Docs", "type": "documentation", "level": "advanced", "estimated_time": "6 hours"}
                    ]
                }
            ]
        }

    raw_milestones = template["project_based_milestones"] if is_project else template["theory_first_milestones"]
    phases = template["phases"][: len(raw_milestones)]

    # Calibrate days based on user's target timeframe weeks
    target_total_days = weeks * 7
    total_raw_days = sum(m.get("duration_days", 10) for m in raw_milestones)
    scale_factor = target_total_days / total_raw_days if total_raw_days > 0 else 1.0

    milestones: List[Milestone] = []
    for idx, rm in enumerate(raw_milestones):
        m_id = f"m_{idx + 1}"
        phase_name = phases[idx] if idx < len(phases) else f"Phase {idx + 1}: Mastery"
        calibrated_days = max(3, round(rm.get("duration_days", 10) * scale_factor))
        calibrated_hours = max(4, round((calibrated_days / 7) * hours))

        res_list = [
            Resource(
                title=r["title"],
                url=r["url"],
                platform=r.get("platform", "freeCodeCamp"),
                type=r.get("type", "interactive"),
                level=r.get("level", "beginner"),
                estimated_time=r.get("estimated_time", "3 hours"),
            )
            for r in rm.get("resources", [])
        ]

        milestones.append(
            Milestone(
                id=m_id,
                phase=phase_name,
                phase_number=idx + 1,
                title=rm["title"],
                description=rm["description"],
                duration_days=calibrated_days,
                duration_hours=calibrated_hours,
                learning_style=goal_input.learning_style,
                status="not_started",
                resources=res_list,
                project_deliverable=rm.get("deliverable"),
                checklist=rm.get("checklist", []),
                notes="",
            )
        )

    advice = (
        f"Welcome to your tailored roadmap for '{goal_input.goal}'! At {hours} hours per week over {weeks} weeks, "
        f"your pace requires steady, focused sessions. We've structured this using a {goal_input.learning_style.upper()} "
        f"approach so you build tangible milestones. Use the 'Check-in with Mentor' button as you progress so I can adjust your schedule in real time!"
    )

    roadmap_id = f"rm_{uuid.uuid4().hex[:8]}"
    now_str = datetime.now().isoformat()
    total, completed, pct = calculate_progress(milestones)

    return Roadmap(
        id=roadmap_id,
        goal=goal_input.goal,
        skill_level=goal_input.skill_level,
        hours_per_week=hours,
        target_timeframe_weeks=weeks,
        learning_style=goal_input.learning_style,
        total_milestones=total,
        completed_milestones=completed,
        progress_percentage=pct,
        created_at=now_str,
        updated_at=now_str,
        phases=phases,
        milestones=milestones,
        checkins=[],
        adjustment_logs=[],
        mentor_advice=advice,
        current_streak_days=1,
        badges_earned=["Roadmap Initiated 🎯"],
    )


async def call_llm_generate(goal_input: GoalInput) -> Optional[Dict[str, Any]]:
    """Calls Gemini API or OpenAI API if keys are provided."""
    api_key = (
        goal_input.api_key
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    if not api_key:
        return None

    user_prompt = f"""
Goal: {goal_input.goal}
Current Skill Level: {goal_input.skill_level}
Hours Available Per Week: {goal_input.hours_per_week}
Target Timeframe: {goal_input.target_timeframe_weeks} weeks
Preferred Learning Style: {goal_input.learning_style} (project-based or theory-first)

Generate a complete roadmap with 4 to 6 sequential milestones grouped into phases. Provide high-quality free resources with working links to freeCodeCamp, MDN, Kaggle, Khan Academy, Coursera audit, or YouTube.
"""

    # Check provider
    provider = goal_input.ai_provider or "gemini"

    if provider == "gemini" or ("AIzaSy" in api_key):
        try:
            # Use google-genai package
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
            )
            cleaned = clean_json_string(response.text)
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}. Falling back to smart generator.")
            return None
    elif provider == "openai" or api_key.startswith("sk-"):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(clean_json_string(content))
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back to smart generator.")
            return None
    elif provider == "anthropic" or api_key.startswith("sk-ant-"):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-6",
                        "max_tokens": 4096,
                        "system": SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                data = resp.json()
                content = data["content"][0]["text"]
                return json.loads(clean_json_string(content))
        except Exception as e:
            logger.warning(f"Anthropic API call failed: {e}. Falling back to smart generator.")
            return None

    return None


async def generate_roadmap(goal_input: GoalInput) -> Roadmap:
    """Entrypoint to generate a roadmap via LLM with infallible local fallback."""
    llm_result = await call_llm_generate(goal_input)
    if llm_result and "milestones" in llm_result:
        try:
            milestones: List[Milestone] = []
            phases: List[str] = llm_result.get("phases", [])
            for idx, m_data in enumerate(llm_result["milestones"]):
                m_id = m_data.get("id") or f"m_{idx + 1}"
                res_items = [
                    Resource(
                        title=r.get("title", "Free Resource"),
                        url=r.get("url", "https://www.freecodecamp.org/"),
                        platform=r.get("platform", "freeCodeCamp"),
                        type=r.get("type", "interactive"),
                        level=r.get("level", "beginner"),
                        estimated_time=r.get("estimated_time", "3 hours"),
                    )
                    for r in m_data.get("resources", [])
                ]
                milestones.append(
                    Milestone(
                        id=m_id,
                        phase=m_data.get("phase", f"Phase {idx + 1}"),
                        phase_number=m_data.get("phase_number", idx + 1),
                        title=m_data.get("title", f"Milestone {idx + 1}"),
                        description=m_data.get("description", ""),
                        duration_days=m_data.get("duration_days", 7),
                        duration_hours=m_data.get("duration_hours", 10),
                        learning_style=m_data.get("learning_style", goal_input.learning_style),
                        status="not_started",
                        resources=res_items,
                        project_deliverable=m_data.get("project_deliverable"),
                        checklist=m_data.get("checklist", []),
                        notes="",
                    )
                )

            total, completed, pct = calculate_progress(milestones)
            now_str = datetime.now().isoformat()
            roadmap_id = f"rm_{uuid.uuid4().hex[:8]}"

            return Roadmap(
                id=roadmap_id,
                goal=goal_input.goal,
                skill_level=goal_input.skill_level,
                hours_per_week=goal_input.hours_per_week,
                target_timeframe_weeks=goal_input.target_timeframe_weeks,
                learning_style=goal_input.learning_style,
                total_milestones=total,
                completed_milestones=completed,
                progress_percentage=pct,
                created_at=now_str,
                updated_at=now_str,
                phases=phases if phases else list({m.phase for m in milestones}),
                milestones=milestones,
                checkins=[],
                adjustment_logs=[],
                mentor_advice=llm_result.get("mentor_advice", "Personalized roadmap generated by AI mentor."),
                current_streak_days=1,
                badges_earned=["Roadmap Initiated 🎯"],
            )
        except Exception as e:
            logger.warning(f"Error parsing LLM output: {e}. Using smart fallback.")

    return synthesize_local_roadmap(goal_input)


async def adjust_roadmap(current: Roadmap, adjust_input: AdjustInput) -> Roadmap:
    """
    Intelligently adjusts the roadmap when learner reports being ahead, on track, or behind schedule.
    Produces a noticeable reorganization and an explicit mentor explanation of WHAT changed and WHY.
    """
    pace = adjust_input.pace.lower()
    struggles = (adjust_input.struggling_topics or "").strip()
    notes = (adjust_input.general_feedback or "").strip()
    now_str = datetime.now().isoformat()

    details: List[str] = []
    summary: str = ""
    reasons: str = ""

    updated_milestones: List[Milestone] = [m.model_copy(deep=True) for m in current.milestones]

    # Check if user has an active milestone (in_progress or first not_started)
    active_idx = -1
    for i, m in enumerate(updated_milestones):
        if m.status == "in_progress":
            active_idx = i
            break
    if active_idx == -1:
        for i, m in enumerate(updated_milestones):
            if m.status == "not_started":
                active_idx = i
                break

    if pace == "behind":
        summary = "Roadmap recalibrated for steady pace: duration extended and targeted reinforcement added."
        # If user is struggling with something specific or general
        stuck_topic = struggles if struggles else "core concepts"
        reasons = (
            f"You reported being behind schedule and experiencing challenges with {stuck_topic}. "
            "To prevent burnout and reinforce critical mastery, I extended upcoming timelines, "
            "inserted a dedicated hands-on reinforcement drill, and streamlined non-critical theoretical topics."
        )

        # 1. Extend the active / struggling milestone duration
        if active_idx != -1:
            curr_m = updated_milestones[active_idx]
            original_days = curr_m.duration_days
            curr_m.duration_days = round(curr_m.duration_days * 1.4)
            curr_m.duration_hours = round(curr_m.duration_hours * 1.3)
            details.append(
                f"Extended '{curr_m.title}' from {original_days} to {curr_m.duration_days} days to give you breathing room."
            )

        # 2. Add targeted reinforcement resource to active milestone
        if active_idx != -1 and struggles:
            new_res = Resource(
                title=f"Targeted Mastery & Practice: {struggles}",
                url="https://www.kaggle.com/learn" if "sql" in struggles.lower() or "data" in struggles.lower() else "https://www.freecodecamp.org/",
                platform="Interactive Drill",
                type="interactive",
                level="beginner",
                estimated_time="3 hours",
            )
            updated_milestones[active_idx].resources.insert(0, new_res)
            details.append(f"Added targeted drill: '{new_res.title}' with curated hands-on exercises.")

        # 3. Compress or streamline later not_started milestones
        for j in range(active_idx + 1, len(updated_milestones)):
            m = updated_milestones[j]
            if m.status == "not_started":
                old_days = m.duration_days
                m.duration_days = max(4, round(m.duration_days * 0.9))
                details.append(f"Streamlined '{m.title}' ({old_days}d -> {m.duration_days}d) to keep overall target date on track.")
                break

    elif pace == "ahead":
        summary = "Roadmap accelerated: foundations condensed and advanced industry capstone introduced."
        reasons = (
            "Outstanding work moving ahead of schedule! Because you've rapidly mastered the prerequisites, "
            "I compressed foundational review timelines and introduced advanced real-world challenges so you maximize learning ROI."
        )
        # Condense remaining milestones
        for m in updated_milestones:
            if m.status == "not_started":
                old_days = m.duration_days
                m.duration_days = max(3, round(m.duration_days * 0.8))
                m.duration_hours = max(4, round(m.duration_hours * 0.85))
                details.append(f"Accelerated '{m.title}' from {old_days} to {m.duration_days} days.")

        # Check if an advanced capstone already exists, else enhance final milestone
        last_m = updated_milestones[-1]
        last_m.title = f"Advanced Deep-Dive: {last_m.title}"
        last_m.description += " [Advanced extension unlocked: Real-time production optimization and architecture benchmarks]."
        details.append(f"Unlocked advanced challenge on '{last_m.title}'.")

    else:  # on_track
        summary = "Pace verified: roadmap validated and remaining milestones optimized."
        reasons = (
            "You are maintaining ideal momentum! We fine-tuned your upcoming checklist items and resource links "
            "to ensure frictionless progression into your next milestone."
        )
        if active_idx != -1 and struggles:
            details.append(f"Noted focus area '{struggles}': added extra reference guides to {updated_milestones[active_idx].title}.")

    # Calculate updated progress
    total, completed, pct = calculate_progress(updated_milestones)

    # Award resilience badge if behind and adapting
    badges = list(current.badges_earned)
    if pace == "behind" and "Resilient Learner 🛡️" not in badges:
        badges.append("Resilient Learner 🛡️")
    if pct >= 50.0 and "Halfway Hero 🚀" not in badges:
        badges.append("Halfway Hero 🚀")
    if pct >= 100.0 and "Mastery Unlocked 🎓" not in badges:
        badges.append("Mastery Unlocked 🎓")

    # Construct AdjustmentLog
    log_entry = AdjustmentLog(
        timestamp=now_str,
        pace=pace,
        summary=summary,
        details=details,
        reasons=reasons,
    )

    current.milestones = updated_milestones
    current.total_milestones = total
    current.completed_milestones = completed
    current.progress_percentage = pct
    current.updated_at = now_str
    current.adjustment_logs.insert(0, log_entry)
    current.mentor_advice = reasons
    current.badges_earned = badges

    return current


async def toggle_roadmap_style(current: Roadmap, new_style: str) -> Roadmap:
    """Switches a roadmap between 'project-based' and 'theory-first' with meaningfully distinct milestones."""
    if current.learning_style == new_style:
        return current

    # Create GoalInput from current roadmap and re-synthesize matching current progress
    goal_input = GoalInput(
        goal=current.goal,
        skill_level=current.skill_level,
        hours_per_week=current.hours_per_week,
        target_timeframe_weeks=current.target_timeframe_weeks,
        learning_style=new_style,
    )

    fresh_roadmap = synthesize_local_roadmap(goal_input)
    fresh_roadmap.id = current.id
    fresh_roadmap.created_at = current.created_at
    fresh_roadmap.checkins = current.checkins
    fresh_roadmap.badges_earned = list(current.badges_earned)
    if "Style Explorer 🔄" not in fresh_roadmap.badges_earned:
        fresh_roadmap.badges_earned.append("Style Explorer 🔄")

    # Retain completion state for equivalent count of milestones
    completed_count = current.completed_milestones
    for i in range(min(completed_count, len(fresh_roadmap.milestones))):
        fresh_roadmap.milestones[i].status = "done"

    total, completed, pct = calculate_progress(fresh_roadmap.milestones)
    fresh_roadmap.total_milestones = total
    fresh_roadmap.completed_milestones = completed
    fresh_roadmap.progress_percentage = pct

    # Log style change
    style_label = "Project-Based (hands-on code & deliverables)" if new_style == "project-based" else "Theory-First (deep conceptual principles & architecture)"
    fresh_roadmap.adjustment_logs = list(current.adjustment_logs)
    fresh_roadmap.adjustment_logs.insert(
        0,
        AdjustmentLog(
            timestamp=datetime.now().isoformat(),
            pace="style_toggle",
            summary=f"Switched learning philosophy to {new_style.upper()}.",
            details=[
                f"Reconstructed all milestones with {style_label} priorities.",
                "Updated resource materials from academic texts to practical build tutorials (or vice-versa).",
                "Retained completed progress count across transitions."
            ],
            reasons=f"Roadmap re-architected to align with your {new_style} learning preference.",
        ),
    )
    fresh_roadmap.mentor_advice = f"Switched to {new_style.upper()} learning! Milestones now emphasize {style_label}."

    return fresh_roadmap

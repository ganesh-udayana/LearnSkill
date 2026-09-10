import os
import uuid
import requests
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Response, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    Roadmap,
    GoalInput,
    CheckinInput,
    AdjustInput,
    ToggleStyleInput,
    UpdateMilestoneStatusInput,
    MilestoneNoteInput,
    Checkin,
    RegisterInput,
    LoginInput,
    AuthResponse,
)
from app.database import (
    init_db,
    save_roadmap,
    get_roadmap,
    get_latest_roadmap,
    list_roadmaps,
    delete_roadmap,
    record_checkin,
    create_user,
    verify_user,
    create_session,
    get_session_user,
    delete_session,
    get_user_by_username,
    get_user_by_email,
)
from app.ai_engine import (
    generate_roadmap as ai_generate_roadmap,
    adjust_roadmap as ai_adjust_roadmap,
    toggle_roadmap_style as ai_toggle_roadmap_style,
    calculate_progress,
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="PathPulse AI: Personalized Learning Roadmap Generator",
    description="Adaptive AI-powered milestone-based learning roadmap generator with progress check-ins and mentor adjustments.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local dev and embedded iframes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(authorization: Optional[str] = Header(None)):
    """Resolves the bearer token from the Authorization header into a user, or None."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return get_session_user(token)


def require_user(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


def supabase_auth_request(path: str, payload: dict) -> dict:
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=503, detail="Supabase Authentication is not configured.")

    try:
        response = requests.post(
            f"{supabase_url}/auth/v1/{path}",
            headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Unable to reach Supabase Authentication.")

    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        detail = data.get("msg") or data.get("error_description") or data.get("message")
        raise HTTPException(status_code=response.status_code, detail=detail or "Supabase Authentication failed.")
    return data


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterInput):
    existing = get_user_by_username(payload.username) or get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="That username or email is already registered.")

    auth_data = supabase_auth_request(
        "signup",
        {"email": payload.email.strip().lower(), "password": payload.password},
    )
    try:
        # Keep a local password hash so the app can work while Supabase email
        # confirmation is enabled and no access token is returned yet.
        user = create_user(payload.username, payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    token = create_session(user["id"], user["username"])
    return AuthResponse(token=token, username=user["username"])


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginInput):
    identifier = payload.username.strip()
    local_user = get_user_by_username(identifier) or get_user_by_email(identifier)
    email = identifier.lower()
    if local_user and local_user.get("email"):
        email = local_user["email"]

    try:
        supabase_data = supabase_auth_request(
            "token?grant_type=password",
            {"email": email, "password": payload.password},
        )
    except HTTPException as error:
        # Keep existing locally-created accounts usable during migration.
        fallback_username = local_user["username"] if local_user else identifier
        user = verify_user(fallback_username, payload.password)
        if not user:
            raise error
    else:
        user = local_user or get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=401, detail="Account profile is not available yet.")

    token = create_session(user["id"], user["username"])
    return AuthResponse(token=token, username=user["username"])


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.lower().startswith("bearer "):
        delete_session(authorization.split(" ", 1)[1].strip())
    return {"status": "logged_out"}


@app.get("/api/auth/me")
def me(user: dict = Depends(require_user)):
    return {"username": user["username"]}


@app.get("/api/samples")
def get_sample_roadmaps():
    samples_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_roadmaps.json")
    if os.path.exists(samples_path):
        import json
        with open(samples_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"samples": []}


@app.post("/api/roadmaps/generate", response_model=Roadmap)
async def generate_roadmap(
    payload: GoalInput,
    user: Optional[dict] = Depends(get_current_user),
):
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Learning goal cannot be empty.")
    roadmap = await ai_generate_roadmap(payload)
    saved = save_roadmap(roadmap, user["id"] if user else None)
    return saved


@app.get("/api/roadmaps", response_model=List[dict])
def get_all_roadmaps(user: Optional[dict] = Depends(get_current_user)):
    return list_roadmaps(user["id"] if user else None)


@app.get("/api/roadmaps/latest", response_model=Optional[Roadmap])
def get_latest_saved_roadmap(user: Optional[dict] = Depends(get_current_user)):
    return get_latest_roadmap(user["id"] if user else None)


@app.get("/api/roadmaps/{roadmap_id}", response_model=Roadmap)
def get_single_roadmap(roadmap_id: str):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")
    return rm


@app.delete("/api/roadmaps/{roadmap_id}")
def remove_roadmap(roadmap_id: str):
    success = delete_roadmap(roadmap_id)
    if not success:
        raise HTTPException(status_code=404, detail="Roadmap not found.")
    return {"status": "deleted", "id": roadmap_id}


@app.post("/api/roadmaps/{roadmap_id}/checkin", response_model=Roadmap)
async def checkin_progress(roadmap_id: str, payload: CheckinInput):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")

    found = False
    for m in rm.milestones:
        if m.id == payload.milestone_id:
            m.status = payload.status
            if payload.notes:
                m.notes = payload.notes
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Milestone not found in roadmap.")

    # Record checkin entry
    checkin_entry = Checkin(
        id=f"chk_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now().isoformat(),
        milestone_id=payload.milestone_id,
        status=payload.status,
        pace=payload.pace,
        struggling_topics=payload.struggling_topics,
        notes=payload.notes,
    )
    record_checkin(roadmap_id, checkin_entry)
    rm.checkins.append(checkin_entry)

    # Recalculate progress & badges
    total, completed, pct = calculate_progress(rm.milestones)
    rm.total_milestones = total
    rm.completed_milestones = completed
    rm.progress_percentage = pct
    rm.updated_at = datetime.now().isoformat()

    badges = list(rm.badges_earned)
    if completed >= 1 and "First Step Taken ⚡" not in badges:
        badges.append("First Step Taken ⚡")
    if pct >= 50.0 and "Halfway Hero 🚀" not in badges:
        badges.append("Halfway Hero 🚀")
    if pct >= 100.0 and "Mastery Unlocked 🎓" not in badges:
        badges.append("Mastery Unlocked 🎓")
    if payload.notes and "Reflective Scholar 📝" not in badges:
        badges.append("Reflective Scholar 📝")
    rm.badges_earned = badges

    saved = save_roadmap(rm)
    return saved


@app.post("/api/roadmaps/{roadmap_id}/adjust", response_model=Roadmap)
async def adjust_roadmap(roadmap_id: str, payload: AdjustInput):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")

    adjusted_rm = await ai_adjust_roadmap(rm, payload)
    saved = save_roadmap(adjusted_rm)
    return saved


@app.post("/api/roadmaps/{roadmap_id}/toggle-style", response_model=Roadmap)
async def toggle_style(roadmap_id: str, payload: ToggleStyleInput):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")

    updated_rm = await ai_toggle_roadmap_style(rm, payload.learning_style)
    saved = save_roadmap(updated_rm)
    return saved


@app.patch("/api/roadmaps/{roadmap_id}/milestones/{milestone_id}/status", response_model=Roadmap)
def update_status(roadmap_id: str, milestone_id: str, payload: UpdateMilestoneStatusInput):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")

    found = False
    for m in rm.milestones:
        if m.id == milestone_id:
            m.status = payload.status
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Milestone not found.")

    total, completed, pct = calculate_progress(rm.milestones)
    rm.total_milestones = total
    rm.completed_milestones = completed
    rm.progress_percentage = pct
    rm.updated_at = datetime.now().isoformat()

    badges = list(rm.badges_earned)
    if completed >= 1 and "First Step Taken ⚡" not in badges:
        badges.append("First Step Taken ⚡")
    if pct >= 50.0 and "Halfway Hero 🚀" not in badges:
        badges.append("Halfway Hero 🚀")
    if pct >= 100.0 and "Mastery Unlocked 🎓" not in badges:
        badges.append("Mastery Unlocked 🎓")
    rm.badges_earned = badges

    saved = save_roadmap(rm)
    return saved


@app.post("/api/roadmaps/{roadmap_id}/milestones/{milestone_id}/notes", response_model=Roadmap)
def save_milestone_notes(roadmap_id: str, milestone_id: str, payload: MilestoneNoteInput):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")

    found = False
    for m in rm.milestones:
        if m.id == milestone_id:
            m.notes = payload.notes
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Milestone not found.")

    badges = list(rm.badges_earned)
    if payload.notes.strip() and "Reflective Scholar 📝" not in badges:
        badges.append("Reflective Scholar 📝")
    rm.badges_earned = badges
    rm.updated_at = datetime.now().isoformat()

    saved = save_roadmap(rm)
    return saved


@app.get("/api/roadmaps/{roadmap_id}/share")
def get_shareable_view(roadmap_id: str):
    """Provides a clean public read-only JSON payload for sharing."""
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")
    return {
        "read_only": True,
        "goal": rm.goal,
        "skill_level": rm.skill_level,
        "learning_style": rm.learning_style,
        "target_timeframe_weeks": rm.target_timeframe_weeks,
        "hours_per_week": rm.hours_per_week,
        "progress_percentage": rm.progress_percentage,
        "completed_milestones": rm.completed_milestones,
        "total_milestones": rm.total_milestones,
        "milestones": [
            {
                "phase": m.phase,
                "title": m.title,
                "description": m.description,
                "duration_days": m.duration_days,
                "status": m.status,
                "deliverable": m.project_deliverable,
                "resources": [r.model_dump() for r in m.resources],
            }
            for m in rm.milestones
        ],
        "mentor_advice": rm.mentor_advice,
        "badges": rm.badges_earned,
    }


@app.get("/api/roadmaps/{roadmap_id}/export/markdown")
def export_markdown(roadmap_id: str):
    rm = get_roadmap(roadmap_id)
    if not rm:
        raise HTTPException(status_code=404, detail="Roadmap not found.")

    md = []
    md.append(f"# Personalized Learning Roadmap: {rm.goal}\n")
    md.append(f"- **Skill Level**: {rm.skill_level.title()}")
    md.append(f"- **Pace**: {rm.hours_per_week} hrs/week over {rm.target_timeframe_weeks} weeks")
    md.append(f"- **Philosophy**: {rm.learning_style.title()}")
    md.append(f"- **Progress**: {rm.progress_percentage}% ({rm.completed_milestones}/{rm.total_milestones} milestones completed)\n")

    if rm.mentor_advice:
        md.append(f"> **Mentor Note**: {rm.mentor_advice}\n")

    current_phase = None
    for idx, m in enumerate(rm.milestones, 1):
        if m.phase != current_phase:
            current_phase = m.phase
            md.append(f"\n## {current_phase}\n")

        status_emoji = "✅ [DONE]" if m.status == "done" else ("⏳ [IN PROGRESS]" if m.status == "in_progress" else "⭕ [NOT STARTED]")
        md.append(f"### Milestone {idx}: {m.title} {status_emoji}")
        md.append(f"*{m.duration_days} days ({m.duration_hours} hours estimated)*\n")
        md.append(f"{m.description}\n")

        if m.project_deliverable:
            md.append(f"**Deliverable**: {m.project_deliverable}\n")

        if m.checklist:
            md.append("**Checklist**:")
            for item in m.checklist:
                md.append(f"- [ ] {item}")
            md.append("")

        if m.resources:
            md.append("**Free Resources**:")
            for r in m.resources:
                md.append(f"- [{r.title}]({r.url}) — *{r.platform}* ({r.type}, {r.level}, {r.estimated_time})")
            md.append("")

        if m.notes:
            md.append(f"**My Notes/Journal**:\n> {m.notes}\n")

    filename = f"roadmap_{rm.id}.md"
    return PlainTextResponse(
        content="\n".join(md),
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# Serve frontend static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_home():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/login")
    def serve_login():
        return FileResponse(os.path.join(static_dir, "login.html"))

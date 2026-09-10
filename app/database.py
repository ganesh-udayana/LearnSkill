import json
import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Text,
    ForeignKey,
    inspect,
    select,
    delete as sql_delete,
    insert,
    text,
    update as sql_update,
)
from app.schemas import Roadmap, Checkin

# Load environment variables from .env
load_dotenv()

# Database URL configuration
# Default is local SQLite in ./data/roadmaps.db
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./data/roadmaps.db"

# Fix common Heroku / Supabase postgres:// prefix to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ensure data directory exists if using default SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "").lstrip(".")
    db_dir = os.path.dirname(db_path.lstrip("/\\"))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# Create SQLAlchemy engine
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
metadata = MetaData()
_database_initialized = False

# Define tables
roadmaps_table = Table(
    "roadmaps",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("user_id", String(64), ForeignKey("users.id", ondelete="CASCADE")),
    Column("goal", Text, nullable=False),
    Column("skill_level", String(32)),
    Column("hours_per_week", Integer),
    Column("target_timeframe_weeks", Integer),
    Column("learning_style", String(32)),
    Column("created_at", String(64)),
    Column("updated_at", String(64)),
    Column("data_json", Text, nullable=False),
)

checkins_table = Table(
    "checkins",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("roadmap_id", String(64), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False),
    Column("milestone_id", String(64), nullable=False),
    Column("timestamp", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("pace", String(32), nullable=False),
    Column("struggling_topics", Text),
    Column("notes", Text),
)

app_settings_table = Table(
    "app_settings",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("value", Text),
)

users_table = Table(
    "users",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(128)),
    Column("email", String(128)),
    Column("username", String(64), nullable=False, unique=True),
    Column("password_hash", String(256), nullable=False),
    Column("salt", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("token", String(128), primary_key=True),
    Column("user_id", String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("username", String(64), nullable=False),
    Column("created_at", String(64), nullable=False),
    Column("expires_at", String(64), nullable=False),
)


def init_db():
    """Initializes tables in whatever database is configured (SQLite, PostgreSQL, Supabase)."""
    global _database_initialized
    if _database_initialized:
        return
    metadata.create_all(engine)
    _migrate_auth_schema()
    _migrate_roadmap_schema()
    _database_initialized = True


def _migrate_auth_schema():
    """Adds auth columns that may be missing from an older database schema."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}

    with engine.begin() as conn:
        if "username" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(64)"))
            if "email" in columns:
                conn.execute(
                    text("UPDATE users SET username = SUBSTR(email, 1, 64) WHERE username IS NULL")
                )
            else:
                conn.execute(
                    text("UPDATE users SET username = 'user_' || SUBSTR(id, 1, 55) WHERE username IS NULL")
                )

        for column_name, column_type in (
            ("name", "VARCHAR(128)"),
            ("email", "VARCHAR(128)"),
            ("password_hash", "VARCHAR(256)"),
            ("salt", "VARCHAR(64)"),
            ("created_at", "VARCHAR(64)"),
        ):
            if column_name not in columns:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))

        conn.execute(text("UPDATE users SET name = username WHERE name IS NULL"))
        conn.execute(text("UPDATE users SET email = username WHERE email IS NULL"))

        conn.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username_unique ON users (username)")
        )


def _migrate_roadmap_schema():
    inspector = inspect(engine)
    if "roadmaps" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("roadmaps")}
    if "user_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE roadmaps ADD COLUMN user_id VARCHAR(64)"))


def save_roadmap(roadmap: Roadmap, user_id: Optional[str] = None) -> Roadmap:
    init_db()
    data_json = roadmap.model_dump_json()
    now_str = datetime.now().isoformat()

    with engine.begin() as conn:
        # Check if exists
        stmt = select(roadmaps_table.c.id).where(roadmaps_table.c.id == roadmap.id)
        exists = conn.execute(stmt).fetchone()

        if exists:
            values = {
                "goal": roadmap.goal,
                "skill_level": roadmap.skill_level,
                "hours_per_week": roadmap.hours_per_week,
                "target_timeframe_weeks": roadmap.target_timeframe_weeks,
                "learning_style": roadmap.learning_style,
                "updated_at": now_str,
                "data_json": data_json,
            }
            if user_id is not None:
                values["user_id"] = user_id
            update_stmt = sql_update(roadmaps_table).where(
                roadmaps_table.c.id == roadmap.id
            ).values(**values)
            conn.execute(update_stmt)
        else:
            insert_stmt = insert(roadmaps_table).values(
                id=roadmap.id,
                user_id=user_id,
                goal=roadmap.goal,
                skill_level=roadmap.skill_level,
                hours_per_week=roadmap.hours_per_week,
                target_timeframe_weeks=roadmap.target_timeframe_weeks,
                learning_style=roadmap.learning_style,
                created_at=roadmap.created_at or now_str,
                updated_at=now_str,
                data_json=data_json,
            )
            conn.execute(insert_stmt)

    return roadmap


def get_roadmap(roadmap_id: str) -> Optional[Roadmap]:
    init_db()
    with engine.connect() as conn:
        stmt = select(roadmaps_table.c.data_json).where(roadmaps_table.c.id == roadmap_id)
        row = conn.execute(stmt).fetchone()
        if row:
            return Roadmap.model_validate_json(row[0])
    return None


def get_latest_roadmap(user_id: Optional[str] = None) -> Optional[Roadmap]:
    init_db()
    with engine.connect() as conn:
        stmt = select(roadmaps_table.c.data_json).order_by(roadmaps_table.c.updated_at.desc()).limit(1)
        if user_id:
            stmt = stmt.where(roadmaps_table.c.user_id == user_id)
        row = conn.execute(stmt).fetchone()
        if row:
            return Roadmap.model_validate_json(row[0])
    return None


def list_roadmaps(user_id: Optional[str] = None) -> List[dict]:
    init_db()
    results = []
    with engine.connect() as conn:
        stmt = select(
            roadmaps_table.c.id,
            roadmaps_table.c.goal,
            roadmaps_table.c.skill_level,
            roadmaps_table.c.hours_per_week,
            roadmaps_table.c.target_timeframe_weeks,
            roadmaps_table.c.learning_style,
            roadmaps_table.c.created_at,
            roadmaps_table.c.updated_at,
            roadmaps_table.c.data_json,
        ).order_by(roadmaps_table.c.updated_at.desc())

        if user_id:
            stmt = stmt.where(roadmaps_table.c.user_id == user_id)
        rows = conn.execute(stmt.limit(20)).fetchall()
        for r in rows:
            parsed = json.loads(r.data_json)
            results.append(
                {
                    "id": r.id,
                    "goal": r.goal,
                    "skill_level": r.skill_level,
                    "hours_per_week": r.hours_per_week,
                    "target_timeframe_weeks": r.target_timeframe_weeks,
                    "learning_style": r.learning_style,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "total_milestones": parsed.get("total_milestones", 0),
                    "completed_milestones": parsed.get("completed_milestones", 0),
                    "progress_percentage": parsed.get("progress_percentage", 0.0),
                }
            )
    return results


def delete_roadmap(roadmap_id: str) -> bool:
    init_db()
    with engine.begin() as conn:
        stmt = sql_delete(roadmaps_table).where(roadmaps_table.c.id == roadmap_id)
        res = conn.execute(stmt)
        return res.rowcount > 0


def record_checkin(roadmap_id: str, checkin: Checkin):
    init_db()
    with engine.begin() as conn:
        stmt = insert(checkins_table).values(
            id=checkin.id,
            roadmap_id=roadmap_id,
            milestone_id=checkin.milestone_id,
            timestamp=checkin.timestamp,
            status=checkin.status,
            pace=checkin.pace,
            struggling_topics=checkin.struggling_topics,
            notes=checkin.notes,
        )
        conn.execute(stmt)


# ---------------------------------------------------------------------------
# User authentication
# ---------------------------------------------------------------------------
import hashlib
import hmac
import secrets
import uuid as _uuid


def _hash_password(password: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256 password hash. No extra deps required."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return dk.hex()


def create_user(username: str, email: str, password: str) -> dict:
    """Creates a new user. Raises ValueError if the username is taken."""
    init_db()
    username = username.strip()
    email = email.strip().lower()
    with engine.begin() as conn:
        existing = conn.execute(
            select(users_table.c.id).where(users_table.c.username == username)
        ).fetchone()
        if existing:
            raise ValueError("That username is already taken.")
        existing_email = conn.execute(
            select(users_table.c.id).where(users_table.c.email == email)
        ).fetchone()
        if existing_email:
            raise ValueError("That email is already registered.")

        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        user_id = f"usr_{_uuid.uuid4().hex[:12]}"
        now_str = datetime.now().isoformat()

        conn.execute(
            insert(users_table).values(
                id=user_id,
                name=username,
                email=email,
                username=username,
                password_hash=password_hash,
                salt=salt,
                created_at=now_str,
            )
        )
    return {"id": user_id, "username": username}


def get_user_by_username(username: str) -> Optional[dict]:
    init_db()
    with engine.connect() as conn:
        row = conn.execute(
            select(users_table.c.id, users_table.c.username, users_table.c.email).where(
                users_table.c.username == username.strip()
            )
        ).fetchone()
    if not row:
        return None
    return {"id": row.id, "username": row.username, "email": row.email}


def get_user_by_email(email: str) -> Optional[dict]:
    init_db()
    with engine.connect() as conn:
        row = conn.execute(
            select(users_table.c.id, users_table.c.username, users_table.c.email).where(
                users_table.c.email == email.strip().lower()
            )
        ).fetchone()
    if not row:
        return None
    return {"id": row.id, "username": row.username, "email": row.email}


def verify_user(username: str, password: str) -> Optional[dict]:
    """Returns the user dict if credentials are valid, otherwise None."""
    init_db()
    with engine.connect() as conn:
        row = conn.execute(
            select(
                users_table.c.id,
                users_table.c.username,
                users_table.c.password_hash,
                users_table.c.salt,
            ).where(users_table.c.username == username.strip())
        ).fetchone()

    if not row:
        return None

    candidate_hash = _hash_password(password, row.salt)
    if not hmac.compare_digest(candidate_hash, row.password_hash):
        return None

    return {"id": row.id, "username": row.username}


def create_session(user_id: str, username: str, ttl_days: int = 30) -> str:
    init_db()
    from datetime import timedelta

    token = secrets.token_hex(32)
    now = datetime.now()
    expires = now + timedelta(days=ttl_days)

    with engine.begin() as conn:
        conn.execute(
            insert(sessions_table).values(
                token=token,
                user_id=user_id,
                username=username,
                created_at=now.isoformat(),
                expires_at=expires.isoformat(),
            )
        )
    return token


def get_session_user(token: str) -> Optional[dict]:
    if not token:
        return None
    init_db()
    with engine.connect() as conn:
        row = conn.execute(
            select(sessions_table.c.user_id, sessions_table.c.username, sessions_table.c.expires_at).where(
                sessions_table.c.token == token
            )
        ).fetchone()

    if not row:
        return None

    if datetime.fromisoformat(row.expires_at) < datetime.now():
        delete_session(token)
        return None

    return {"id": row.user_id, "username": row.username}


def delete_session(token: str) -> bool:
    init_db()
    with engine.begin() as conn:
        res = conn.execute(sql_delete(sessions_table).where(sessions_table.c.token == token))
        return res.rowcount > 0

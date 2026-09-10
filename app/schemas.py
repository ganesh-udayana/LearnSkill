from typing import List, Optional
from pydantic import BaseModel, Field


class Resource(BaseModel):
    title: str = Field(..., description="Name of the free learning resource")
    url: str = Field(..., description="Link to the resource")
    platform: str = Field(..., description="Host platform (e.g., MDN, freeCodeCamp, Kaggle, Coursera, YouTube, Khan Academy)")
    type: str = Field("interactive", description="Format type: interactive, video, article, course, documentation")
    level: str = Field("beginner", description="Resource difficulty: beginner, intermediate, advanced")
    estimated_time: str = Field("3-5 hours", description="Estimated completion time")


class Milestone(BaseModel):
    id: str = Field(..., description="Unique identifier for the milestone")
    phase: str = Field(..., description="Parent phase name, e.g. 'Phase 1: Core Foundations'")
    phase_number: int = Field(1, description="Sequential phase order")
    title: str = Field(..., description="Topic or milestone title")
    description: str = Field(..., description="Concise explanation of learning objectives and key concepts")
    duration_days: int = Field(7, description="Estimated duration in calendar days")
    duration_hours: int = Field(10, description="Estimated total study hours required")
    learning_style: str = Field("project-based", description="project-based or theory-first")
    status: str = Field("not_started", description="not_started, in_progress, done")
    resources: List[Resource] = Field(default_factory=list, description="1-3 curated free resources")
    project_deliverable: Optional[str] = Field(None, description="Hands-on mini-project or deliverable for this milestone")
    checklist: List[str] = Field(default_factory=list, description="Key skills or checkpoints to master")
    notes: Optional[str] = Field(None, description="User notes or journal reflection for this milestone")


class Checkin(BaseModel):
    id: str
    timestamp: str
    milestone_id: str
    status: str = "done"  # not_started, in_progress, done
    pace: str = "on_track"  # ahead, on_track, behind
    struggling_topics: Optional[str] = None
    notes: Optional[str] = None


class AdjustmentLog(BaseModel):
    timestamp: str
    pace: str
    summary: str
    details: List[str] = Field(default_factory=list)
    reasons: str


class Roadmap(BaseModel):
    id: str
    goal: str
    skill_level: str = "beginner"
    hours_per_week: int = 10
    target_timeframe_weeks: int = 10
    learning_style: str = "project-based"  # project-based vs theory-first
    total_milestones: int = 0
    completed_milestones: int = 0
    progress_percentage: float = 0.0
    created_at: str
    updated_at: str
    phases: List[str] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)
    checkins: List[Checkin] = Field(default_factory=list)
    adjustment_logs: List[AdjustmentLog] = Field(default_factory=list)
    mentor_advice: Optional[str] = None
    current_streak_days: int = 1
    badges_earned: List[str] = Field(default_factory=list)


# Request schemas
class GoalInput(BaseModel):
    goal: str
    skill_level: str = "beginner"  # beginner, intermediate, advanced
    hours_per_week: int = 10
    target_timeframe_weeks: int = 10
    learning_style: str = "project-based"  # project-based or theory-first
    api_key: Optional[str] = None
    ai_provider: Optional[str] = "gemini"  # gemini, openai, or smart_fallback


class CheckinInput(BaseModel):
    milestone_id: str
    status: str = "done"  # not_started, in_progress, done
    pace: str = "on_track"  # ahead, on_track, behind
    struggling_topics: Optional[str] = None
    notes: Optional[str] = None


class AdjustInput(BaseModel):
    pace: str = "behind"  # ahead, on_track, behind
    struggling_topics: Optional[str] = None
    general_feedback: Optional[str] = None
    api_key: Optional[str] = None
    ai_provider: Optional[str] = "gemini"


class MilestoneNoteInput(BaseModel):
    notes: str


class ToggleStyleInput(BaseModel):
    learning_style: str  # project-based or theory-first
    api_key: Optional[str] = None
    ai_provider: Optional[str] = "gemini"


class UpdateMilestoneStatusInput(BaseModel):
    status: str  # not_started, in_progress, done


class RegisterInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=128)
    password: str = Field(..., min_length=6, max_length=128)


class LoginInput(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    username: str

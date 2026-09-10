import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_samples_endpoint():
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert len(data["samples"]) > 0


def test_generate_roadmap():
    payload = {
        "goal": "Become a Data Analyst in 10 weeks",
        "skill_level": "beginner",
        "hours_per_week": 10,
        "target_timeframe_weeks": 10,
        "learning_style": "project-based",
        "ai_provider": "smart_fallback",
    }
    response = client.post("/api/roadmaps/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["goal"] == payload["goal"]
    assert len(data["milestones"]) >= 3
    assert len(data["phases"]) >= 2

    first_milestone = data["milestones"][0]
    assert "title" in first_milestone
    assert "duration_days" in first_milestone
    assert "resources" in first_milestone
    assert len(first_milestone["resources"]) >= 1

    # Verify resource quality tag fields
    first_res = first_milestone["resources"][0]
    assert "platform" in first_res
    assert "level" in first_res
    assert "estimated_time" in first_res


def test_checkin_flow():
    # First generate a roadmap
    payload = {
        "goal": "Frontend Developer",
        "skill_level": "beginner",
        "hours_per_week": 15,
        "target_timeframe_weeks": 12,
        "learning_style": "project-based",
    }
    gen_res = client.post("/api/roadmaps/generate", json=payload)
    roadmap = gen_res.json()
    rm_id = roadmap["id"]
    first_m_id = roadmap["milestones"][0]["id"]

    # Checkin milestone as done
    checkin_payload = {
        "milestone_id": first_m_id,
        "status": "done",
        "pace": "on_track",
        "struggling_topics": None,
        "notes": "Built my portfolio site using HTML and CSS grid!",
    }
    chk_res = client.post(f"/api/roadmaps/{rm_id}/checkin", json=checkin_payload)
    assert chk_res.status_code == 200
    updated = chk_res.json()
    assert updated["completed_milestones"] >= 1
    assert updated["progress_percentage"] > 0
    assert any("First Step Taken" in b for b in updated["badges_earned"])
    assert any("Reflective Scholar" in b for b in updated["badges_earned"])


def test_ai_adjustment_behind():
    # Generate roadmap
    payload = {
        "goal": "Data Analyst",
        "skill_level": "beginner",
        "hours_per_week": 10,
        "target_timeframe_weeks": 10,
        "learning_style": "project-based",
    }
    gen_res = client.post("/api/roadmaps/generate", json=payload)
    rm = gen_res.json()
    rm_id = rm["id"]

    # Submit adjustment reporting behind with SQL struggles
    adjust_payload = {
        "pace": "behind",
        "struggling_topics": "SQL window functions and complex joins",
        "general_feedback": "Need more practice drills",
    }
    adj_res = client.post(f"/api/roadmaps/{rm_id}/adjust", json=adjust_payload)
    assert adj_res.status_code == 200
    adj_data = adj_res.json()

    # Verify mentor change explanation is present
    assert len(adj_data["adjustment_logs"]) > 0
    latest_log = adj_data["adjustment_logs"][0]
    assert latest_log["pace"] == "behind"
    assert "SQL" in latest_log["reasons"] or "behind" in latest_log["reasons"]
    assert len(latest_log["details"]) > 0
    assert any("Resilient Learner" in b for b in adj_data["badges_earned"])


def test_toggle_learning_style():
    # Generate project-based roadmap
    payload = {
        "goal": "Data Analyst",
        "skill_level": "beginner",
        "hours_per_week": 10,
        "target_timeframe_weeks": 10,
        "learning_style": "project-based",
    }
    gen_res = client.post("/api/roadmaps/generate", json=payload)
    rm = gen_res.json()
    rm_id = rm["id"]
    original_m1_title = rm["milestones"][0]["title"]

    # Toggle to theory-first
    toggle_payload = {"learning_style": "theory-first"}
    toggle_res = client.post(f"/api/roadmaps/{rm_id}/toggle-style", json=toggle_payload)
    assert toggle_res.status_code == 200
    theory_rm = toggle_res.json()
    assert theory_rm["learning_style"] == "theory-first"
    new_m1_title = theory_rm["milestones"][0]["title"]

    # Verify meaningful distinction in curriculum
    assert new_m1_title != original_m1_title
    assert "Statistics" in new_m1_title or "Probability" in new_m1_title or "Theory" in new_m1_title


def test_export_markdown_and_share():
    # Generate roadmap
    payload = {
        "goal": "Full-Stack Web Developer",
        "skill_level": "beginner",
        "hours_per_week": 10,
        "target_timeframe_weeks": 8,
        "learning_style": "project-based",
    }
    gen_res = client.post("/api/roadmaps/generate", json=payload)
    rm = gen_res.json()
    rm_id = rm["id"]

    # Test Markdown export
    md_res = client.get(f"/api/roadmaps/{rm_id}/export/markdown")
    assert md_res.status_code == 200
    assert "# Personalized Learning Roadmap" in md_res.text
    assert "Full-Stack Web Developer" in md_res.text

    # Test Public Read-Only Share
    share_res = client.get(f"/api/roadmaps/{rm_id}/share")
    assert share_res.status_code == 200
    share_data = share_res.json()
    assert share_data["read_only"] is True
    assert "milestones" in share_data

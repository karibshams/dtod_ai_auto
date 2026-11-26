"""Service layer for activity logging."""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import ActivityLog


def _activity_to_dict(log: ActivityLog) -> dict:
    return {
        "id": log.id,
        "agent": log.agent,
        "action": log.action,
        "details": log.details,
        "user_query": log.user_query,
        "success": log.success,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def log_activity(
    db: Session,
    agent: str,
    action: str,
    details: str | None = None,
    user_query: str | None = None,
    success: bool = True,
) -> dict:
    """Create an activity log entry and return it as a dict."""
    entry = ActivityLog(
        agent=agent,
        action=action,
        details=details,
        user_query=user_query,
        success=success,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _activity_to_dict(entry)


def get_recent_activities(db: Session, limit: int = 50) -> list[dict]:
    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_activity_to_dict(l) for l in logs]


def get_activities_by_agent(db: Session, agent: str) -> list[dict]:
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.agent == agent)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )
    return [_activity_to_dict(l) for l in logs]

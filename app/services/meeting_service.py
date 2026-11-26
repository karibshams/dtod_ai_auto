"""Service layer for meeting / scheduling operations."""

from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import Meeting, MeetingStatus


def _meeting_to_dict(meeting: Meeting) -> dict:
    return {
        "id": meeting.id,
        "title": meeting.title,
        "description": meeting.description,
        "organizer": meeting.organizer,
        "attendees": meeting.attendees.split(",") if meeting.attendees else [],
        "meeting_date": meeting.meeting_date.isoformat() if meeting.meeting_date else None,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "location": meeting.location,
        "status": meeting.status.value if meeting.status else None,
        "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
    }


def get_available_slots(db: Session, target_date: date) -> list:
    """Return 1-hour slots between 09:00-17:00 that are not booked on *target_date*."""
    # All possible 1-hour slots during business hours
    all_slots = []
    for hour in range(9, 17):
        start = f"{hour:02d}:00"
        end = f"{hour + 1:02d}:00"
        all_slots.append({"start_time": start, "end_time": end})

    # Fetch booked meetings for the date that are not cancelled
    booked = (
        db.query(Meeting.start_time, Meeting.end_time)
        .filter(
            Meeting.meeting_date == target_date,
            Meeting.status != MeetingStatus.CANCELLED,
        )
        .all()
    )
    booked_starts = {row.start_time for row in booked}

    available = [
        {**slot, "date": target_date.isoformat()}
        for slot in all_slots
        if slot["start_time"] not in booked_starts
    ]
    return available


def schedule_meeting(
    db: Session,
    title: str,
    description: str = None,
    organizer: str = None,
    attendees=None,
    meeting_date: date = None,
    start_time: str = None,
    end_time: str = None,
    location: str = None,
) -> dict:
    """Create a new meeting and return its dict representation."""
    if isinstance(attendees, (list, tuple)):
        attendees = ",".join(attendees)
    meeting = Meeting(
        title=title,
        description=description,
        organizer=organizer,
        attendees=attendees or "",
        meeting_date=meeting_date,
        start_time=start_time,
        end_time=end_time,
        location=location,
        status=MeetingStatus.SCHEDULED,
        created_at=datetime.utcnow(),
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _meeting_to_dict(meeting)


def get_meetings_by_date(db: Session, target_date: date) -> list:
    meetings = (
        db.query(Meeting)
        .filter(Meeting.meeting_date == target_date)
        .order_by(Meeting.start_time)
        .all()
    )
    return [_meeting_to_dict(m) for m in meetings]


def get_upcoming_meetings(db: Session, limit: int = 10) -> list:
    today = date.today()
    meetings = (
        db.query(Meeting)
        .filter(
            Meeting.meeting_date >= today,
            Meeting.status != MeetingStatus.CANCELLED,
        )
        .order_by(Meeting.meeting_date, Meeting.start_time)
        .limit(limit)
        .all()
    )
    return [_meeting_to_dict(m) for m in meetings]


def cancel_meeting(db: Session, meeting_id: int) -> bool:
    """Cancel a meeting by id. Returns True if found and cancelled, False otherwise."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        return False
    meeting.status = MeetingStatus.CANCELLED
    db.commit()
    return True


def get_meeting_stats(db: Session) -> dict:
    total = db.query(func.count(Meeting.id)).scalar() or 0

    status_counts = {}
    rows = (
        db.query(Meeting.status, func.count(Meeting.id))
        .group_by(Meeting.status)
        .all()
    )
    for status, count in rows:
        key = status.value if hasattr(status, "value") else str(status)
        status_counts[key] = count

    today = date.today()
    upcoming = (
        db.query(func.count(Meeting.id))
        .filter(
            Meeting.meeting_date >= today,
            Meeting.status == MeetingStatus.SCHEDULED,
        )
        .scalar()
    ) or 0

    return {
        "total_meetings": total,
        "meetings_by_status": status_counts,
        "upcoming_meetings": upcoming,
    }

"""Meeting Scheduling AI Agent for Dress 2 Decor."""

from datetime import date, timedelta
import re
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.agents.tools import MEETING_TOOLS

MEETING_SYSTEM_PROMPT = """You are the Meeting Scheduling Agent for Dress 2 Decor.
Your responsibilities:
1. Check available meeting slots on a given date (business hours 09:00-17:00, 1-hour slots) using `check_available_slots`.
2. Schedule new meetings using `schedule_meeting` with `date` (YYYY-MM-DD), `start_time` (HH:MM), `end_time` (HH:MM), `title`, `organizer`, `attendees`, and `location`.
   - IMPORTANT: Do NOT ask follow-up questions if `title`, `organizer`, `attendees`, or `location` are omitted. Use sensible defaults immediately (`title="Dress 2 Decor Meeting"`, `organizer="Dress 2 Decor Team"`, `attendees=""`, `location="Virtual"`, and 1 hour duration if `end_time` is omitted) and call `schedule_meeting` right away after checking slots.
3. List upcoming meetings or cancel existing meetings by ID.
4. Provide clear booking confirmations with date, time, and meeting ID."""


class MeetingAgent(BaseAgent):
    """Handles meeting slot checks, booking, listing, and cancellations."""

    def __init__(self):
        super().__init__(
            name="meeting_agent",
            system_prompt=MEETING_SYSTEM_PROMPT,
            tools=MEETING_TOOLS,
        )

    def _mock_tool_execution(
        self, message: str, db: Session, context: dict | None
    ) -> list[dict]:
        """Extend mock tool execution to support natural-language scheduling."""
        results = super()._mock_tool_execution(message, db, context)
        if results:
            return results

        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ("schedule", "book", "set up", "create")) and any(
            kw in msg_lower for kw in ("meeting", "call", "appointment", "consultation")
        ):
            # Determine date (explicit YYYY-MM-DD, "tomorrow", or today+1)
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", message)
            if date_match:
                target_date = date_match.group(0)
            elif "today" in msg_lower:
                target_date = date.today().isoformat()
            else:
                target_date = (date.today() + timedelta(days=1)).isoformat()

            # Determine time (e.g. "10am", "14:00", "2pm")
            time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", msg_lower)
            hour = 10
            minute = 0
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                ampm = time_match.group(3)
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
            if hour < 9 or hour >= 17:
                hour = 10

            start_time = f"{hour:02d}:{minute:02d}"
            end_time = f"{hour + 1:02d}:{minute:02d}"

            args = {
                "title": "Dress 2 Decor Consultation",
                "description": message,
                "organizer": (context or {}).get("organizer", "Dress 2 Decor Team"),
                "attendees": (context or {}).get("attendees", "Vendor / Customer"),
                "meeting_date": target_date,
                "start_time": start_time,
                "end_time": end_time,
                "location": "Virtual / Conference Room A",
            }
            result = self._tool_executor.execute("schedule_meeting", args, db)
            results.append(
                {"tool": "schedule_meeting", "arguments": args, "result": result}
            )
            return results

        # Fallback: show upcoming meetings if user asks generally about meetings
        if any(kw in msg_lower for kw in ("meeting", "calendar", "schedule")):
            result = self._tool_executor.execute("get_upcoming_meetings", {}, db)
            results.append(
                {"tool": "get_upcoming_meetings", "arguments": {}, "result": result}
            )
        return results

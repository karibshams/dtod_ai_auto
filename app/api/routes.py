"""FastAPI REST API and webhook routes for Dress 2 Decor."""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.agents import OrderAgent, VendorAgent, MeetingAgent, AnalystAgent, AgentRouter
from app.services import (
    order_service,
    vendor_service,
    meeting_service,
    product_service,
    analytics_service,
    activity_service,
)

router = APIRouter(prefix="/api", tags=["api"])

_AGENTS = {
    "order": OrderAgent(),
    "vendor": VendorAgent(),
    "meeting": MeetingAgent(),
    "analyst": AnalystAgent(),
}

# In-memory conversation history per session_id (last 10 messages)
_CONVERSATION_HISTORY: dict[str, list[dict]] = {}
_MAX_HISTORY_MESSAGES = 10


# ── Pydantic Schemas ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    agent_type: Optional[str] = None
    vendor_id: Optional[int] = None
    session_id: Optional[str] = "default"
    history: Optional[list[dict]] = None


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1)


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""
    organizer: str = Field(..., min_length=1, max_length=100)
    attendees: Optional[str] = ""
    meeting_date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    location: Optional[str] = "Virtual"


class WebhookEvent(BaseModel):
    event_type: str
    payload: dict = Field(default_factory=dict)


# ── Health & Config ──────────────────────────────────────────────

@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── AI Chat Endpoint ─────────────────────────────────────────────

@router.post("/chat")
async def chat_with_agent(req: ChatRequest, db: Session = Depends(get_db)):
    """Route a message to the appropriate AI agent and execute tools."""
    selected = AgentRouter.route(req.message, req.agent_type)
    agent = _AGENTS.get(selected, _AGENTS["order"])

    session_key = (req.session_id or "default").strip() or "default"
    history = req.history if req.history is not None else _CONVERSATION_HISTORY.get(session_key, [])

    context: dict = {"history": history[-_MAX_HISTORY_MESSAGES:]}
    if req.vendor_id is not None:
        context["vendor_id"] = req.vendor_id

    result = await agent.process(req.message, db, context=context)
    reply_text = result.get("response", "")

    # Persist turn in session history (skip validation errors if vendor_id was missing)
    if req.history is None and reply_text:
        sess_hist = _CONVERSATION_HISTORY.setdefault(session_key, [])
        sess_hist.append({"role": "user", "content": req.message})
        sess_hist.append({"role": "assistant", "content": reply_text})
        if len(sess_hist) > _MAX_HISTORY_MESSAGES:
            _CONVERSATION_HISTORY[session_key] = sess_hist[-_MAX_HISTORY_MESSAGES:]

    return {
        "agent": result.get("agent", selected),
        "routed_to": selected,
        "response": reply_text,
        "tool_results": result.get("tool_results", []),
        "chart": result.get("chart"),
        "ai_provider": get_settings().ai_provider,
        "session_id": session_key,
    }


# ── Analytics & Dashboard ────────────────────────────────────────

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return combined dashboard metrics, revenue by month, and status breakdown."""
    stats = analytics_service.get_dashboard_stats(db)
    order_stats = order_service.get_order_stats(db)
    stats["total_orders"] = stats["orders"]["total"]
    stats["total_revenue"] = stats["orders"]["revenue"]
    stats["active_vendors"] = stats["vendors"]["active"]
    stats["total_vendors"] = stats["vendors"]["total"]
    stats["total_products"] = stats["products"]["total"]
    stats["orders_by_status"] = order_stats.get("by_status", {})
    stats["revenue_by_month"] = analytics_service.get_revenue_by_month(db)
    stats["top_products"] = analytics_service.get_top_products(db, limit=5)
    stats["top_vendors"] = analytics_service.get_top_vendors(db, limit=5)
    return stats


# ── Orders ───────────────────────────────────────────────────────

@router.get("/orders")
def list_orders(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if status:
        orders = order_service.get_orders_by_status(db, status)
    else:
        orders = order_service.get_recent_orders(db, limit=limit)

    if search:
        q = search.lower()
        orders = [
            o for o in orders
            if q in (o.get("order_number") or "").lower()
            or q in (o.get("customer_name") or "").lower()
            or q in (o.get("customer_email") or "").lower()
        ]
    return {"orders": orders, "count": len(orders)}


@router.get("/orders/{order_number}")
def get_order(order_number: str, db: Session = Depends(get_db)):
    order = order_service.get_order_by_number(db, order_number)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_number} not found")
    return order


@router.patch("/orders/{order_number}/status")
def update_order_status(
    order_number: str, body: OrderStatusUpdate, db: Session = Depends(get_db)
):
    try:
        updated = order_service.update_order_status(db, order_number, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Order {order_number} not found")
    return updated


# ── Vendors ──────────────────────────────────────────────────────

@router.get("/vendors")
def list_vendors(db: Session = Depends(get_db)):
    vendors = vendor_service.get_all_vendors(db)
    return {"vendors": vendors, "count": len(vendors)}


@router.get("/vendors/{vendor_id}")
def get_vendor_details(vendor_id: int, db: Session = Depends(get_db)):
    vendor = vendor_service.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    vendor["products"] = vendor_service.get_vendor_products(db, vendor_id)
    vendor["orders"] = vendor_service.get_vendor_orders(db, vendor_id)
    vendor["commission_summary"] = vendor_service.get_vendor_commission_summary(
        db, vendor_id
    )
    return vendor


# ── Products ─────────────────────────────────────────────────────

@router.get("/products")
def list_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if search:
        products = product_service.search_products(db, search, category=category)
    elif category:
        products = product_service.get_products_by_category(db, category)
    else:
        products = product_service.get_all_products(db, limit=limit)
    return {"products": products, "count": len(products)}


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = product_service.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


# ── Meetings ─────────────────────────────────────────────────────

@router.get("/meetings")
def list_meetings(
    target_date: Optional[date] = Query(None, alias="date"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if target_date:
        meetings = meeting_service.get_meetings_by_date(db, target_date)
        slots = meeting_service.get_available_slots(db, target_date)
        return {"meetings": meetings, "available_slots": slots, "count": len(meetings)}
    meetings = meeting_service.get_upcoming_meetings(db, limit=limit)
    return {"meetings": meetings, "count": len(meetings)}


@router.get("/meetings/slots")
def available_slots(
    target_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    slots = meeting_service.get_available_slots(db, target_date)
    return {"date": target_date.isoformat(), "available_slots": slots}


@router.post("/meetings", status_code=201)
def create_meeting(body: MeetingCreate, db: Session = Depends(get_db)):
    try:
        meeting = meeting_service.schedule_meeting(
            db=db,
            title=body.title,
            description=body.description or "",
            organizer=body.organizer,
            attendees=body.attendees or "",
            meeting_date=body.meeting_date,
            start_time=body.start_time,
            end_time=body.end_time,
            location=body.location or "Virtual",
        )
        activity_service.log_activity(
            db=db,
            agent="meeting_api",
            action="schedule_meeting",
            details=f"Scheduled '{body.title}' on {body.meeting_date} {body.start_time}",
            user_query="API meeting creation",
            success=True,
        )
        return meeting
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/meetings/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    cancelled = meeting_service.cancel_meeting(db, meeting_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return {"status": "cancelled", "meeting_id": meeting_id}


# ── Activity Log ─────────────────────────────────────────────────

@router.get("/activities")
def list_activities(
    agent: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if agent:
        activities = activity_service.get_activities_by_agent(db, agent)
    else:
        activities = activity_service.get_recent_activities(db, limit=limit)
    return {"activities": activities, "count": len(activities)}


# ── Automation Webhook ───────────────────────────────────────────

@router.post("/webhooks/automation")
async def automation_webhook(event: WebhookEvent, db: Session = Depends(get_db)):
    """Receive external webhook triggers (e.g., from n8n or order events)."""
    activity_service.log_activity(
        db=db,
        agent="webhook",
        action=event.event_type,
        details=str(event.payload),
        user_query=f"Webhook: {event.event_type}",
        success=True,
    )
    return {"status": "received", "event_type": event.event_type}

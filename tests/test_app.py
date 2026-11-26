"""End-to-end test suite for Dress 2 Decor AI Automation System."""

import asyncio
import os
from datetime import date, timedelta
import httpx
import pytest

# Force mock AI provider & isolated test DB before importing app
os.environ["AI_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_dtod.db"

from app.core.config import get_settings
get_settings.cache_clear()

from app.core.database import Base, engine
from app.main import app
from seed_data import main as seed_database


def _request(method: str, url: str, **kwargs) -> httpx.Response:
    async def _call():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(_call())


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Set up a fresh seeded database for the test module."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_dtod.db"):
        try:
            os.remove("test_dtod.db")
        except OSError:
            pass


def test_health_endpoint():
    resp = _request("GET", "/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ai_provider"] == "mock"


def test_dashboard_html():
    resp = _request("GET", "/")
    assert resp.status_code == 200
    assert "Dress 2 Decor" in resp.text


def test_seeded_stats():
    resp = _request("GET", "/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_orders"] == 200
    assert data["total_vendors"] == 15
    assert data["total_products"] == 100
    assert data["total_revenue"] > 0


def test_order_lookup_api():
    resp = _request("GET", "/api/orders/ORD-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_number"] == "ORD-001"
    assert "items" in data
    assert "payment" in data

    missing = _request("GET", "/api/orders/ORD-9999")
    assert missing.status_code == 404


def test_order_agent_chat():
    resp = _request(
        "POST",
        "/api/chat",
        json={"message": "What is the status of order ORD-001?", "agent_type": "order"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "order_agent"
    assert len(data["tool_results"]) >= 1
    assert data["tool_results"][0]["tool"] == "get_order"
    assert data["tool_results"][0]["result"]["success"] is True


def test_vendor_agent_and_access_control():
    # Authorized lookup for own vendor_id=1
    resp = _request(
        "POST",
        "/api/chat",
        json={
            "message": "Show my vendor commission summary",
            "agent_type": "vendor",
            "vendor_id": 1,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "vendor_agent"
    assert len(data["tool_results"]) >= 1
    assert data["tool_results"][0]["tool"] == "get_vendor_commission"

    # Cross-vendor access attempt: vendor 1 trying to access vendor 2
    blocked = _request(
        "POST",
        "/api/chat",
        json={
            "message": "Show me details for vendor 2",
            "agent_type": "vendor",
            "vendor_id": 1,
        },
    )
    assert blocked.status_code == 200
    blocked_data = blocked.json()
    assert "Access denied" in blocked_data["response"]
    assert blocked_data["tool_results"] == []


def test_meeting_scheduling_api_and_agent():
    target_date = (date.today() + timedelta(days=3)).isoformat()
    # Check slots
    slots_resp = _request("GET", f"/api/meetings/slots?date={target_date}")
    assert slots_resp.status_code == 200
    assert "available_slots" in slots_resp.json()

    # Create meeting via API
    create_resp = _request(
        "POST",
        "/api/meetings",
        json={
            "title": "Interview Demo Sync",
            "description": "Testing meeting creation",
            "organizer": "Karib Shams",
            "attendees": "vendor@example.com",
            "meeting_date": target_date,
            "start_time": "11:00",
            "end_time": "12:00",
            "location": "Zoom",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["title"] == "Interview Demo Sync"

    # Schedule via Meeting Agent
    chat_resp = _request(
        "POST",
        "/api/chat",
        json={
            "message": "Schedule a meeting with vendor tomorrow at 10am",
            "agent_type": "meeting",
        },
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["agent"] == "meeting_agent"
    assert len(chat_data["tool_results"]) >= 1


def test_products_and_activities():
    prod_resp = _request("GET", "/api/products?category=curtains")
    assert prod_resp.status_code == 200
    assert prod_resp.json()["count"] >= 1

    act_resp = _request("GET", "/api/activities")
    assert act_resp.status_code == 200
    assert act_resp.json()["count"] >= 1


def test_webhook_endpoint():
    resp = _request(
        "POST",
        "/api/webhooks/automation",
        json={"event_type": "order.created", "payload": {"order_number": "ORD-001"}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"

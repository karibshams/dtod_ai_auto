"""Vendor Support AI Agent for Dress 2 Decor."""

import json
import re
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.agents.tools import VENDOR_TOOLS

VENDOR_SYSTEM_PROMPT = """You are the Vendor Support Agent for Dress 2 Decor, a home decor e-commerce marketplace.
Your responsibilities:
1. Answer vendor questions about their profile, product listings, orders, and commissions.
2. Explain marketplace rules:
   - Standard platform commission is 10%-20% (default 15%) deducted from completed sales.
   - Vendors must ship confirmed orders within 2 business days with valid tracking.
   - Payouts are processed bi-weekly for delivered orders.
3. Enforce strict data isolation: vendors may ONLY access their own vendor_id data.

Always be helpful, concise, and transparent."""


class VendorAgent(BaseAgent):
    """Handles vendor support queries with strict vendor-level access control."""

    def __init__(self):
        super().__init__(
            name="vendor_agent",
            system_prompt=VENDOR_SYSTEM_PROMPT,
            tools=VENDOR_TOOLS,
        )

    async def process(
        self,
        user_message: str,
        db: Session,
        context: dict | None = None,
    ) -> dict:
        """Enforce vendor_id presence & isolation before delegating to BaseAgent."""
        context = context or {}
        raw_vendor_id = context.get("vendor_id")

        try:
            scoped_vendor_id = int(raw_vendor_id) if raw_vendor_id is not None else 0
        except (TypeError, ValueError):
            scoped_vendor_id = 0

        if scoped_vendor_id <= 0:
            return {
                "response": "Please enter your Vendor ID (a positive number, e.g. 1) before asking Vendor Agent questions.",
                "tool_results": [],
                "agent": self.name,
            }

        # Check if the user is trying to access another vendor's ID
        mentioned_ids = re.findall(
            r"vendor\s*(?:id|#)?\s*(\d+)", user_message, re.IGNORECASE
        )
        for mid in mentioned_ids:
            if int(mid) != scoped_vendor_id:
                from app.services import activity_service

                msg = (
                    f"Access denied: As Vendor #{scoped_vendor_id}, you are only "
                    f"authorized to view your own vendor data (requested Vendor #{mid})."
                )
                activity_service.log_activity(
                    db=db,
                    agent=self.name,
                    action="access_denied",
                    details=json.dumps(
                        {"scoped_vendor_id": scoped_vendor_id, "requested_id": int(mid)}
                    ),
                    user_query=user_message,
                    success=False,
                )
                return {
                    "response": msg,
                    "tool_results": [],
                    "agent": self.name,
                }

        # Inject scoped vendor_id into prompt for real LLM providers
        augmented_message = (
            f"[Authenticated Vendor ID: {scoped_vendor_id}. "
            f"Only query data for vendor_id={scoped_vendor_id}.] {user_message}"
        )
        return await super().process(augmented_message, db, context)

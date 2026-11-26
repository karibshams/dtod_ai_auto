"""Intent-based router that dispatches messages to the right AI agent."""

import re


class AgentRouter:
    """Routes user messages to order, vendor, or meeting agents."""

    VALID_AGENTS = ("order", "vendor", "meeting")

    @classmethod
    def route(cls, message: str, agent_type: str | None = None) -> str:
        """Return 'order', 'vendor', or 'meeting'."""
        if agent_type and agent_type.lower() in cls.VALID_AGENTS:
            return agent_type.lower()

        msg = message.lower()

        if any(
            kw in msg
            for kw in (
                "meeting",
                "schedule",
                "calendar",
                "appointment",
                "slot",
                "book",
            )
        ):
            return "meeting"

        if any(
            kw in msg
            for kw in (
                "vendor",
                "commission",
                "payout",
                "marketplace rule",
                "my products",
                "my listings",
            )
        ):
            return "vendor"

        if re.search(r"ord-\d+", msg) or any(
            kw in msg
            for kw in (
                "order",
                "delivery",
                "tracking",
                "payment",
                "shipped",
                "product",
                "curtain",
                "rug",
                "blind",
            )
        ):
            return "order"

        return "order"

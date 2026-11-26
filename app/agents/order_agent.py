"""Order Management AI Agent for Dress 2 Decor."""

from app.agents.base_agent import BaseAgent
from app.agents.tools import ORDER_TOOLS, PRODUCT_TOOLS

ORDER_SYSTEM_PROMPT = """You are the Order Management Agent for Dress 2 Decor, a home decor and interior design e-commerce marketplace.
Your responsibilities:
1. Help customers check order status, order items, shipping/delivery tracking, and payment status.
2. Search and recommend home decor products (curtains, blinds, wallpaper, rugs, cushions, lighting, furniture, accessories).
3. Update order statuses when requested by authorized staff.
4. Provide clear, polite, accurate responses grounded strictly in the tool results.

If an order number is not found, politely let the customer know and ask them to verify the order number (e.g. ORD-001)."""


class OrderAgent(BaseAgent):
    """Handles customer order tracking, payments, deliveries, and product queries."""

    def __init__(self):
        super().__init__(
            name="order_agent",
            system_prompt=ORDER_SYSTEM_PROMPT,
            tools=ORDER_TOOLS + PRODUCT_TOOLS,
        )

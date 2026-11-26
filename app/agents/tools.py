"""Tool definitions (OpenAI function-calling format) and ToolExecutor."""

from sqlalchemy.orm import Session

# ── Order Tools ──────────────────────────────────────────────────

ORDER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up an order by order number",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "Order number like ORD-001",
                    }
                },
                "required": ["order_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders_by_email",
            "description": "Get all orders for a customer email",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Customer email address",
                    }
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders_by_status",
            "description": "Get orders filtered by status",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "confirmed",
                            "processing",
                            "shipped",
                            "delivered",
                            "cancelled",
                            "returned",
                        ],
                    }
                },
                "required": ["status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_order_status",
            "description": "Update the status of an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "Order number like ORD-001",
                    },
                    "new_status": {
                        "type": "string",
                        "description": "New status for the order",
                        "enum": [
                            "pending",
                            "confirmed",
                            "processing",
                            "shipped",
                            "delivered",
                            "cancelled",
                            "returned",
                        ],
                    },
                },
                "required": ["order_number", "new_status"],
            },
        },
    },
]

# ── Vendor Tools ─────────────────────────────────────────────────

VENDOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_vendor_info",
            "description": "Get vendor information by vendor ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "integer",
                        "description": "Vendor ID",
                    }
                },
                "required": ["vendor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_products",
            "description": "Get all products for a specific vendor",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "integer",
                        "description": "Vendor ID",
                    }
                },
                "required": ["vendor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_orders",
            "description": "Get all orders for a specific vendor",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "integer",
                        "description": "Vendor ID",
                    }
                },
                "required": ["vendor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_commission",
            "description": "Get commission summary for a specific vendor",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "integer",
                        "description": "Vendor ID",
                    }
                },
                "required": ["vendor_id"],
            },
        },
    },
]

# ── Meeting Tools ────────────────────────────────────────────────

MEETING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_available_slots",
            "description": "Check available meeting slots for a given date",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    }
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_meeting",
            "description": "Schedule a new meeting",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Meeting title",
                    },
                    "date": {
                        "type": "string",
                        "description": "Meeting date in YYYY-MM-DD format",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM format",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in HH:MM format",
                    },
                    "organizer": {
                        "type": "string",
                        "description": "Name of the organizer",
                    },
                    "attendees": {
                        "type": "string",
                        "description": "Comma-separated list of attendees",
                    },
                    "location": {
                        "type": "string",
                        "description": "Meeting location",
                    },
                    "description": {
                        "type": "string",
                        "description": "Meeting description",
                    },
                },
                "required": ["title", "date", "start_time", "end_time", "organizer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_meetings",
            "description": "Get a list of upcoming meetings",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of meetings to return",
                        "default": 10,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_meeting",
            "description": "Cancel a meeting by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "meeting_id": {
                        "type": "integer",
                        "description": "Meeting ID to cancel",
                    }
                },
                "required": ["meeting_id"],
            },
        },
    },
]

# ── Product Tools ────────────────────────────────────────────────

PRODUCT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for products by keyword and optional category",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword",
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category to filter by",
                        "enum": [
                            "curtains",
                            "blinds",
                            "wallpaper",
                            "rugs",
                            "cushions",
                            "lighting",
                            "furniture",
                            "accessories",
                        ],
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_info",
            "description": "Get detailed information about a product by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID",
                    }
                },
                "required": ["product_id"],
            },
        },
    },
]


# ── Tool Executor ────────────────────────────────────────────────

class ToolExecutor:
    """Maps tool names to service-layer function calls and executes them."""

    def execute(self, tool_name: str, arguments: dict, db: Session) -> dict:
        """Execute a tool by name with the given arguments against the database.

        Returns a dict with ``"success"`` and ``"data"`` / ``"error"`` keys.
        """
        try:
            handler = self._get_handler(tool_name)
            if handler is None:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
            result = handler(db=db, **arguments)
            return {"success": True, "data": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # -- private routing ------------------------------------------------

    @staticmethod
    def _get_handler(tool_name: str):
        """Return the service function matching *tool_name*, or None."""
        from app.services import order_service, vendor_service, meeting_service, product_service

        mapping = {
            # Order tools
            "get_order": order_service.get_order_by_number,
            "get_orders_by_email": order_service.get_orders_by_customer_email,
            "get_orders_by_status": order_service.get_orders_by_status,
            "update_order_status": order_service.update_order_status,

            # Vendor tools
            "get_vendor_info": vendor_service.get_vendor_by_id,
            "get_vendor_products": vendor_service.get_vendor_products,
            "get_vendor_orders": vendor_service.get_vendor_orders,
            "get_vendor_commission": vendor_service.get_vendor_commission_summary,

            # Meeting tools
            "check_available_slots": _adapt_available_slots,
            "schedule_meeting": _adapt_schedule_meeting,
            "get_upcoming_meetings": meeting_service.get_upcoming_meetings,
            "cancel_meeting": meeting_service.cancel_meeting,

            # Product tools
            "search_products": product_service.search_products,
            "get_product_info": product_service.get_product_by_id,
        }
        return mapping.get(tool_name)


# ── Adapter helpers (signature translation) ──────────────────────

def _adapt_available_slots(db: Session, date: str, **kwargs):
    """Convert ISO date string to a ``datetime.date`` for the service."""
    from datetime import date as _date
    from app.services import meeting_service

    parsed = _date.fromisoformat(date)
    return meeting_service.get_available_slots(db, parsed)


def _adapt_schedule_meeting(
    db: Session,
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    organizer: str,
    attendees: str = "",
    location: str = "",
    description: str = "",
    **kwargs,
):
    """Translate flat tool arguments into the service function call."""
    from datetime import date as _date
    from app.services import meeting_service

    parsed_date = _date.fromisoformat(date)
    return meeting_service.schedule_meeting(
        db=db,
        title=title,
        description=description,
        organizer=organizer,
        attendees=attendees,
        meeting_date=parsed_date,
        start_time=start_time,
        end_time=end_time,
        location=location,
    )

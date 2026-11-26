"""Base agent class that all specialised agents inherit from."""

import json
import logging
import re
from sqlalchemy.orm import Session

from app.agents.tools import ToolExecutor

logger = logging.getLogger(__name__)


class BaseAgent:
    """Provides the common process loop: prompt → AI → (tool calls) → response."""

    def __init__(self, name: str, system_prompt: str, tools: list[dict]):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self._tool_executor = ToolExecutor()

    # ── public API ───────────────────────────────────────────────

    async def process(
        self,
        user_message: str,
        db: Session,
        context: dict | None = None,
    ) -> dict:
        """Run one user turn through the agent.

        Returns ``{"response": str, "tool_results": list, "agent": str}``.
        """
        from datetime import date as _date
        from app.core.ai_provider import MockProvider, get_ai_provider
        from app.core.config import get_settings

        provider = get_ai_provider()
        tool_results: list[dict] = []
        settings = get_settings()
        context = context or {}
        effective_system_prompt = (
            f"{self.system_prompt}\n\n"
            f"Current date: {_date.today().isoformat()}. "
            f"Always call the required tools directly using exact tool names (without any 'tool_' prefix). "
            f"If a request needs multiple tools, call all of them."
        )

        try:
            # ── Mock-mode fast path ──────────────────────────────
            if settings.ai_provider == "mock":
                tool_results, response_text = await self._run_mock_turn(
                    user_message, db, context, provider
                )

            # ── Real-provider agent loop (max 4 iterations) ──────
            else:
                history = context.get("history") or []
                messages: list[dict] = [
                    *history[-10:],
                    {"role": "user", "content": user_message},
                ]
                response_text = ""
                max_iterations = 4

                for _ in range(max_iterations):
                    ai_result = await provider.generate(
                        system_prompt=effective_system_prompt,
                        user_message=user_message,
                        tools=self.tools,
                        messages=messages,
                    )

                    if ai_result.get("error"):
                        logger.warning(
                            "Provider %s failed (%s); falling back to mock mode.",
                            settings.ai_provider,
                            ai_result["error"],
                        )
                        tool_results, response_text = await self._run_mock_turn(
                            user_message, db, context, MockProvider()
                        )
                        break

                    response_text = ai_result.get("response", "")
                    tool_calls = ai_result.get("tool_calls")

                    if not tool_calls:
                        break

                    # Preserve assistant message with tool_calls in conversation
                    assistant_msg = ai_result.get("assistant_message") or {
                        "role": "assistant",
                        "content": response_text or None,
                        "tool_calls": [
                            {
                                "id": tc.get("id", f"call_{i}"),
                                "type": "function",
                                "function": {
                                    "name": tc.get("name", ""),
                                    "arguments": (
                                        tc["arguments"]
                                        if isinstance(tc.get("arguments"), str)
                                        else json.dumps(tc.get("arguments", {}))
                                    ),
                                },
                            }
                            for i, tc in enumerate(tool_calls)
                        ],
                    }
                    messages.append(assistant_msg)

                    # Execute ALL tool calls requested in this turn
                    for i, tc in enumerate(tool_calls):
                        tc_id = tc.get("id") or f"call_{i}"
                        name = tc.get("name", "")
                        args = tc.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        result = self._tool_executor.execute(name, args, db)
                        tool_results.append(
                            {"tool": name, "arguments": args, "result": result}
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "name": name,
                                "content": json.dumps(result, default=str),
                            }
                        )

        except Exception as exc:
            logger.exception("Agent %s failed", self.name)
            response_text = (
                f"I encountered an error while processing your request: {exc}"
            )

        # ── Log activity ─────────────────────────────────────────
        try:
            from app.services import activity_service

            tools_used = [tr["tool"] for tr in tool_results]
            action = ", ".join(tools_used) if tools_used else "chat"
            activity_service.log_activity(
                db=db,
                agent=self.name,
                action=action,
                details=json.dumps(tool_results, default=str) if tool_results else None,
                user_query=user_message,
                success=True,
            )
        except Exception:
            logger.warning("Failed to log activity for agent %s", self.name)

        return {
            "response": response_text,
            "tool_results": tool_results,
            "agent": self.name,
        }

    # ── Mock-mode helpers ────────────────────────────────────────

    async def _run_mock_turn(
        self,
        user_message: str,
        db: Session,
        context: dict | None,
        provider,
    ) -> tuple[list[dict], str]:
        tool_results = self._mock_tool_execution(user_message, db, context)
        ai_result = await provider.generate(
            system_prompt=self.system_prompt,
            user_message=user_message,
            tools=self.tools,
        )
        response_text = ai_result.get("response", "")
        if ai_result.get("tool_calls"):
            for tc in ai_result["tool_calls"]:
                name = tc.get("name", "")
                args = tc.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                result = self._tool_executor.execute(name, args, db)
                tool_results.append(
                    {"tool": name, "arguments": args, "result": result}
                )
        if tool_results:
            response_text = self._format_tool_response(response_text, tool_results)
        return tool_results, response_text

    def _mock_tool_execution(
        self, message: str, db: Session, context: dict | None
    ) -> list[dict]:
        """Detect intent via keywords and directly execute matching tools."""
        results: list[dict] = []
        msg_lower = message.lower()

        # --- Order-related intent ---
        order_match = re.search(r"ORD-\d+", message, re.IGNORECASE)
        if order_match:
            order_number = order_match.group(0).upper()
            # Check for status-update intent
            status_kw = re.search(
                r"\b(cancel|ship|deliver|confirm|process|return)\b",
                msg_lower,
            )
            if status_kw:
                status_map = {
                    "cancel": "cancelled",
                    "ship": "shipped",
                    "deliver": "delivered",
                    "confirm": "confirmed",
                    "process": "processing",
                    "return": "returned",
                }
                new_status = status_map.get(status_kw.group(1), "processing")
                result = self._tool_executor.execute(
                    "update_order_status",
                    {"order_number": order_number, "new_status": new_status},
                    db,
                )
                results.append(
                    {
                        "tool": "update_order_status",
                        "arguments": {
                            "order_number": order_number,
                            "new_status": new_status,
                        },
                        "result": result,
                    }
                )
            else:
                result = self._tool_executor.execute(
                    "get_order", {"order_number": order_number}, db
                )
                results.append(
                    {
                        "tool": "get_order",
                        "arguments": {"order_number": order_number},
                        "result": result,
                    }
                )
            return results

        # Email lookup
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", message)
        if email_match and any(
            kw in msg_lower for kw in ("order", "purchase", "bought")
        ):
            email = email_match.group(0)
            result = self._tool_executor.execute(
                "get_orders_by_email", {"email": email}, db
            )
            results.append(
                {
                    "tool": "get_orders_by_email",
                    "arguments": {"email": email},
                    "result": result,
                }
            )
            return results

        # Status filter
        for status in (
            "pending",
            "confirmed",
            "processing",
            "shipped",
            "delivered",
            "cancelled",
            "returned",
        ):
            if status in msg_lower and any(
                kw in msg_lower for kw in ("order", "status", "list", "show")
            ):
                result = self._tool_executor.execute(
                    "get_orders_by_status", {"status": status}, db
                )
                results.append(
                    {
                        "tool": "get_orders_by_status",
                        "arguments": {"status": status},
                        "result": result,
                    }
                )
                return results

        # --- Vendor-related intent ---
        vendor_id = None
        if context and context.get("vendor_id"):
            vendor_id = int(context["vendor_id"])
        else:
            vid_match = re.search(r"vendor\s*#?\s*(\d+)", msg_lower)
            if vid_match:
                vendor_id = int(vid_match.group(1))

        if vendor_id:
            if "commission" in msg_lower:
                result = self._tool_executor.execute(
                    "get_vendor_commission", {"vendor_id": vendor_id}, db
                )
                results.append(
                    {
                        "tool": "get_vendor_commission",
                        "arguments": {"vendor_id": vendor_id},
                        "result": result,
                    }
                )
            elif "product" in msg_lower:
                result = self._tool_executor.execute(
                    "get_vendor_products", {"vendor_id": vendor_id}, db
                )
                results.append(
                    {
                        "tool": "get_vendor_products",
                        "arguments": {"vendor_id": vendor_id},
                        "result": result,
                    }
                )
            elif "order" in msg_lower:
                result = self._tool_executor.execute(
                    "get_vendor_orders", {"vendor_id": vendor_id}, db
                )
                results.append(
                    {
                        "tool": "get_vendor_orders",
                        "arguments": {"vendor_id": vendor_id},
                        "result": result,
                    }
                )
            else:
                result = self._tool_executor.execute(
                    "get_vendor_info", {"vendor_id": vendor_id}, db
                )
                results.append(
                    {
                        "tool": "get_vendor_info",
                        "arguments": {"vendor_id": vendor_id},
                        "result": result,
                    }
                )
            return results

        # --- Meeting-related intent ---
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", message)
        if any(
            kw in msg_lower
            for kw in ("meeting", "schedule", "calendar", "appointment", "book")
        ):
            if "cancel" in msg_lower:
                mid_match = re.search(r"meeting\s*#?\s*(\d+)", msg_lower)
                if mid_match:
                    meeting_id = int(mid_match.group(1))
                    result = self._tool_executor.execute(
                        "cancel_meeting", {"meeting_id": meeting_id}, db
                    )
                    results.append(
                        {
                            "tool": "cancel_meeting",
                            "arguments": {"meeting_id": meeting_id},
                            "result": result,
                        }
                    )
                    return results

            if date_match and any(
                kw in msg_lower for kw in ("available", "slot", "free", "open")
            ):
                result = self._tool_executor.execute(
                    "check_available_slots", {"date": date_match.group(0)}, db
                )
                results.append(
                    {
                        "tool": "check_available_slots",
                        "arguments": {"date": date_match.group(0)},
                        "result": result,
                    }
                )
                return results

            if "upcoming" in msg_lower or "next" in msg_lower or "list" in msg_lower:
                result = self._tool_executor.execute(
                    "get_upcoming_meetings", {}, db
                )
                results.append(
                    {
                        "tool": "get_upcoming_meetings",
                        "arguments": {},
                        "result": result,
                    }
                )
                return results

        # --- Product-related intent ---
        if any(kw in msg_lower for kw in ("product", "search", "find", "item")):
            category = None
            for cat in (
                "curtains", "blinds", "wallpaper", "rugs",
                "cushions", "lighting", "furniture", "accessories",
            ):
                if cat in msg_lower:
                    category = cat
                    break
            query = message  # Use full message as search query
            args: dict = {"query": query}
            if category:
                args["category"] = category
            result = self._tool_executor.execute("search_products", args, db)
            results.append(
                {"tool": "search_products", "arguments": args, "result": result}
            )
            return results

        return results

    @staticmethod
    def _format_tool_response(base_response: str, tool_results: list[dict]) -> str:
        """Append a human-readable summary of tool results to the response."""
        parts = [base_response] if base_response else []
        for tr in tool_results:
            tool = tr["tool"]
            result = tr["result"]
            if result.get("success"):
                data = result["data"]
                if data is None:
                    parts.append(f"✅ **{tool}** executed successfully.")
                elif isinstance(data, list):
                    parts.append(f"📋 **{tool}** returned {len(data)} result(s).")
                    for item in data[:5]:
                        if isinstance(item, dict):
                            summary_parts = []
                            for k in ("order_number", "name", "title", "email", "id"):
                                if k in item:
                                    summary_parts.append(f"{k}: {item[k]}")
                            if summary_parts:
                                parts.append(f"  • {', '.join(summary_parts)}")
                    if len(data) > 5:
                        parts.append(f"  ... and {len(data) - 5} more")
                elif isinstance(data, dict):
                    parts.append(f"✅ **{tool}** result:")
                    for k, v in list(data.items())[:8]:
                        parts.append(f"  • **{k}**: {v}")
                else:
                    parts.append(f"✅ **{tool}**: {data}")
            else:
                parts.append(f"❌ **{tool}** failed: {result.get('error', 'unknown')}")
        return "\n\n".join(parts)

"""Provider-independent AI integration layer.

Supports Groq, Gemini, OpenAI, Ollama, and a fully-functional mock provider.
The active provider is selected via the AI_PROVIDER env var / settings.
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    """Base class every AI provider must implement."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        """Return {"response": str, "tool_calls": list[dict] | None}."""
        ...


# ---------------------------------------------------------------------------
# Mock provider — no API key needed
# ---------------------------------------------------------------------------

class MockProvider(AIProvider):
    """Returns intelligent canned responses based on keyword / regex matching."""

    # Regex helpers
    _ORDER_RE = re.compile(r"ORD-\d+", re.IGNORECASE)
    _VENDOR_ID_RE = re.compile(r"vendor\s*#?\s*(\d+)", re.IGNORECASE)
    _DATE_RE = re.compile(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",
        re.IGNORECASE,
    )

    # Keyword → intent mapping (checked in priority order)
    _ORDER_KEYWORDS = {"order", "ord-", "track", "status", "delivery", "payment"}
    _VENDOR_KEYWORDS = {"vendor", "commission", "product listing", "my products", "my orders"}
    _MEETING_KEYWORDS = {"meeting", "schedule", "calendar", "appointment", "book"}

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        msg_lower = user_message.lower()
        intent = self._detect_intent(msg_lower)
        tool_calls = self._build_tool_calls(intent, user_message, msg_lower)
        response_text = self._build_response(intent, user_message, msg_lower)
        return {"response": response_text, "tool_calls": tool_calls or None}

    # ----- intent detection ------------------------------------------------

    def _detect_intent(self, msg_lower: str) -> str:
        """Return 'order', 'vendor', 'meeting', or 'general'."""
        for kw in self._ORDER_KEYWORDS:
            if kw in msg_lower:
                return "order"
        for kw in self._VENDOR_KEYWORDS:
            if kw in msg_lower:
                return "vendor"
        for kw in self._MEETING_KEYWORDS:
            if kw in msg_lower:
                return "meeting"
        return "general"

    # ----- tool-call generation -------------------------------------------

    def _build_tool_calls(self, intent: str, raw: str, lower: str) -> list[dict]:
        calls: list[dict] = []

        if intent == "order":
            order_match = self._ORDER_RE.search(raw)
            if order_match:
                calls.append({
                    "name": "get_order",
                    "arguments": {"order_number": order_match.group().upper()},
                })
            elif any(k in lower for k in ("status", "track", "delivery")):
                calls.append({
                    "name": "get_orders_by_status",
                    "arguments": {"status": self._extract_status(lower)},
                })
            elif "payment" in lower:
                order_match2 = self._ORDER_RE.search(raw)
                calls.append({
                    "name": "get_order",
                    "arguments": {"order_number": order_match2.group().upper() if order_match2 else "ORD-001"},
                })
            else:
                calls.append({
                    "name": "get_recent_orders",
                    "arguments": {"limit": 10},
                })

        elif intent == "vendor":
            vendor_match = self._VENDOR_ID_RE.search(raw)
            if "commission" in lower:
                vid = int(vendor_match.group(1)) if vendor_match else 1
                calls.append({
                    "name": "get_vendor_commission_summary",
                    "arguments": {"vendor_id": vid},
                })
            elif any(k in lower for k in ("product listing", "my products")):
                vid = int(vendor_match.group(1)) if vendor_match else 1
                calls.append({
                    "name": "get_vendor_products",
                    "arguments": {"vendor_id": vid},
                })
            elif "my orders" in lower:
                vid = int(vendor_match.group(1)) if vendor_match else 1
                calls.append({
                    "name": "get_vendor_orders",
                    "arguments": {"vendor_id": vid},
                })
            else:
                if vendor_match:
                    calls.append({
                        "name": "get_vendor",
                        "arguments": {"vendor_id": int(vendor_match.group(1))},
                    })
                else:
                    calls.append({
                        "name": "get_all_vendors",
                        "arguments": {},
                    })

        elif intent == "meeting":
            date_match = self._DATE_RE.search(raw)
            extracted_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
            if any(k in lower for k in ("book", "schedule")):
                calls.append({
                    "name": "schedule_meeting",
                    "arguments": {
                        "title": "Meeting",
                        "date": extracted_date,
                    },
                })
            elif "available" in lower or "slot" in lower or "free" in lower:
                calls.append({
                    "name": "get_available_slots",
                    "arguments": {"date": extracted_date},
                })
            else:
                calls.append({
                    "name": "get_meetings",
                    "arguments": {"date": extracted_date},
                })

        return calls

    @staticmethod
    def _extract_status(lower: str) -> str:
        for s in ("pending", "processing", "shipped", "delivered", "cancelled", "refunded"):
            if s in lower:
                return s
        return "pending"

    # ----- canned responses ------------------------------------------------

    def _build_response(self, intent: str, raw: str, lower: str) -> str:
        if intent == "order":
            order_match = self._ORDER_RE.search(raw)
            if order_match:
                return (
                    f"I found the details for order **{order_match.group().upper()}**. "
                    "Let me pull up the full information including items, payment status, "
                    "and delivery tracking for you."
                )
            return (
                "I'll look up the order information for you. "
                "Let me retrieve the latest data from our system."
            )

        if intent == "vendor":
            if "commission" in lower:
                return (
                    "I'll pull up the commission summary including total sales, "
                    "commission rate, and earnings for this vendor."
                )
            if any(k in lower for k in ("product listing", "my products")):
                return (
                    "Let me fetch the product listings for this vendor, "
                    "including pricing, stock levels, and categories."
                )
            return "I'll retrieve the vendor information from our records."

        if intent == "meeting":
            if any(k in lower for k in ("book", "schedule")):
                return (
                    "I'll help you schedule that meeting. Let me check the available "
                    "slots and set it up for you."
                )
            if "available" in lower or "slot" in lower:
                return "Let me check the available time slots for that date."
            return "Here are the upcoming meetings I found on the calendar."

        # general fallback
        if any(k in lower for k in ("help", "hi", "hello", "hey")):
            return (
                "Hello! I'm your DtoD AI assistant. I can help you with:\n"
                "• **Order Management** — track orders, check statuses, view payments\n"
                "• **Vendor Portal** — view products, commissions, vendor details\n"
                "• **Meeting Scheduler** — book meetings, check availability\n\n"
                "How can I assist you today?"
            )

        if any(k in lower for k in ("thank", "thanks")):
            return "You're welcome! Let me know if you need anything else."

        return (
            "I'd be happy to help! Could you provide a bit more detail? "
            "I can assist with orders, vendor information, or meeting scheduling."
        )


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

class GroqProvider(AIProvider):
    """Groq Cloud API (OpenAI-compatible chat completions)."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        chat_messages = (
            [{"role": "system", "content": system_prompt}, *messages]
            if messages
            else [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        )
        payload: dict = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        if tools:
            payload["tools"] = self._format_tools(tools)
            payload["tool_choice"] = "auto"

        last_error = ""
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(self.API_URL, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                return self._parse_response(data)
            except httpx.HTTPStatusError as exc:
                last_error = f"HTTP {exc.response.status_code}: {exc.response.text}"
                logger.error("Groq API HTTP error (attempt %d): %s", attempt + 1, last_error)
                payload["temperature"] = 0.0
            except httpx.RequestError as exc:
                last_error = str(exc)
                logger.error("Groq API request error (attempt %d): %s", attempt + 1, last_error)
            except Exception as exc:
                last_error = str(exc)
                logger.error("Groq unexpected error (attempt %d): %s", attempt + 1, last_error)
                break

        return self._fallback_response(last_error)

    @staticmethod
    def _format_tools(tools: list[dict]) -> list[dict]:
        formatted = []
        for t in tools:
            if "type" in t and t["type"] == "function":
                formatted.append(t)
            else:
                formatted.append({
                    "type": "function",
                    "function": t if "name" in t else t.get("function", t),
                })
        return formatted

    @staticmethod
    def _parse_response(data: dict) -> dict:
        choice = data["choices"][0]
        message = choice["message"]
        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = []
            for idx, tc in enumerate(message["tool_calls"]):
                import json as _json
                args = tc["function"].get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = _json.loads(args)
                    except _json.JSONDecodeError:
                        args = {}
                tool_calls.append({
                    "id": tc.get("id") or f"call_{idx}",
                    "name": tc["function"]["name"],
                    "arguments": args,
                })
        return {
            "response": message.get("content") or "",
            "tool_calls": tool_calls,
            "assistant_message": message,
        }

    @staticmethod
    def _fallback_response(error: str) -> dict:
        return {
            "response": f"AI provider error: {error}",
            "tool_calls": None,
            "error": error,
        }


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(AIProvider):
    """Standard OpenAI chat completions with tool calling."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        if tools:
            payload["tools"] = GroqProvider._format_tools(tools)
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            return GroqProvider._parse_response(data)
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI API HTTP error %s: %s", exc.response.status_code, exc.response.text)
            return GroqProvider._fallback_response(str(exc))
        except httpx.RequestError as exc:
            logger.error("OpenAI API request error: %s", exc)
            return GroqProvider._fallback_response(str(exc))
        except Exception as exc:
            logger.error("OpenAI unexpected error: %s", exc)
            return GroqProvider._fallback_response(str(exc))


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider(AIProvider):
    """Google Gemini REST API."""

    API_URL_TEMPLATE = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        url = self.API_URL_TEMPLATE.format(model=self.model)
        params = {"key": self.api_key}
        payload: dict = {
            "contents": [
                {"role": "user", "parts": [{"text": user_message}]},
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            },
        }
        if tools:
            payload["tools"] = [{"functionDeclarations": self._convert_tools(tools)}]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, params=params, json=payload)
                resp.raise_for_status()
                data = resp.json()
            return self._parse_response(data)
        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API HTTP error %s: %s", exc.response.status_code, exc.response.text)
            return GroqProvider._fallback_response(str(exc))
        except httpx.RequestError as exc:
            logger.error("Gemini API request error: %s", exc)
            return GroqProvider._fallback_response(str(exc))
        except Exception as exc:
            logger.error("Gemini unexpected error: %s", exc)
            return GroqProvider._fallback_response(str(exc))

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[dict]:
        """Convert OpenAI-style tool schemas to Gemini functionDeclarations."""
        declarations: list[dict] = []
        for tool in tools:
            func = tool.get("function", tool)
            decl: dict = {
                "name": func["name"],
                "description": func.get("description", ""),
            }
            params = func.get("parameters")
            if params:
                decl["parameters"] = GeminiProvider._convert_schema(params)
            declarations.append(decl)
        return declarations

    @staticmethod
    def _convert_schema(schema: dict) -> dict:
        """Recursively convert JSON Schema to Gemini's Schema format."""
        result: dict = {}
        type_map = {
            "string": "STRING",
            "number": "NUMBER",
            "integer": "INTEGER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT",
        }
        if "type" in schema:
            result["type"] = type_map.get(schema["type"], schema["type"].upper())
        if "description" in schema:
            result["description"] = schema["description"]
        if "enum" in schema:
            result["enum"] = schema["enum"]
        if "properties" in schema:
            result["properties"] = {
                k: GeminiProvider._convert_schema(v)
                for k, v in schema["properties"].items()
            }
        if "required" in schema:
            result["required"] = schema["required"]
        if "items" in schema:
            result["items"] = GeminiProvider._convert_schema(schema["items"])
        return result

    @staticmethod
    def _parse_response(data: dict) -> dict:
        import json as _json

        candidates = data.get("candidates", [])
        if not candidates:
            return {"response": "", "tool_calls": None}

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts: list[str] = []
        tool_calls: list[dict] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "name": fc["name"],
                    "arguments": fc.get("args", {}),
                })

        return {
            "response": "\n".join(text_parts),
            "tool_calls": tool_calls if tool_calls else None,
        }


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------

class OllamaProvider(AIProvider):
    """Local Ollama instance."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        messages: list[dict] | None = None,
    ) -> dict:
        url = f"{self.base_url}/api/chat"
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        if tools:
            payload["tools"] = GroqProvider._format_tools(tools)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            return self._parse_response(data)
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama API HTTP error %s: %s", exc.response.status_code, exc.response.text)
            return GroqProvider._fallback_response(str(exc))
        except httpx.RequestError as exc:
            logger.error("Ollama API request error: %s", exc)
            return GroqProvider._fallback_response(str(exc))
        except Exception as exc:
            logger.error("Ollama unexpected error: %s", exc)
            return GroqProvider._fallback_response(str(exc))

    @staticmethod
    def _parse_response(data: dict) -> dict:
        import json as _json

        message = data.get("message", {})
        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = []
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = _json.loads(args)
                    except _json.JSONDecodeError:
                        args = {}
                tool_calls.append({
                    "name": func.get("name", ""),
                    "arguments": args,
                })

        return {
            "response": message.get("content") or "",
            "tool_calls": tool_calls,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_ai_provider() -> AIProvider:
    """Return the provider instance configured in settings."""
    settings = get_settings()
    provider_name = settings.ai_provider.lower().strip()

    if provider_name == "groq":
        if not settings.groq_api_key:
            logger.warning("GROQ_API_KEY not set — falling back to MockProvider")
            return MockProvider()
        return GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set — falling back to MockProvider")
            return MockProvider()
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)

    if provider_name == "openai":
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set — falling back to MockProvider")
            return MockProvider()
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)

    if provider_name == "ollama":
        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)

    # Default / "mock"
    if provider_name != "mock":
        logger.warning("Unknown AI_PROVIDER '%s' — using MockProvider", provider_name)
    return MockProvider()

"""LLM-powered decision engine — Gemini primary, Anthropic Claude preserved-but-inactive.

PRIMARY PROVIDER: Google Gemini (free tier via AI Studio API key)
  - Model: gemini-3.6-flash
  - SDK:   google-genai 2.20.0  (package: google-genai, import: google.genai)
  - Auth:  GEMINI_API_KEY environment variable (no billing account required)

INACTIVE / PRESERVED: Anthropic Claude
  - Kept intact below for future reactivation when credits are available.
  - Controlled by the ``primary`` constructor parameter (default: "gemini").
  - Switching back to Claude: pass primary="claude" and a valid anthropic_api_key.

SAFETY CONSTRAINTS (HARD-CODED, DO NOT REMOVE):
  - Never retries on Gemini quota-exceeded (HTTP 429 / RESOURCE_EXHAUSTED).
    Log and stop instead of burning through the 1,500 req/day limit.
  - Never calls any billing, subscription, or payment endpoint.
  - Only uses gemini-3.6-flash — no paid Vertex AI endpoints.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Gemini free-tier limits (sourced from ai.google.dev, Aug 2026) ─────────────
GEMINI_FREE_RPD = 1_500      # requests per day
GEMINI_FREE_RPM = 10         # requests per minute
# We enforce a conservative inter-request floor to stay well under RPM.
# 60s / 10 RPM = 6s minimum gap; we use 6.5s for safety margin.
_GEMINI_MIN_INTERVAL_SECONDS = 6.5

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert AI trading assistant. Your task is to analyze financial market data, "
    "evaluating technical indicators, market trends, portfolio context, and risk parameters "
    "to make reasoned trading decisions (e.g., BUY, SELL, HOLD). "
    "Focus strictly on risk management, market dynamics, and clear logical reasoning. "
    "Do not include any blockchain or cryptocurrency assumptions unless explicitly specified in market data."
)

# ── Gemini quota error detection ──────────────────────────────────────────────
# google-genai raises ClientError (subclass of APIError) for HTTP-level errors.
# Quota exhaustion is HTTP 429 / gRPC RESOURCE_EXHAUSTED.
# On quota error: log clearly and STOP — do NOT retry (safety constraint).
_GEMINI_QUOTA_STATUS = "RESOURCE_EXHAUSTED"
_GEMINI_QUOTA_HTTP_CODE = 429

# ── Anthropic quota error detection (kept for Claude path) ────────────────────
# Anthropic surfaces billing issues as HTTP 402 (APIStatusError).
# Rate-limit is HTTP 429 (RateLimitError).
_ANTHROPIC_FALLBACK_STATUS_CODES = {402, 429}


def _is_gemini_quota_error(exc: Exception) -> bool:
    """Return True if *exc* is a Gemini quota-exceeded error.

    Inspects both the HTTP status code and the gRPC status string so we catch
    quota errors from any transport layer.
    """
    try:
        from google.genai.errors import APIError  # noqa: PLC0415
        if isinstance(exc, APIError):
            if exc.code == _GEMINI_QUOTA_HTTP_CODE:
                return True
            if isinstance(exc.status, str) and _GEMINI_QUOTA_STATUS in exc.status:
                return True
    except ImportError:
        pass
    # Fallback: inspect the string representation for known quota markers
    exc_str = str(exc)
    return _GEMINI_QUOTA_STATUS in exc_str or "429" in exc_str


def _is_anthropic_quota_error(exc: Exception) -> bool:
    """Return True if *exc* is an Anthropic credit / quota / rate-limit error."""
    try:
        import anthropic  # noqa: PLC0415
        if isinstance(exc, anthropic.RateLimitError):
            return True
        if isinstance(exc, anthropic.APIStatusError):
            return exc.status_code in _ANTHROPIC_FALLBACK_STATUS_CODES
    except ImportError:
        pass
    return False


# ── MCP/Anthropic → Gemini tool schema adapter ───────────────────────────────
# MCP tool schemas are surfaced to this engine in Anthropic format:
#   {"name": str, "description": str, "input_schema": {"type": "object", ...}}
# Gemini FunctionDeclaration format:
#   types.FunctionDeclaration(name=str, description=str, parameters_json_schema={...})
# This adapter translates between the two WITHOUT touching mcp_client/.
def _mcp_tools_to_gemini(mcp_tools: List[Dict[str, Any]]) -> List[Any]:
    """Convert MCP/Anthropic-format tool definitions to Gemini FunctionDeclaration objects.

    Translates ``input_schema`` (Anthropic/MCP key) → ``parameters_json_schema``
    (Gemini key). All other schema content is passed through unchanged.

    Args:
        mcp_tools: List of tool dicts in Anthropic/MCP format.

    Returns:
        List of ``google.genai.types.FunctionDeclaration`` objects ready to pass
        to ``types.Tool(function_declarations=...)``.
    """
    try:
        from google.genai import types as genai_types  # noqa: PLC0415
    except ImportError:
        logger.error(
            "google-genai not installed. Run: pip install google-genai>=1.0.0"
        )
        return []

    declarations = []
    for tool in mcp_tools:
        name = tool.get("name", "")
        description = tool.get("description", "")
        # MCP/Anthropic wraps the JSON Schema under "input_schema";
        # Gemini takes it directly as "parameters_json_schema".
        input_schema: Dict[str, Any] = tool.get("input_schema", {})
        try:
            declarations.append(
                genai_types.FunctionDeclaration(
                    name=name,
                    description=description,
                    parameters_json_schema=input_schema,
                )
            )
        except Exception as e:
            logger.warning("Skipping tool '%s' — schema conversion error: %s", name, e)
    return declarations


class DecisionEngine:
    """LLM decision engine: Gemini primary (free tier), Claude preserved-but-inactive.

    Attributes:
        primary: Active provider — "gemini" (default) or "claude".
        gemini_model: Gemini model ID. Default: "gemini-3.6-flash" (free tier).
        system_prompt: System prompt injected into every LLM request.
    """

    #: The only model used on the Gemini path — verified free tier
    GEMINI_MODEL = "gemini-3.6-flash"

    def __init__(
        self,
        # Gemini (primary, free tier)
        gemini_api_key: str,
        gemini_model: str = GEMINI_MODEL,
        # Anthropic (preserved, inactive by default)
        anthropic_api_key: Optional[str] = None,
        claude_model: str = "claude-sonnet-4-20250514",
        # Provider selection
        primary: str = "gemini",
        system_prompt: Optional[str] = None,
    ) -> None:
        """Initialise the decision engine.

        Args:
            gemini_api_key: Google AI Studio API key (no billing account required).
                Obtained from https://aistudio.google.com/app/apikey — free.
            gemini_model: Gemini model ID. Defaults to ``"gemini-3.6-flash"``.
                DO NOT change to a Vertex AI endpoint without explicit user approval.
            anthropic_api_key: Anthropic API key — optional, only needed when
                ``primary="claude"``. Kept here for future reactivation.
            claude_model: Anthropic model ID (inactive unless primary="claude").
            primary: Active provider. "gemini" (default) or "claude".
            system_prompt: Custom system prompt.
        """
        if gemini_model != self.GEMINI_MODEL:
            logger.warning(
                "Non-default Gemini model '%s' requested. Verify this model is on "
                "the free tier at ai.google.dev before use. Default free-tier model "
                "is '%s'.",
                gemini_model,
                self.GEMINI_MODEL,
            )

        self.primary = primary
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        # Gemini client (lazy-initialised on first use)
        self._gemini_client: Optional[Any] = None
        # Timestamp of last successful Gemini call (for inter-request pacing)
        self._last_gemini_call_at: float = 0.0

        # ── Anthropic (preserved but inactive) ──────────────────────────────
        # This block stays here so switching back to Claude requires only
        # passing primary="claude" and a valid anthropic_api_key.
        self._anthropic_client: Optional[Any] = None
        self._claude_model = claude_model
        if primary == "claude":
            if not anthropic_api_key:
                raise ValueError(
                    "anthropic_api_key is required when primary='claude'. "
                    "Current balance is $0 — use primary='gemini' instead."
                )
            try:
                import anthropic  # noqa: PLC0415
                self._anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
                logger.info("Claude primary provider active (model: %s).", claude_model)
            except ImportError:
                logger.error("anthropic package not installed. Run: pip install anthropic>=0.40.0")
        # ────────────────────────────────────────────────────────────────────

        if primary == "gemini":
            logger.info(
                "Gemini primary provider active (model: %s, free tier, 1,500 req/day).",
                gemini_model,
            )

    # ── Gemini client (lazy init) ─────────────────────────────────────────────

    def _get_gemini_client(self) -> Optional[Any]:
        """Return a cached Gemini client, initialising on first call."""
        if self._gemini_client is not None:
            return self._gemini_client

        if not self.gemini_api_key:
            logger.error("GEMINI_API_KEY not set — cannot initialise Gemini client.")
            return None

        try:
            from google import genai  # noqa: PLC0415
            self._gemini_client = genai.Client(api_key=self.gemini_api_key)
            return self._gemini_client
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
            return None

    # ── Free-tier rate-limit pacing ───────────────────────────────────────────

    async def _gemini_rate_limit_wait(self) -> None:
        """Sleep if needed to respect the 10 RPM free-tier rate limit.

        Enforces a minimum gap of 6.5 seconds between consecutive Gemini calls.
        This keeps us under 10 req/minute without aggressive throttling.
        SAFETY: on quota-exceeded error we stop entirely — we do NOT retry here.
        """
        import time  # noqa: PLC0415
        elapsed = time.monotonic() - self._last_gemini_call_at
        if elapsed < _GEMINI_MIN_INTERVAL_SECONDS:
            wait = _GEMINI_MIN_INTERVAL_SECONDS - elapsed
            logger.debug("Gemini rate-limit pacing: sleeping %.2fs", wait)
            await asyncio.sleep(wait)

    def _gemini_record_call(self) -> None:
        """Record that a Gemini API call is about to be made."""
        import time  # noqa: PLC0415
        self._last_gemini_call_at = time.monotonic()

    # ── Gemini: analyze_market ────────────────────────────────────────────────

    async def _analyze_market_gemini(self, prompt: str) -> Dict[str, Any]:
        """Send a market-analysis prompt to Gemini and return a parsed decision dict."""
        gemini_client = self._get_gemini_client()
        if gemini_client is None:
            return _error_decision("Gemini client not initialised (check GEMINI_API_KEY).", provider="gemini")

        try:
            from google.genai import types as genai_types  # noqa: PLC0415

            full_prompt = f"{self.system_prompt}\n\n{prompt}\nCRITICAL: OUTPUT MUST BE A SINGLE VALID JSON OBJECT ONLY. NO MARKDOWN, NO CODE BLOCKS, NO EXPLANATORY TEXT."
            
            for attempt in range(2):
                await self._gemini_rate_limit_wait()
                self._gemini_record_call()
                
                response = await gemini_client.aio.models.generate_content(
                    model=self.gemini_model,
                    contents=full_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=2048,
                        response_mime_type="application/json",
                    ),
                )

                raw_text: str = response.text or ""
                decision = _parse_json_decision(raw_text)
                
                if decision.get("action") == "hold" and "JSON parse error" in decision.get("reasoning", ""):
                    if attempt == 0:
                        logger.warning("Gemini returned malformed JSON, retrying once. raw: %s", raw_text[:200])
                        full_prompt += "\nYOUR PREVIOUS RESPONSE WAS INVALID JSON. PLEASE FIX THE FORMATTING AND RETURN ONLY VALID JSON."
                        continue
                    else:
                        decision["reasoning"] = f"Gemini returned malformed JSON, could not parse decision — raw response logged. Error: {decision['reasoning']}"
                        decision["provider"] = "gemini"
                        return decision
                
                logger.info("Gemini analyze_market: success (provider=gemini).")
                decision["provider"] = "gemini"
                return decision

        except Exception as err:
            if _is_gemini_quota_error(err):
                logger.error(
                    "GEMINI QUOTA EXCEEDED — stopping. Error: %s\n", err
                )
                return _error_decision(
                    f"Gemini quota exceeded (free tier: {GEMINI_FREE_RPD} req/day).",
                    provider="gemini",
                    quota_exceeded=True,
                )
            logger.error("Gemini API error in analyze_market: %s", err)
            return _error_decision(f"Gemini API error: {err}", provider="gemini")

    # ── Gemini: chat ──────────────────────────────────────────────────────────

    async def _chat_gemini(
        self,
        user_message: str,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Gemini chat interface with optional MCP tool-calling loop.

        MCP tool schemas (Anthropic format) are automatically adapted to
        Gemini FunctionDeclaration format via _mcp_tools_to_gemini().
        The MCP client itself is not touched.

        Args:
            user_message: User query / agent prompt.
            available_tools: Optional list of MCP tool schemas in Anthropic format.

        Returns:
            Tuple of (response_text, list_of_tool_calls_made).
        """
        gemini_client = self._get_gemini_client()
        if gemini_client is None:
            return "Gemini client not initialised (check GEMINI_API_KEY).", []

        await self._gemini_rate_limit_wait()

        try:
            from google.genai import types as genai_types  # noqa: PLC0415

            full_prompt = f"{self.system_prompt}\n\n{user_message}"
            tool_calls_made: List[Dict[str, Any]] = []
            max_iterations = 5

            # Build config — adapt MCP/Anthropic tool schemas to Gemini format
            config_kwargs: Dict[str, Any] = {
                "temperature": 0.2,
                "max_output_tokens": 2048,
            }
            if available_tools:
                gemini_tool_decls = _mcp_tools_to_gemini(available_tools)
                if gemini_tool_decls:
                    config_kwargs["tools"] = [
                        genai_types.Tool(function_declarations=gemini_tool_decls)
                    ]
                    # Disable automatic execution: we drive the tool loop ourselves
                    # so we can log every call and inject real MCP results later.
                    config_kwargs["automatic_function_calling"] = (
                        genai_types.AutomaticFunctionCallingConfig(disable=True)
                    )

            contents: Any = full_prompt  # grows on each tool-result turn

            for iteration in range(max_iterations):
                # Enforce rate-limit pacing on each iteration (each = one API call)
                if iteration > 0:
                    await self._gemini_rate_limit_wait()

                self._gemini_record_call()
                response = await gemini_client.aio.models.generate_content(
                    model=self.gemini_model,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(**config_kwargs),
                )

                function_calls = response.function_calls
                if function_calls:
                    tool_parts = []
                    for fc in function_calls:
                        tool_record = {
                            "id": f"gemini_{iteration}_{fc.name}",
                            "name": fc.name,
                            "input": dict(fc.args) if fc.args else {},
                        }
                        tool_calls_made.append(tool_record)
                        logger.info(
                            "Gemini tool call: '%s' args=%s (iter %d)",
                            fc.name,
                            tool_record["input"],
                            iteration,
                        )
                        # Return a simulated success result for each call.
                        # Real MCP execution happens in mcp_client/ — this stub
                        # is intentional: the tool call record is what gets logged
                        # and forwarded to the real MCP dispatcher upstream.
                        tool_result = {
                            "status": "success",
                            "message": f"Tool '{fc.name}' executed",
                            "input": tool_record["input"],
                        }
                        tool_parts.append(
                            genai_types.Part.from_function_response(
                                name=fc.name,
                                response=tool_result,
                            )
                        )
                    contents = [genai_types.Content(parts=tool_parts, role="tool")]
                else:
                    # No tool calls — terminal text response
                    text = response.text or ""
                    logger.info(
                        "Gemini chat: completed in %d iteration(s).", iteration + 1
                    )
                    return text, tool_calls_made

            # Max iterations reached
            final_text = response.text or "Reached maximum tool-call iterations."
            return final_text, tool_calls_made

        except Exception as err:
            if _is_gemini_quota_error(err):
                logger.error(
                    "GEMINI QUOTA EXCEEDED in chat — stopping. Error: %s\n"
                    "Free tier: %d req/day. Do NOT retry automatically.",
                    err,
                    GEMINI_FREE_RPD,
                )
                return (
                    f"Gemini quota exceeded (free tier: {GEMINI_FREE_RPD} req/day). "
                    "Stopping. Wait for quota reset at midnight PT.",
                    tool_calls_made if "tool_calls_made" in dir() else [],
                )
            logger.error("Gemini API error in chat: %s", err)
            return f"Gemini API error: {err}", []

    # ── Claude path (PRESERVED, INACTIVE) ────────────────────────────────────
    # The following two methods are kept intact so switching back to Claude
    # requires only passing primary="claude" and a valid anthropic_api_key.
    # They are NOT called when primary="gemini" (the current default).

    async def _analyze_market_claude(self, prompt: str) -> Dict[str, Any]:  # noqa: E501
        """[PRESERVED, INACTIVE] Analyze market via Anthropic Claude."""
        if self._anthropic_client is None:
            return _error_decision("Claude client not initialised (Anthropic balance: $0).")
        raw_text = ""
        try:
            response = await self._anthropic_client.messages.create(
                model=self._claude_model,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.2,
            )
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    raw_text += block.text
            decision = _parse_json_decision(raw_text)
            decision["provider"] = "claude"
            return decision
        except json.JSONDecodeError as e:
            logger.error("Claude: JSON parse error: %s", e)
            return _error_decision(f"Claude JSON parse error: {e}", provider="claude")
        except Exception as err:
            logger.error("Claude API error: %s", err)
            return _error_decision(f"Claude API error: {err}", provider="claude")

    async def _chat_claude(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """[PRESERVED, INACTIVE] Chat via Anthropic Claude with tool-calling loop."""
        if self._anthropic_client is None:
            return "Claude client not initialised (Anthropic balance: $0).", []
        messages: List[Dict[str, Any]] = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})
        tool_calls_made: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {
            "model": self._claude_model,
            "system": self.system_prompt,
            "messages": messages,
            "max_tokens": 2048,
        }
        if available_tools:
            kwargs["tools"] = available_tools
        assistant_content: Any = []
        for iteration in range(5):
            try:
                response = await self._anthropic_client.messages.create(**kwargs)
            except Exception as err:
                logger.error("Claude chat error (iter %d): %s", iteration, err)
                return f"Claude error: {err}", tool_calls_made
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})
            has_tool_use = False
            tool_results = []
            for block in assistant_content:
                if getattr(block, "type", None) == "tool_use":
                    has_tool_use = True
                    tool_calls_made.append({"id": block.id, "name": block.name, "input": block.input})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"status": "success", "input": block.input}),
                    })
            if has_tool_use:
                messages.append({"role": "user", "content": tool_results})
                kwargs["messages"] = messages
            else:
                final_text = "".join(b.text for b in assistant_content if getattr(b, "type", None) == "text")
                return final_text, tool_calls_made
        last_text = "".join(b.text for b in assistant_content if getattr(b, "type", None) == "text")
        return last_text or "Max iterations.", tool_calls_made

    # ── Public API ────────────────────────────────────────────────────────────

    async def analyze_market(
        self, market_data: Dict[str, Any], strategy_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze market data and strategy context to make a trading decision.

        Routes to Gemini (default) or Claude based on ``self.primary``.

        Args:
            market_data: Market prices, volumes, technical indicators.
            strategy_context: Risk parameters, current positions, strategy rules.

        Returns:
            Dict with keys:
                - action: "buy" | "sell" | "hold"
                - confidence: float 0.0–1.0
                - reasoning: explanation string
                - parameters: {symbol, qty, order_type, limit_price}
                - provider: "gemini" | "claude" | "none"
                - quota_exceeded: bool (True only on Gemini quota error — stops caller)
        """
        prompt = (
            "Analyze the following market data and strategy context to determine a trading action.\n\n"
            f"Market Data:\n{json.dumps(market_data, indent=2, default=str)}\n\n"
            f"Strategy Context:\n{json.dumps(strategy_context, indent=2, default=str)}\n\n"
            "Respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "action": "buy" | "sell" | "hold",\n'
            '  "confidence": <float 0.0 to 1.0>,\n'
            '  "reasoning": "<explanation>",\n'
            '  "parameters": {\n'
            '    "symbol": "<ticker>",\n'
            '    "qty": <number>,\n'
            '    "order_type": "market" | "limit",\n'
            '    "limit_price": <optional float>\n'
            "  }\n"
            "}\n"
            "Do not include markdown formatting or backticks."
        )

        if self.primary == "gemini":
            result = await self._analyze_market_gemini(prompt)
            result.setdefault("provider", "gemini")
            return result
        elif self.primary == "claude":
            result = await self._analyze_market_claude(prompt)
            result.setdefault("provider", "claude")
            return result
        else:
            logger.error("Unknown primary provider: %s", self.primary)
            return _error_decision(f"Unknown provider: {self.primary}")

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Chat interface with optional MCP tool-calling loop.

        Tool schemas must be in Anthropic/MCP format; adaptation to Gemini
        format happens transparently inside _chat_gemini() without touching
        mcp_client/.

        Args:
            user_message: User query or agent prompt.
            conversation_history: Prior messages (Anthropic format; used by
                Claude path only — Gemini path starts fresh to keep it simple).
            available_tools: MCP tool schema list in Anthropic format.

        Returns:
            Tuple of (response_text, list_of_tool_calls_made).
        """
        if self.primary == "gemini":
            return await self._chat_gemini(user_message, available_tools)
        elif self.primary == "claude":
            return await self._chat_claude(user_message, conversation_history, available_tools)
        else:
            return f"Unknown provider: {self.primary}", []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json_decision(raw_text: str) -> Dict[str, Any]:
    """Strip markdown fences and parse a JSON decision from LLM output."""
    cleaned = raw_text.strip()
    for prefix in ("```json", "```"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("JSON parse error in LLM response: %s | raw: %s", e, raw_text[:200])
        return _error_decision(f"JSON parse error: {e}")


def _error_decision(
    reason: str,
    provider: str = "none",
    quota_exceeded: bool = False,
) -> Dict[str, Any]:
    """Return a safe HOLD decision with an error reason."""
    return {
        "action": "hold",
        "confidence": 0.0,
        "reasoning": reason,
        "parameters": {},
        "provider": provider,
        "quota_exceeded": quota_exceeded,
    }


__all__ = ["DecisionEngine"]

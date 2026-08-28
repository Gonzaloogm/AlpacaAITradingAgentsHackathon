"""Claude-powered decision engine using Anthropic's tool-calling API for Alpaca trading agents."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert AI trading assistant. Your task is to analyze financial market data, "
    "evaluating technical indicators, market trends, portfolio context, and risk parameters "
    "to make reasoned trading decisions (e.g., BUY, SELL, HOLD). "
    "Focus strictly on risk management, market dynamics, and clear logical reasoning. "
    "Do not include any blockchain or cryptocurrency assumptions unless explicitly specified in market data."
)


class DecisionEngine:
    """Decision engine using Anthropic Claude to analyze market data and execute tool calls."""

    def __init__(
        self,
        anthropic_api_key: str,
        model: str = "claude-sonnet-4-20250514",
        system_prompt: Optional[str] = None,
    ) -> None:
        """Initialize DecisionEngine with Anthropic API key and model selection.

        Args:
            anthropic_api_key: Anthropic API key.
            model: Anthropic model identifier. Defaults to 'claude-sonnet-4-20250514'.
            system_prompt: Custom system prompt to guide LLM behavior.
        """
        self.client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    async def analyze_market(
        self, market_data: Dict[str, Any], strategy_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze market data and strategy context to make a trading decision.

        Sends market data and strategy context to Claude and expects a JSON response
        containing the trade decision and rationale.

        Args:
            market_data: Dictionary containing market prices, volumes, and technical indicators.
            strategy_context: Dictionary containing risk parameters, current positions, and rules.

        Returns:
            Dictionary containing:
                - action: "buy" | "sell" | "hold"
                - confidence: float between 0.0 and 1.0
                - reasoning: explanation of the decision
                - parameters: order parameters dict (symbol, qty, order_type, limit_price)
        """
        prompt = (
            "Analyze the following market data and strategy context to determine a trading action.\n\n"
            f"Market Data:\n{json.dumps(market_data, indent=2, default=str)}\n\n"
            f"Strategy Context:\n{json.dumps(strategy_context, indent=2, default=str)}\n\n"
            "Respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "action": "buy" | "sell" | "hold",\n'
            '  "confidence": <float 0.0 to 1.0>,\n'
            '  "reasoning": "<explanation text>",\n'
            '  "parameters": {\n'
            '    "symbol": "<ticker>",\n'
            '    "qty": <number>,\n'
            '    "order_type": "market" | "limit",\n'
            '    "limit_price": <optional float>\n'
            "  }\n"
            "}\n"
            "Do not include markdown formatting or backticks around the JSON output."
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.2,
            )

            raw_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    raw_text += block.text

            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            decision = json.loads(cleaned_text)
            return decision

        except json.JSONDecodeError as parse_err:
            logger.error("Failed to parse JSON decision from LLM output: %s", raw_text)
            return {
                "action": "hold",
                "confidence": 0.0,
                "reasoning": f"Failed to parse LLM response JSON: {parse_err}",
                "parameters": {},
            }
        except Exception as err:
            logger.error("Error calling Anthropic API in analyze_market: %s", err)
            return {
                "action": "hold",
                "confidence": 0.0,
                "reasoning": f"API error: {err}",
                "parameters": {},
            }

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """General chat interface supporting native Anthropic tool-calling loop.

        Executes up to 5 iterations to allow multi-step tool calls before returning.

        Args:
            user_message: User query or prompt.
            conversation_history: Optional list of past conversation message objects.
            available_tools: Optional list of tool schema dictionaries.

        Returns:
            Tuple of (response_text, list_of_tool_calls_made).
        """
        messages: List[Dict[str, Any]] = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        tool_calls_made: List[Dict[str, Any]] = []
        max_iterations = 5

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "system": self.system_prompt,
            "messages": messages,
            "max_tokens": 2048,
        }
        if available_tools:
            kwargs["tools"] = available_tools

        for iteration in range(max_iterations):
            try:
                response = await self.client.messages.create(**kwargs)
            except Exception as err:
                logger.error("Anthropic API chat error on iteration %d: %s", iteration, err)
                return f"Error communicating with AI model: {err}", tool_calls_made

            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            has_tool_use = False
            tool_results = []

            for block in assistant_content:
                if getattr(block, "type", None) == "tool_use":
                    has_tool_use = True
                    tool_record = {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                    tool_calls_made.append(tool_record)
                    logger.info("Executing tool call: %s (ID: %s)", block.name, block.id)

                    tool_output = {
                        "status": "success",
                        "message": f"Executed tool '{block.name}' successfully",
                        "input": block.input,
                    }
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_output),
                    })

            if has_tool_use and tool_results:
                messages.append({"role": "user", "content": tool_results})
                kwargs["messages"] = messages
            else:
                final_text = "".join(
                    [b.text for b in assistant_content if getattr(b, "type", None) == "text"]
                )
                return final_text, tool_calls_made

        last_text = "".join(
            [b.text for b in assistant_content if getattr(b, "type", None) == "text"]
        )
        return last_text or "Reached maximum tool execution iterations.", tool_calls_made


__all__ = ["DecisionEngine"]

"""Provider-agnostic LLM client and agent loop.

Supports Anthropic and OpenAI. Each provider adapter is ~20 lines.
The agent loop is identical regardless of provider.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from .fhir import tools_for_anthropic


DEFAULT_SYSTEM_PROMPT = """You are a clinical data assistant working against a FHIR server with synthetic patient data.

When answering diabetes classification questions:
- gather enough evidence before concluding
- prefer direct evidence over heuristics
- use C-peptide when available to distinguish likely Type 1 from likely Type 2 diabetes
- use medication pattern, BMI, age, and diagnosis history as supporting context
- if evidence is missing or conflicting, say the case is unclear rather than forcing a binary answer
- cite concrete evidence from the tool results in your final answer
"""


# ---------------------------------------------------------------------------
# Normalized response container
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Provider-agnostic wrapper around an LLM API response."""
    text: str
    tool_calls: list[dict[str, Any]]
    model: str
    raw: Any


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------

class _AnthropicAdapter:
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def create_message(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools_for_anthropic(tools)
        resp = self._client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })
        return LLMResponse(
            text="".join(text_parts).strip(),
            tool_calls=tool_calls,
            model=resp.model,
            raw=resp,
        )

    def serialize_assistant(self, response: LLMResponse) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = []
        for block in response.raw.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return content

    def format_tool_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "tool_result",
                "tool_use_id": r["call_id"],
                "content": r["output"],
            }
            for r in results
        ]


class _OpenAIAdapter:
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def create_message(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        oai_messages: list[dict[str, Any]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": oai_messages,
        }
        if tools:
            kwargs["tools"] = [
                {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
                for t in tools
            ]
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        text = choice.message.content or ""
        tool_calls: list[dict[str, Any]] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        return LLMResponse(
            text=text.strip(),
            tool_calls=tool_calls,
            model=resp.model,
            raw=resp,
        )

    def serialize_assistant(self, response: LLMResponse) -> list[dict[str, Any]]:
        choice = response.raw.choices[0]
        msg: dict[str, Any] = {"role": "assistant"}
        if choice.message.content:
            msg["content"] = choice.message.content
        if choice.message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
        return msg  # type: ignore[return-value]

    def format_tool_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "role": "tool",
                "tool_call_id": r["call_id"],
                "content": r["output"],
            }
            for r in results
        ]


# ---------------------------------------------------------------------------
# Public LLMClient
# ---------------------------------------------------------------------------

@dataclass
class LLMClient:
    provider: str
    api_key: str
    model: str
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        if self.provider == "anthropic":
            self._adapter = _AnthropicAdapter(self.api_key, self.model, self.max_tokens)
        elif self.provider == "openai":
            self._adapter = _OpenAIAdapter(self.api_key, self.model, self.max_tokens)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def create_message(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        return self._adapter.create_message(
            messages=messages, system=system, tools=tools, max_tokens=max_tokens,
        )

    def create_text_response(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 300,
    ) -> str:
        resp = self.create_message(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            max_tokens=max_tokens,
        )
        return resp.text


# ---------------------------------------------------------------------------
# Backward compat alias
# ---------------------------------------------------------------------------

ClaudeClient = LLMClient  # capstone.py imports this name


# ---------------------------------------------------------------------------
# Agent loop (provider-agnostic)
# ---------------------------------------------------------------------------

def suggest_next_step(
    client: LLMClient,
    *,
    state: dict[str, Any],
    system: str | None = None,
) -> str:
    prompt = (
        "You are coaching a student who is pretending to be the clinical agent. "
        "Recommend exactly one next action from this list: "
        "Get demographics, Get full problem list, Get labs, Get medications, "
        "Get encounters, Finish and answer. "
        "If the evidence is already sufficient, recommend Finish and answer. "
        "Be concise and explain why.\n\n"
        f"{json.dumps(state, indent=2)}"
    )
    return client.create_text_response(
        prompt=prompt,
        system=system or DEFAULT_SYSTEM_PROMPT,
        max_tokens=250,
    )


def run_agent(
    *,
    client: LLMClient,
    tools: list[dict[str, Any]],
    tool_runner,
    question: str,
    system: str = DEFAULT_SYSTEM_PROMPT,
    max_steps: int = 8,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Run a provider-agnostic tool-use agent loop."""
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": question},
    ]
    tool_calls_log: list[dict[str, Any]] = []
    response: LLMResponse | None = None

    for step in range(1, max_steps + 1):
        response = client.create_message(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
        )

        if not response.tool_calls:
            return {
                "answer": response.text,
                "tool_calls": tool_calls_log,
                "messages": messages,
                "model": response.model,
                "completed": True,
            }

        # Add assistant turn to history
        serialized = client._adapter.serialize_assistant(response)
        if isinstance(serialized, dict):
            # OpenAI: single message dict
            messages.append(serialized)
        else:
            # Anthropic: list of content blocks
            messages.append({"role": "assistant", "content": serialized})

        # Execute tools and collect results
        raw_results: list[dict[str, Any]] = []
        for call in response.tool_calls:
            try:
                result = tool_runner(call["name"], call["arguments"])
            except Exception as e:
                result = {"error": str(e)}

            tool_calls_log.append({
                "step": step,
                "tool": call["name"],
                "arguments": call["arguments"],
                "result_preview": str(result)[:300],
            })
            raw_results.append({
                "call_id": call["id"],
                "output": json.dumps(result, default=str),
            })

        # Format tool results for provider and add to history
        formatted = client._adapter.format_tool_results(raw_results)
        if isinstance(formatted[0], dict) and formatted[0].get("role") == "tool":
            # OpenAI: each tool result is a separate message
            messages.extend(formatted)
        else:
            # Anthropic: all tool results in one user message
            messages.append({"role": "user", "content": formatted})

    return {
        "answer": response.text if response else "",
        "tool_calls": tool_calls_log,
        "messages": messages,
        "model": response.model if response else "",
        "completed": False,
        "stop_reason": f"max_steps_exceeded:{max_steps}",
    }

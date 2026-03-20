"""Anthropic Claude Messages API helpers and a Claude-backed agent loop."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import anthropic


DEFAULT_SYSTEM_PROMPT = """You are a clinical data assistant working against a FHIR server with synthetic patient data.

When answering diabetes classification questions:
- gather enough evidence before concluding
- prefer direct evidence over heuristics
- use C-peptide when available to distinguish likely Type 1 from likely Type 2 diabetes
- use medication pattern, BMI, age, and diagnosis history as supporting context
- if evidence is missing or conflicting, say the case is unclear rather than forcing a binary answer
- cite concrete evidence from the tool results in your final answer
"""


@dataclass
class ClaudeClient:
    api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def create_message(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> anthropic.types.Message:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        return self._client.messages.create(**kwargs)

    def create_text_response(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 300,
    ) -> str:
        response = self.create_message(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            max_tokens=max_tokens,
        )
        return extract_text(response)


def extract_text(response: anthropic.types.Message) -> str:
    """Extract text content from a Claude response."""
    chunks: list[str] = []
    for block in response.content:
        if hasattr(block, "text"):
            chunks.append(block.text)
    return "".join(chunks).strip()


def extract_tool_use_blocks(response: anthropic.types.Message) -> list[Any]:
    """Extract tool_use blocks from a Claude response."""
    return [block for block in response.content if block.type == "tool_use"]


def suggest_next_step(
    client: ClaudeClient,
    *,
    state: dict[str, Any],
    system: str | None = None,
) -> str:
    """Ask Claude to suggest the next action for a student acting as the agent."""
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
    client: ClaudeClient,
    tools: list[dict[str, Any]],
    tool_runner,
    question: str,
    system: str = DEFAULT_SYSTEM_PROMPT,
    max_steps: int = 8,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Run a Claude tool-use agent loop.

    Follows the battle-tested pattern from create_v3_notebooks.py:
    - Client-side message history (no server-side state)
    - Serialize assistant content as dicts for message history
    - Tool results sent as user messages with tool_result blocks
    """
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": question},
    ]
    tool_calls_log: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        response = client.create_message(
            messages=messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
        )

        tool_use_blocks = extract_tool_use_blocks(response)

        if not tool_use_blocks:
            # No tool calls — final text answer
            return {
                "answer": extract_text(response),
                "tool_calls": tool_calls_log,
                "messages": messages,
                "model": response.model,
                "completed": True,
            }

        # Serialize assistant content for message history
        assistant_content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool call and collect results
        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
            fn_name = block.name
            fn_args = block.input

            try:
                result = tool_runner(fn_name, fn_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_calls_log.append({
                "step": step,
                "tool": fn_name,
                "arguments": fn_args,
                "result_preview": str(result)[:300],
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
            })

        # Send tool results back as a user message
        messages.append({"role": "user", "content": tool_results})

    # Reached max steps — return what we have
    return {
        "answer": extract_text(response),
        "tool_calls": tool_calls_log,
        "messages": messages,
        "model": response.model,
        "completed": False,
        "stop_reason": f"max_steps_exceeded:{max_steps}",
    }

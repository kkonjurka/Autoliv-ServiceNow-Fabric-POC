"""app.py — ServiceNow Orchestrator Agent entry point.

Creates (or reuses) the Foundry hosted agent, registers tool functions, and
provides a run_query() helper for local testing and for Azure Container Apps
deployment.

Usage:
    python app.py                        # interactive CLI loop
    python app.py --query "..."          # single query, print result and exit

Environment variables (see .env.example):
    AZURE_AI_PROJECT_CONNECTION_STRING   — Foundry project connection string
    FOUNDRY_ORCHESTRATOR_AGENT_NAME      — agent name (default: servicenow-orchestrator)
    FOUNDRY_MODEL                        — model deployment name (default: gpt-4o)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    FunctionTool,
    ToolSet,
)
from azure.identity import DefaultAzureCredential

from tools import (
    get_attachment_metadata,
    query_fabric_data_agent,
    search_incidents,
    search_knowledge,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("orchestrator")

_HERE = pathlib.Path(__file__).parent
_INSTRUCTIONS_FILE = _HERE / "instructions.md"
_TOOL_SCHEMAS_FILE = _HERE / "tool_schemas.json"

_AGENT_NAME = os.environ.get("FOUNDRY_ORCHESTRATOR_AGENT_NAME", "servicenow-orchestrator")
_MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-4o")

# Map function names to callables so the SDK can dispatch tool calls.
_TOOL_FUNCTIONS = {
    "query_fabric_data_agent": query_fabric_data_agent,
    "search_knowledge": search_knowledge,
    "search_incidents": search_incidents,
    "get_attachment_metadata": get_attachment_metadata,
}


def _build_client() -> AIProjectClient:
    conn_str = os.environ.get("AZURE_AI_PROJECT_CONNECTION_STRING", "")
    if not conn_str:
        raise EnvironmentError(
            "AZURE_AI_PROJECT_CONNECTION_STRING is not set. "
            "See foundry-agent/DEPLOY.md for setup instructions."
        )
    return AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str,
    )


def _load_instructions() -> str:
    return _INSTRUCTIONS_FILE.read_text(encoding="utf-8")


def _load_tool_schemas() -> list[dict]:
    data = json.loads(_TOOL_SCHEMAS_FILE.read_text(encoding="utf-8"))
    return data.get("tools", [])


def _get_or_create_agent(client: AIProjectClient) -> Any:
    """Return the existing agent by name, or create it if absent."""
    for agent in client.agents.list_agents().value:
        if agent.name == _AGENT_NAME:
            logger.info("Reusing existing agent: %s (%s)", agent.name, agent.id)
            return agent

    instructions = _load_instructions()
    schemas = _load_tool_schemas()
    toolset = ToolSet()
    toolset.add(FunctionTool(functions=set(_TOOL_FUNCTIONS.values())))

    agent = client.agents.create_agent(
        model=_MODEL,
        name=_AGENT_NAME,
        instructions=instructions,
        tools=toolset.definitions,
        temperature=0.2,
    )
    logger.info("Created agent: %s (%s)", agent.name, agent.id)
    return agent


def run_query(question: str, thread_id: str | None = None) -> dict[str, Any]:
    """Run a single question through the orchestrator and return the full response.

    Args:
        question:   The user's natural-language question.
        thread_id:  Optional existing thread ID to continue a conversation.

    Returns:
        dict with keys:
            answer (str):     The agent's final markdown-formatted response.
            thread_id (str):  Thread ID (pass back in for multi-turn conversations).
            run_id (str):     Run ID for auditing.
    """
    client = _build_client()
    agent = _get_or_create_agent(client)

    if thread_id:
        thread = client.agents.get_thread(thread_id)
    else:
        thread = client.agents.create_thread()

    client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=question,
    )

    run = client.agents.create_and_process_run(
        thread_id=thread.id,
        assistant_id=agent.id,
        tool_resources=ToolSet(functions=_TOOL_FUNCTIONS),
    )

    messages = client.agents.list_messages(thread_id=thread.id)
    answer_message = next(
        (m for m in reversed(messages.value) if m.role == "assistant"),
        None,
    )
    answer_text = (
        answer_message.content[0].text.value
        if answer_message and answer_message.content
        else "(no response)"
    )

    return {
        "answer": answer_text,
        "thread_id": thread.id,
        "run_id": run.id,
    }


def _interactive_loop() -> None:
    print("ServiceNow Orchestrator Agent — type 'quit' to exit.\n")
    thread_id: str | None = None
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            continue
        result = run_query(question, thread_id=thread_id)
        thread_id = result["thread_id"]
        print(f"\nAgent:\n{result['answer']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="ServiceNow Orchestrator Agent")
    parser.add_argument("--query", "-q", help="Single query to run (non-interactive)")
    args = parser.parse_args()

    if args.query:
        result = run_query(args.query)
        print(result["answer"])
    else:
        _interactive_loop()


if __name__ == "__main__":
    main()

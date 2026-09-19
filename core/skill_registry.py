"""
core/skill_registry.py — LLM Skill Descriptor Generator
=========================================================
Generates a  skill.json  file (or prints instructions as text) so that
any LLM / AI Agent framework can discover and call KeyReach automatically.

The format is intentionally compatible with:
    - OpenAI / GPT function calling schema
    - Anthropic Claude tool use schema
    - LangChain Tool format
    - AutoGen / AgentBench skill descriptors
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# ── Skill descriptor ─────────────────────────────────────────────────────────
SKILL_DESCRIPTOR = {
    "schema_version": "1.0",
    "name": "keyreach",
    "display_name": "KeyReach — AI Agent Capability Layer",
    "description": (
        "A CLI tool that gives AI Agents the ability to fetch web content, "
        "search the internet, and interact with social media platforms. "
        "All output is structured JSON or Markdown, safe for LLM consumption. "
        "Supports automatic backend fallback — if one source fails, it tries another."
    ),
    "version": "1.0.0",
    "author": "your-org",
    "generated_at": "",  # filled at runtime
    "invocation": {
        "type": "cli",
        "executable": "python main.py",
        "working_directory": ".",
    },
    "commands": [
        {
            "name": "fetch",
            "description": (
                "Fetch and extract the text content of any public web page or "
                "social media profile.  The tool automatically selects the best "
                "backend and falls back if needed."
            ),
            "usage": "python main.py fetch <url> [--timeout <seconds>] [--channel <name>]",
            "parameters": [
                {
                    "name": "url",
                    "type": "string",
                    "required": True,
                    "description": "The full URL to fetch (must start with http:// or https://).",
                    "example": "https://news.ycombinator.com",
                },
                {
                    "name": "--timeout",
                    "type": "integer",
                    "required": False,
                    "default": 15,
                    "description": "Request timeout in seconds.",
                },
                {
                    "name": "--channel",
                    "type": "string",
                    "required": False,
                    "allowed_values": ["web", "twitter", "jina"],
                    "description": (
                        "Force a specific backend channel. "
                        "Leave empty for automatic selection."
                    ),
                },
                {
                    "name": "--format",
                    "type": "string",
                    "required": False,
                    "default": "json",
                    "allowed_values": ["json", "markdown"],
                    "description": "Output format. Use 'json' for structured parsing.",
                },
            ],
            "output": {
                "on_success": {
                    "status": "ok",
                    "url": "<string>",
                    "content": "<string — page text>",
                    "backend_used": "<string>",
                    "backends_attempted": ["<string>"],
                    "elapsed_ms": "<integer>",
                },
                "on_failure": {
                    "status": "error",
                    "url": "<string>",
                    "error": "<string — human-readable reason>",
                    "backends_attempted": ["<string>"],
                    "elapsed_ms": "<integer>",
                    "hint": "<string — suggested next step>",
                },
            },
            "examples": [
                {
                    "description": "Fetch Hacker News front page",
                    "command": "python main.py fetch https://news.ycombinator.com",
                },
                {
                    "description": "Fetch a Twitter/X profile",
                    "command": "python main.py fetch https://twitter.com/elonmusk",
                },
                {
                    "description": "Force Jina Reader for a JS-heavy page",
                    "command": (
                        "python main.py fetch https://example-spa.com "
                        "--channel jina"
                    ),
                },
            ],
        },
        {
            "name": "search",
            "description": "Search the web and return structured results (title, URL, snippet).",
            "usage": "python main.py search <query> [--limit <n>]",
            "parameters": [
                {
                    "name": "query",
                    "type": "string",
                    "required": True,
                    "description": "The search query string.",
                    "example": "Python AI agent frameworks 2025",
                },
                {
                    "name": "--limit",
                    "type": "integer",
                    "required": False,
                    "default": 5,
                    "description": "Maximum number of results to return (1–20).",
                },
            ],
            "output": {
                "on_success": {
                    "status": "ok",
                    "query": "<string>",
                    "results": [{"title": "<str>", "url": "<str>", "snippet": "<str>"}],
                    "count": "<integer>",
                    "elapsed_ms": "<integer>",
                },
            },
            "examples": [
                {
                    "description": "Search for AI news",
                    "command": 'python main.py search "OpenAI GPT-5" --limit 10',
                },
            ],
        },
        {
            "name": "status",
            "description": "Check the health of all registered backend channels.",
            "usage": "python main.py status",
            "parameters": [],
            "output": {
                "on_success": {
                    "status": "ok",
                    "channels": [{"name": "<str>", "healthy": True, "detail": "<str>"}],
                    "summary": "<string>",
                },
            },
        },
        {
            "name": "skill-register",
            "description": "Re-generate this skill.json file or print instructions.",
            "usage": "python main.py skill-register [--output <path>] [--print-only]",
            "parameters": [
                {
                    "name": "--output",
                    "type": "string",
                    "required": False,
                    "default": "skill.json",
                },
                {
                    "name": "--print-only",
                    "type": "boolean",
                    "required": False,
                    "default": False,
                    "description": "Print instructions to stdout without writing a file.",
                },
            ],
        },
    ],
    "decision_guide": (
        "Use 'fetch' when you need the full text of a specific URL. "
        "Use 'search' when you need to discover URLs for a topic. "
        "Use 'status' to check if backends are available before a batch operation. "
        "Always check the 'status' field in the response first before reading 'content'."
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────

def generate_skill_file(output_path: str = "skill.json") -> str:
    """
    Write SKILL_DESCRIPTOR as JSON to *output_path*.

    Returns the absolute path of the written file.
    """
    descriptor = dict(SKILL_DESCRIPTOR)
    descriptor["generated_at"] = datetime.now(tz=timezone.utc).isoformat()

    path = Path(output_path).resolve()
    path.write_text(
        json.dumps(descriptor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def print_skill_instructions() -> str:
    """
    Return a concise natural-language description of the skill,
    suitable for embedding in an LLM system prompt.
    """
    lines = [
        "# KeyReach CLI Skill Instructions",
        "",
        "You have access to the `keyreach` command-line tool.  "
        "Run it via shell/terminal to interact with the web.",
        "",
        "## Fetch a URL",
        "```",
        "python main.py fetch <url>",
        "```",
        "Returns JSON: {status, content, backend_used, elapsed_ms}",
        "",
        "## Search the Web",
        "```",
        "python main.py search \"<query>\" --limit 5",
        "```",
        "Returns JSON: {status, results: [{title, url, snippet}]}",
        "",
        "## Check Backend Health",
        "```",
        "python main.py status",
        "```",
        "",
        "## Rules",
        "- Always parse `status` first: if it is `error`, read `error` and `hint`.",
        "- Prefer `--format json` for programmatic parsing.",
        "- For Twitter/X URLs, the tool auto-routes to a Nitter proxy — no API key needed.",
        "- For JS-heavy pages, pass `--channel jina` to use the Jina Reader fallback.",
    ]
    return "\n".join(lines)

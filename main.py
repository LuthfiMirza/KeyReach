#!/usr/bin/env python3
"""
KeyReach CLI — AI Agent Capability Layer
Entry point for all agent-callable commands.

Usage:
    python main.py fetch <url> [--format json|markdown]
    python main.py search <query> [--limit 5]
    python main.py skill-register [--output skill.json]
    python main.py status
"""

import sys
import json
import click
from router import AgentRouter
from core.logger import get_logger
from core.skill_registry import generate_skill_file, print_skill_instructions

logger = get_logger(__name__)

# ── Shared context passed down to all sub-commands ──────────────────────────
@click.group()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output format for AI Agent consumption.",
)
@click.pass_context
def cli(ctx: click.Context, output_format: str):
    """
    KeyReach — Modular Capability Layer for AI Agents.

    All commands output clean JSON or Markdown suitable for LLM parsing.
    Debug logs are written to app.log only.
    """
    ctx.ensure_object(dict)
    ctx.obj["format"] = output_format
    ctx.obj["router"] = AgentRouter()


# ── fetch ────────────────────────────────────────────────────────────────────
@cli.command()
@click.argument("url")
@click.option("--timeout", default=15, show_default=True, help="Request timeout in seconds.")
@click.option("--channel", default=None, help="Force a specific channel (web, twitter, …).")
@click.pass_context
def fetch(ctx: click.Context, url: str, timeout: int, channel: str):
    """
    Fetch content from URL using the best available backend.

    The router will automatically select the appropriate channel and
    fall back to secondary backends if the primary one fails.

    \b
    Examples:
        python main.py fetch https://example.com
        python main.py fetch https://twitter.com/elonmusk --channel twitter
        python main.py --format markdown fetch https://news.ycombinator.com
    """
    logger.info("fetch command called: url=%s channel=%s timeout=%s", url, channel, timeout)

    router: AgentRouter = ctx.obj["router"]
    result = router.fetch(url=url, timeout=timeout, preferred_channel=channel)

    _emit(result, ctx.obj["format"])


# ── search ───────────────────────────────────────────────────────────────────
@cli.command()
@click.argument("query")
@click.option("--limit", default=5, show_default=True, help="Maximum number of results.")
@click.pass_context
def search(ctx: click.Context, query: str, limit: int):
    """
    Search the web for QUERY and return structured results.

    \b
    Examples:
        python main.py search "OpenAI GPT-5 release" --limit 10
    """
    logger.info("search command called: query=%s limit=%s", query, limit)

    router: AgentRouter = ctx.obj["router"]
    result = router.search(query=query, limit=limit)

    _emit(result, ctx.obj["format"])


# ── skill-register ───────────────────────────────────────────────────────────
@cli.command("skill-register")
@click.option(
    "--output",
    default="skill.json",
    show_default=True,
    help="Path to write the generated skill descriptor.",
)
@click.option(
    "--print-only",
    is_flag=True,
    default=False,
    help="Print skill instructions to stdout without writing a file.",
)
@click.pass_context
def skill_register(ctx: click.Context, output: str, print_only: bool):
    """
    Generate a skill descriptor (skill.json) so LLMs know how to use KeyReach.

    \b
    Examples:
        python main.py skill-register
        python main.py skill-register --output my_skill.json
        python main.py skill-register --print-only
    """
    if print_only:
        instructions = print_skill_instructions()
        _emit({"skill_instructions": instructions}, ctx.obj["format"])
    else:
        path = generate_skill_file(output)
        _emit(
            {"status": "ok", "message": f"Skill file written to '{path}'", "path": path},
            ctx.obj["format"],
        )


# ── status ────────────────────────────────────────────────────────────────────
@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """
    Report the health / availability of all registered backends.

    \b
    Example:
        python main.py status
    """
    router: AgentRouter = ctx.obj["router"]
    result = router.health_check()
    _emit(result, ctx.obj["format"])


# ── internal helpers ──────────────────────────────────────────────────────────
def _emit(data: dict, fmt: str) -> None:
    """Write *data* to stdout in the requested format and exit cleanly."""
    if fmt == "markdown":
        _emit_markdown(data)
    else:
        # Default: pure JSON — no extra text, no colour codes
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _emit_markdown(data: dict) -> None:
    """Convert a result dict to structured Markdown for LLM readability."""
    status = data.get("status", "unknown")
    lines = [f"## KeyReach Result\n", f"**Status:** `{status}`\n"]

    if status == "ok":
        content = data.get("content", "")
        backend = data.get("backend_used", "n/a")
        url = data.get("url", "")
        lines.append(f"**Backend:** `{backend}`")
        if url:
            lines.append(f"**URL:** {url}")
        lines.append("\n---\n")
        lines.append(content[:4000])  # truncate for safety
    else:
        error = data.get("error", "Unknown error")
        attempted = data.get("backends_attempted", [])
        lines.append(f"**Error:** {error}")
        if attempted:
            lines.append(f"**Backends tried:** {', '.join(attempted)}")

    click.echo("\n".join(lines))


# ── entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli(obj={})

#!/usr/bin/env python3
"""Command-line interface for Humitron."""

import sys
from pathlib import Path
from typing import Optional
import argparse

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.syntax import Syntax

from humitron.agent import ReActAgent
from humitron.config.loader import get_config
from humitron.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)
console = Console()


def run_chat_loop(agent: ReActAgent) -> None:
    """Run continuous chat loop until user types 'exit'.

    Args:
        agent: ReActAgent instance to use for chat.
    """
    console.print(Panel(
        Markdown("""
# 🤖 Humitron - Local AI Agent

**Commands:**
- Type your question or task
- Type `exit` or `quit` to leave
- Type `clear` to reset conversation history
- Type `config` to show current configuration
"""),
        title="Welcome to Humitron",
        border_style="cyan",
        padding=(1, 2)
    ))

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if user_input.lower().strip() in ("exit", "quit"):
                console.print("[yellow]👋 Goodbye![/yellow]")
                break

            if user_input.lower().strip() == "clear":
                agent.memory = agent.__class__.__new__(agent.__class__)
                agent.memory.__init__(max_tokens=get_config().max_tokens_per_call)
                agent.memory.add_message("system", agent.system_prompt)
                console.print("[green]✨ Conversation history cleared.[/green]")
                continue

            if user_input.lower().strip() == "config":
                config = get_config()
                console.print(Panel(
                    Syntax(str(config.to_dict()), "yaml", theme="monokai"),
                    title="⚙️ Current Configuration",
                    border_style="cyan"
                ))
                continue

            if not user_input.strip():
                continue

            # Run agent and display result
            try:
                result = agent.run(user_input)
                console.print(Panel(
                    Markdown(result),
                    title="💬 Humitron",
                    border_style="green",
                    padding=(1, 2)
                ))
            except ConnectionError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                console.print("[yellow]Make sure Ollama is running: [bold]ollama serve[/bold][/yellow]")
                console.print(f"[yellow]And the model is pulled: [bold]ollama pull {get_config().model}[/bold][/yellow]")
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                logger.exception("Agent error")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except EOFError:
            break


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Humitron ReAct Agent")
    parser.add_argument("prompt", nargs="*", help="Prompt for the agent (optional, starts chat loop if omitted)")
    parser.add_argument("--model", default=None, help="Ollama model to use")
    parser.add_argument("--max-steps", type=int, default=None, help="Max steps per query")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace directory")
    parser.add_argument("--temperature", type=float, default=None, help="LLM temperature")
    parser.add_argument("--log-level", default=None, help="Log level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--no-chat", action="store_true", help="Run single prompt and exit (no chat loop)")

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_level=args.log_level)

    # Create agent
    agent = ReActAgent(
        model=args.model,
        max_steps=args.max_steps,
        workspace=args.workspace,
        temperature=args.temperature
    )

    # If prompt provided, run single query
    if args.prompt:
        prompt = " ".join(args.prompt)
        try:
            result = agent.run(prompt)
            console.print(Panel(
                Markdown(result),
                title="💬 Humitron",
                border_style="green",
                padding=(1, 2)
            ))
        except ConnectionError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("[yellow]Make sure Ollama is running: [bold]ollama serve[/bold][/yellow]")
            console.print(f"[yellow]And the model is pulled: [bold]ollama pull {get_config().model}[/bold][/yellow]")
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user.[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            logger.exception("Agent error")
            sys.exit(1)
    else:
        # Run interactive chat loop
        try:
            run_chat_loop(agent)
        except ConnectionError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("[yellow]Make sure Ollama is running: [bold]ollama serve[/bold][/yellow]")
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            logger.exception("Chat error")
            sys.exit(1)


if __name__ == "__main__":
    main()
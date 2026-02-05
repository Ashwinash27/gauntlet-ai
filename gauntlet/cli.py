"""Gauntlet CLI.

Usage:
    gauntlet detect "text to check"
    gauntlet detect --file input.txt
    gauntlet scan ./prompts/ --pattern "*.txt"
    gauntlet config set openai_key sk-xxx
    gauntlet config list
    gauntlet mcp-serve

Requires: pip install gauntlet-ai[cli]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _get_app():
    """Create and return the Typer app."""
    try:
        import typer
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        print("CLI requires typer and rich. Install with: pip install gauntlet-ai[cli]")
        sys.exit(1)

    app = typer.Typer(
        name="gauntlet",
        help="Prompt injection detection for LLM applications.",
        no_args_is_help=True,
    )
    config_app = typer.Typer(help="Manage configuration.")
    app.add_typer(config_app, name="config")

    console = Console()
    err_console = Console(stderr=True)

    @app.command()
    def detect(
        text: str = typer.Argument(None, help="Text to analyze"),
        file: Path = typer.Option(None, "--file", "-f", help="Read text from file"),
        all_layers: bool = typer.Option(False, "--all", "-a", help="Run all configured layers"),
        layers: str = typer.Option(None, "--layers", "-l", help="Comma-separated layer numbers (e.g., 1,2)"),
        output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    ) -> None:
        """Detect prompt injection in text."""
        from gauntlet import Gauntlet

        # Get input text
        if file:
            if not file.exists():
                err_console.print(f"[red]File not found: {file}[/red]")
                raise typer.Exit(1)
            input_text = file.read_text()
        elif text:
            input_text = text
        elif not sys.stdin.isatty():
            input_text = sys.stdin.read()
        else:
            err_console.print("[red]Provide text as argument, --file, or pipe via stdin[/red]")
            raise typer.Exit(1)

        if not input_text.strip():
            err_console.print("[red]Empty input[/red]")
            raise typer.Exit(1)

        # Configure layers
        g = Gauntlet()
        run_layers = None
        if layers:
            run_layers = [int(l.strip()) for l in layers.split(",")]
        elif all_layers:
            run_layers = None  # Use all available
        else:
            run_layers = [1]  # Default: rules only

        result = g.detect(input_text, layers=run_layers)

        if output_json:
            console.print_json(result.model_dump_json())
            raise typer.Exit(0 if not result.is_injection else 1)

        # Rich output
        if result.is_injection:
            console.print()
            console.print(f"  [bold red]INJECTION DETECTED[/bold red]")
            console.print(f"  [dim]Layer {result.detected_by_layer}[/dim] | "
                         f"[dim]Confidence:[/dim] [yellow]{result.confidence:.0%}[/yellow] | "
                         f"[dim]Type:[/dim] [cyan]{result.attack_type}[/cyan]")

            for lr in result.layer_results:
                if lr.details:
                    if lr.layer == 1 and lr.details.get("pattern_name"):
                        console.print(f"  [dim]Pattern:[/dim] {lr.details['pattern_name']}")
                    if lr.layer == 3 and lr.details.get("reasoning"):
                        console.print(f"  [dim]Reasoning:[/dim] {lr.details['reasoning']}")

            console.print(f"  [dim]Latency:[/dim] {result.total_latency_ms:.1f}ms")
        else:
            console.print()
            console.print(f"  [bold green]CLEAN[/bold green]")
            layers_run = [str(lr.layer) for lr in result.layer_results]
            console.print(f"  [dim]Layers checked:[/dim] {', '.join(layers_run)} | "
                         f"[dim]Latency:[/dim] {result.total_latency_ms:.1f}ms")

        # Show errors from layers that failed open
        if result.errors:
            console.print()
            console.print(f"  [bold yellow]WARNINGS[/bold yellow] [dim]({len(result.errors)} layer(s) failed open)[/dim]")
            for error in result.errors:
                console.print(f"  [yellow]  - {error}[/yellow]")
            console.print(f"  [dim]These layers returned 'not injection' due to errors.[/dim]")
            console.print(f"  [dim]Fix the issue and re-run to get full coverage.[/dim]")

        # Show skipped layers
        if result.layers_skipped:
            layer_names = {2: "embeddings (needs OpenAI key + numpy)", 3: "llm_judge (needs Anthropic key)"}
            console.print()
            console.print(f"  [dim]Layers skipped:[/dim]")
            for layer_num in result.layers_skipped:
                console.print(f"  [dim]  - Layer {layer_num}: {layer_names.get(layer_num, 'unknown')}[/dim]")

        console.print()
        raise typer.Exit(1 if result.is_injection else 0)

    @app.command()
    def scan(
        directory: Path = typer.Argument(..., help="Directory to scan"),
        pattern: str = typer.Option("*.txt", "--pattern", "-p", help="File glob pattern"),
        all_layers: bool = typer.Option(False, "--all", "-a", help="Run all configured layers"),
        output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    ) -> None:
        """Scan files in a directory for prompt injections."""
        from gauntlet import Gauntlet

        if not directory.is_dir():
            err_console.print(f"[red]Not a directory: {directory}[/red]")
            raise typer.Exit(1)

        files = sorted(directory.glob(pattern))
        if not files:
            err_console.print(f"[yellow]No files matching '{pattern}' in {directory}[/yellow]")
            raise typer.Exit(0)

        g = Gauntlet()
        run_layers = None if all_layers else [1]
        results = []
        flagged = 0

        for filepath in files:
            try:
                text = filepath.read_text()
            except Exception as e:
                err_console.print(f"[yellow]Skipping {filepath}: {e}[/yellow]")
                continue

            result = g.detect(text, layers=run_layers)
            results.append({"file": str(filepath), "result": result.model_dump()})

            if result.is_injection:
                flagged += 1
                if not output_json:
                    console.print(
                        f"  [red]FLAGGED[/red] {filepath.name} "
                        f"[dim]({result.attack_type}, {result.confidence:.0%})[/dim]"
                    )
            elif not output_json:
                console.print(f"  [green]CLEAN[/green]  {filepath.name}")

        if output_json:
            console.print_json(json.dumps(results, default=str))
        else:
            console.print()
            console.print(
                f"  [dim]Scanned {len(files)} files:[/dim] "
                f"[red]{flagged} flagged[/red], "
                f"[green]{len(files) - flagged} clean[/green]"
            )
            console.print()

        raise typer.Exit(1 if flagged > 0 else 0)

    @config_app.command("set")
    def config_set(
        key: str = typer.Argument(..., help="Config key"),
        value: str = typer.Argument(..., help="Config value"),
    ) -> None:
        """Set a config value."""
        from gauntlet.config import set_config_value

        try:
            set_config_value(key, value)
            console.print(f"  [green]Set {key}[/green]")
        except Exception as e:
            err_console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    @config_app.command("list")
    def config_list() -> None:
        """Show current configuration."""
        from gauntlet.config import list_config

        table = Table(show_header=True, header_style="bold")
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for key, value in list_config().items():
            if value is None:
                table.add_row(key, "[dim]not set[/dim]")
            else:
                table.add_row(key, str(value))

        console.print()
        console.print(table)
        console.print()

    @app.command("mcp-serve")
    def mcp_serve() -> None:
        """Start the MCP server for Claude Code integration."""
        try:
            from gauntlet.mcp_server import serve
            serve()
        except ImportError:
            err_console.print(
                "[red]MCP server requires mcp package. "
                "Install with: pip install gauntlet-ai[mcp][/red]"
            )
            raise typer.Exit(1)

    return app


app = _get_app()


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

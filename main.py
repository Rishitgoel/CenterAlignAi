import argparse
import asyncio
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()


def print_banner():
    banner_text = (
        "[bold white]CentrAlign AI - Autonomous Task Worker[/bold white]\n"
        "[dim]Goal-Driven Enterprise Task Worker Prototype[/dim]"
    )
    console.print(Panel(banner_text, expand=False, border_style="white"))


def handle_run(args):
    print_banner()
    from agent.core import Agent

    agent = Agent(interactive=not args.non_interactive)
    asyncio.run(agent.run(args.task))


def handle_server(args):
    print_banner()
    console.print(f"[bold white]Starting Mock ERP Server on {args.host}:{args.port}...[/bold white]")
    console.print(f"  [bold white]- Web Portal    :[/bold white] http://{args.host}:{args.port}/portal")
    console.print(f"  [bold white]- Swagger Docs  :[/bold white] http://{args.host}:{args.port}/docs")
    console.print(f"  [bold white]- Health Status :[/bold white] http://{args.host}:{args.port}/health")
    console.print(f"[dim]Tip: Keep this terminal open. Run autonomous agent tasks in a second terminal.[/dim]\n")
    import uvicorn
    if getattr(args, "reload", True):
        uvicorn.run("mock_erp.app:app", host=args.host, port=args.port, reload=True)
    else:
        from mock_erp.app import app
        uvicorn.run(app, host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Task Worker Prototype for Enterprise Systems"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run the autonomous agent on a natural language task")
    run_parser.add_argument("--task", type=str, required=True, help="Natural language goal or task prompt")
    run_parser.add_argument("--non-interactive", action="store_true", default=False, help="Disable interactive approval prompt (auto-approve)")

    # Server subcommand
    server_parser = subparsers.add_parser("server", help="Launch the local mock ERP / CRM FastAPI server")
    server_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.add_argument("--no-reload", dest="reload", action="store_false", default=True, help="Disable auto-reload")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        handle_run(args)
    elif args.command == "server":
        handle_server(args)


if __name__ == "__main__":
    main()

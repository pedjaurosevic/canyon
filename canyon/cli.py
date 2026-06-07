import click
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

# Add parent dir to path to support running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from canyon.engine import CanyonEngine

console = Console()

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """CANYON: a framework for mechanistic and behavioural evaluation of LLMs."""
    if ctx.invoked_subcommand is None:
        from canyon.tui import CanyonTUI
        app = CanyonTUI()
        app.run()

@cli.command()
@click.option("--config", default="config.example.yaml", help="Path to the configuration file.")
@click.option("--model", default=None, help="Model name for API evaluation (LiteLLM).")
@click.option("--local", is_flag=True, help="Use a local Hugging Face model (white-box).")
@click.option("--lang", default=None, help="Suite language: en, zh, ja, ru, de, es (defaults to Serbian).")
def run(config, model, local, lang):
    """Run a full model evaluation."""
    rprint(Panel(
        Text("CANYON EVALUATION HARNESS", style="bold magenta", justify="center"),
        subtitle="Hinton Grounding Benchmark",
        border_style="cyan"
    ))

    if not os.path.exists(config):
        rprint(f"[bold red]Error:[/] Configuration file '{config}' does not exist.")
        sys.exit(1)

    engine = CanyonEngine(config)

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:

        task = progress.add_task("[cyan]Preparing the benchmark...", total=3)

        def progress_cb(suite, test_name, step, total_steps):
            progress.update(
                task,
                description=f"[yellow]Suite: {suite}[/] | Test: {test_name} ({step}/{total_steps})"
            )

        progress.update(task, description="Running test suites...", advance=1)
        report = engine.run_eval(model=model, use_local=local, lang=lang, progress_cb=progress_cb)
        progress.update(task, description="Evaluating metrics...", advance=2)

    metrics = report["metrics"]

    table = Table(title="Semantic Grounding Evaluation Results (SPI)", border_style="dim")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Score", style="bold green", justify="right")
    table.add_column("Interpretation", style="yellow")

    table.add_row(
        "Counterfactual Plasticity (CP-Score)",
        f"{metrics['cp_score']:.2f}",
        "Ability to maintain altered laws of logic/physics."
    )
    table.add_row(
        "Contextual Realignment (CR-Score)",
        f"{metrics['cr_score']:.2f}",
        "Speed and sharpness of correcting internal representations."
    )
    table.add_row(
        "Semantic Invariance (SI-Score)",
        f"{metrics['si_score']:.2f}",
        "Stability of abstract understanding across paraphrases."
    )
    table.add_row(
        "Stochastic Parrot Index (SPI)",
        f"{metrics['stochastic_parrot_index']:.2f}",
        "Overall semantic grounding index of the model (groundedness)."
    )

    console.print("\n")
    console.print(table)

    cls_style = (
        "bold green" if "Strong" in report["classification"]
        else "bold yellow" if "Weak" in report["classification"]
        else "bold red"
    )

    console.print("\n")
    console.print(Panel(
        Text(f"Model classification: {report['classification']}", style=cls_style, justify="center"),
        title="Final Benchmark Verdict",
        border_style="magenta"
    ))

    # Display Semantic Drift Analysis if available
    drift_trajs = report.get("drift_trajectories", {})
    if drift_trajs:
        console.print("\n[bold magenta]📈 Latent-space semantic drift analysis[/]")
        from canyon.metrics import SemanticDriftProbe
        for test_id, trajs in drift_trajs.items():
            for traj_info in trajs:
                from_s = traj_info["from_step"]
                to_s = traj_info["to_step"]
                traj_data = traj_info["trajectory"]

                graph = SemanticDriftProbe.generate_ascii_graph(traj_data)
                console.print(f"\n[yellow]Test ID: {test_id}[/] (step {from_s + 1} ➔ step {to_s + 1}, cosine similarity per layer):")
                console.print(graph)

    console.print("\n[bold cyan]Detailed test logs:[/] ")
    log_table = Table(border_style="dim", box=None)
    log_table.add_column("Suite", style="dim")
    log_table.add_column("Test", style="bold white")
    log_table.add_column("Prompt", style="italic")
    log_table.add_column("Model output", style="green")

    for r in report["raw_results"]:
        log_table.add_row(
            r["suite_id"],
            r["test_name"],
            r["prompt"][:50] + "..." if len(r["prompt"]) > 50 else r["prompt"],
            r["output"][:50] + "..." if len(r["output"]) > 50 else r["output"]
        )
    console.print(log_table)

@cli.command()
def list_suites():
    """List all available benchmark test suites."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suites_dir = os.path.join(base_dir, "suites")

    if not os.path.exists(suites_dir):
        rprint("[bold red]Error: suites folder does not exist.[/]")
        return

    table = Table(title="Available CANYON test suites", border_style="cyan")
    table.add_column("File", style="yellow")
    table.add_column("Number of tests", style="green", justify="right")

    import json
    for f in os.listdir(suites_dir):
        if f.endswith(".json"):
            with open(os.path.join(suites_dir, f), "r", encoding="utf-8") as file:
                data = json.load(file)
                table.add_row(f, str(len(data)))

    console.print(table)

@cli.command()
@click.option("--layer", default=12, help="Model layer to probe (linear probe).")
@click.option("--config", default="config.example.yaml", help="Path to the configuration file.")
def probe(layer, config):
    """Run a linear classification probe over a local model's hidden states."""
    rprint(Panel(
        Text(f"Linear probing on layer {layer}", style="bold magenta", justify="center"),
        border_style="cyan"
    ))

    if not os.path.exists(config):
        rprint(f"[bold red]Error:[/] Configuration file '{config}' does not exist.")
        sys.exit(1)

    engine = CanyonEngine(config)

    positives = [
        "The ball fell to the ground after I dropped it.",
        "The stone sank to the bottom of the river.",
        "The person got into the car and started the engine."
    ]
    negatives = [
        "The ball flew off into space after I dropped it on the ground.",
        "The stone floated in the air above the river all by itself.",
        "The building started walking down the street looking for food."
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Loading the local model and extracting activations..."),
        console=console
    ) as progress:
        progress.add_task("probing", total=None)
        try:
            provider = engine.get_local_provider()
            probe_result = provider.train_linear_probe(layer, positives, negatives)
        except Exception as e:
            rprint(f"\n[bold red]Error during linear probing (a local GPU/HF model is required):[/] {str(e)}")
            return

    rprint("\n[bold green]✅ Linear probe training complete![/]")
    rprint(f"Bias at layer {layer}: {probe_result['bias']:.4f}")
    rprint(f"Extracted weights: {len(probe_result['weights'])}")
    rprint("[yellow]The linear probe is ready to detect physical plausibility inside the model's latent space.[/]")

if __name__ == "__main__":
    cli()

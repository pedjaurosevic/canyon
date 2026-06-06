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
    """CANYON: Framework za mehanističku i bihevioralnu evaluaciju LLM-ova."""
    if ctx.invoked_subcommand is None:
        from canyon.tui import CanyonTUI
        app = CanyonTUI()
        app.run()

@cli.command()
@click.option("--config", default="config.example.yaml", help="Putanja do konfiguracionog fajla.")
@click.option("--model", default=None, help="Naziv modela za API evaluaciju (LiteLLM).")
@click.option("--local", is_flag=True, help="Koristi lokalni Hugging Face model (white-box).")
@click.option("--lang", default=None, help="Jezik suite-a: en, zh, ja, ru, de, es (podrazumevano srpski).")
def run(config, model, local, lang):
    """Pokreće kompletnu evaluaciju modela."""
    rprint(Panel(
        Text("CANYON EVALUATION HARNESS", style="bold magenta", justify="center"),
        subtitle="Hinton Grounding Benchmark",
        border_style="cyan"
    ))
    
    if not os.path.exists(config):
        rprint(f"[bold red]Greška:[/] Konfiguracioni fajl '{config}' ne postoji.")
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
        
        task = progress.add_task("[cyan]Priprema benchmark-a...", total=3)
        
        def progress_cb(suite, test_name, step, total_steps):
            progress.update(
                task, 
                description=f"[yellow]Suite: {suite}[/] | Test: {test_name} ({step}/{total_steps})"
            )
            
        progress.update(task, description="Pokretanje test suite-ova...", advance=1)
        report = engine.run_eval(model=model, use_local=local, lang=lang, progress_cb=progress_cb)
        progress.update(task, description="Evaluacija metrika...", advance=2)
        
    metrics = report["metrics"]
    
    table = Table(title="Rezultati Evaluacije Semantičkog Utemeljenja (SPI)", border_style="dim")
    table.add_column("Metrika", style="cyan", no_wrap=True)
    table.add_column("Skor", style="bold green", justify="right")
    table.add_column("Interpretacija", style="yellow")
    
    table.add_row(
        "Counterfactual Plasticity (CP-Score)", 
        f"{metrics['cp_score']:.2f}",
        "Sposobnost održavanja izmenjenih zakona logike/fizike."
    )
    table.add_row(
        "Contextual Realignment (CR-Score)", 
        f"{metrics['cr_score']:.2f}",
        "Brzina i oštrina korekcije unutrašnjih reprezentacija."
    )
    table.add_row(
        "Semantic Invariance (SI-Score)", 
        f"{metrics['si_score']:.2f}",
        "Stabilnost apstraktnog razumevanja kroz parafraze."
    )
    table.add_row(
        "Stochastic Parrot Index (SPI)", 
        f"{metrics['stochastic_parrot_index']:.2f}",
        "Ukupni indeks semantičkog utemeljenja modela (Groundedness)."
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
        Text(f"Model klasifikacija: {report['classification']}", style=cls_style, justify="center"),
        title="Konačni Zaključak Benchmark-a",
        border_style="magenta"
    ))
    
    # Display Semantic Drift Analysis if available
    drift_trajs = report.get("drift_trajectories", {})
    if drift_trajs:
        console.print("\n[bold magenta]📈 Analiza Semantičkog Drifta u Latentnom Prostoru[/]")
        from canyon.metrics import SemanticDriftProbe
        for test_id, trajs in drift_trajs.items():
            for traj_info in trajs:
                from_s = traj_info["from_step"]
                to_s = traj_info["to_step"]
                traj_data = traj_info["trajectory"]
                
                graph = SemanticDriftProbe.generate_ascii_graph(traj_data)
                console.print(f"\n[yellow]Test ID: {test_id}[/] (Korak {from_s + 1} ➔ Korak {to_s + 1} Kosinusna Sličnost po Slojevima):")
                console.print(graph)
                
    console.print("\n[bold cyan]Detaljni logovi testiranja:[/] ")
    log_table = Table(border_style="dim", box=None)
    log_table.add_column("Suite", style="dim")
    log_table.add_column("Test", style="bold white")
    log_table.add_column("Prompt", style="italic")
    log_table.add_column("Izlaz modela", style="green")
    
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
    """Izlistava sve dostupne benchmark test suite-ove."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suites_dir = os.path.join(base_dir, "suites")
    
    if not os.path.exists(suites_dir):
        rprint("[bold red]Greška: Suite folder ne postoji.[/]")
        return
        
    table = Table(title="Dostupni CANYON Test Suite-ovi", border_style="cyan")
    table.add_column("Fajl", style="yellow")
    table.add_column("Broj testova", style="green", justify="right")
    
    import json
    for f in os.listdir(suites_dir):
        if f.endswith(".json"):
            with open(os.path.join(suites_dir, f), "r", encoding="utf-8") as file:
                data = json.load(file)
                table.add_row(f, str(len(data)))
                
    console.print(table)

@cli.command()
@click.option("--layer", default=12, help="Sloj modela koji se proverava (Linear Probe).")
@click.option("--config", default="config.example.yaml", help="Putanja do konfiguracionog fajla.")
def probe(layer, config):
    """Pokreće linear classification probe nad skrivenim stanjima lokalnog modela."""
    rprint(Panel(
        Text(f"Linear Probing nad slojem {layer}", style="bold magenta", justify="center"),
        border_style="cyan"
    ))
    
    if not os.path.exists(config):
        rprint(f"[bold red]Greška:[/] Konfiguracioni fajl '{config}' ne postoji.")
        sys.exit(1)
        
    engine = CanyonEngine(config)
    
    positives = [
        "Loptica je pala na zemlju nakon što sam je ispustio.",
        "Kamen je potonuo na dno reke.",
        "Osoba je ušla u automobil i pokrenula motor."
    ]
    negatives = [
        "Loptica je odletela u svemir nakon što sam je ispustio na zemlju.",
        "Kamen je plutao u vazduhu iznad reke sam od sebe.",
        "Zgrada je počela da hoda niz ulicu tražeći hranu."
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Učitavanje lokalnog modela i ekstrakcija aktivacija..."),
        console=console
    ) as progress:
        progress.add_task("probing", total=None)
        try:
            provider = engine.get_local_provider()
            probe_result = provider.train_linear_probe(layer, positives, negatives)
        except Exception as e:
            rprint(f"\n[bold red]Greška tokom linear probing-a (Potreban je lokalni GPU/HF model):[/] {str(e)}")
            return
            
    rprint("\n[bold green]✅ Trening linear probe-a završen![/]")
    rprint(f"Bias na sloju {layer}: {probe_result['bias']:.4f}")
    rprint(f"Ekstraktovano težina (weights): {len(probe_result['weights'])}")
    rprint("[yellow]Linear probe je spreman za detekciju fizičke mogućnosti unutar latentnog prostora modela.[/]")

if __name__ == "__main__":
    cli()

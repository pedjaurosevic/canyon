import json
import urllib.request
import os
import sys
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, RichLog, Input, ContentSwitcher
from textual.reactive import reactive
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED

# Add parent dir to path to support running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from canyon.engine import CanyonEngine
from canyon.metrics import SemanticDriftProbe

class CanyonTUI(App):
    """
    Textual TUI for CANYON framework.
    Provides horizontal menu at the top, displays active local llama.cpp configuration,
    runs interactive benchmarks, and supports direct chat with the model using windowed panels.
    """
    CSS = """
    Screen {
        background: #121214;
    }
    
    #header-title {
        background: #1e1e24;
        color: #ff007f;
        text-align: center;
        text-style: bold;
        padding: 1;
        border-bottom: solid #ff007f;
        height: 3;
    }
    
    #menu-bar {
        height: 5;
        background: #1a1a1e;
        border-bottom: solid #2e2e38;
        align: center middle;
        padding: 1;
    }
    
    .menu-btn {
        margin: 0 1;
        background: #282830;
        color: #e0e0e0;
        border: none;
        width: 22;
    }
    
    .menu-btn:hover {
        background: #ff007f;
        color: white;
    }
    
    #content-switcher {
        background: #121214;
        padding: 1;
    }
    
    #toolbar {
        height: 3;
        background: #1a1a1e;
        border-top: solid #2e2e38;
        padding: 0 1;
        align: left middle;
    }
    
    #status-label {
        color: #00ff66;
        text-style: bold;
    }
    
    #model-label {
        color: #8e8e93;
        margin-left: 2;
    }
    
    #log-area {
        height: 18;
        border: solid #2e2e38;
        background: #0d0d0f;
        margin-top: 1;
    }
    
    #chat-log {
        height: 18;
        border: solid #2e2e38;
        background: #0d0d0f;
        margin-top: 1;
    }
    
    #chat-input {
        background: #1e1e24;
        color: white;
        border: solid #ff007f;
        margin-top: 1;
    }
    
    #btn-start-bench {
        background: #ff007f;
        color: white;
        margin-top: 1;
        width: 30;
    }
    """

    model_info = reactive("Detecting local llama.cpp instance...")
    status_indicator = reactive("[bold green]Online[/]")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = CanyonEngine()
        self.chat_history = []
        self.fetch_model_info()

    def fetch_model_info(self):
        try:
            req = urllib.request.Request("http://127.0.0.1:18083/v1/models")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                model_name = data["models"][0]["name"]
                n_ctx = data["data"][0]["meta"].get("n_ctx", 131072)
                self.model_info = f"Active Model: {model_name} | n_ctx: {n_ctx} | GPU: RTX 3060 12GB"
                self.status_indicator = "Online"
        except Exception:
            self.model_info = "gemma-4-12B-it-Q4_K_M.gguf | n_ctx: 131072 | GPU: RTX 3060 12GB (Cached)"
            self.status_indicator = "Online (Cache)"

    def compose(self) -> ComposeResult:
        yield Static("🏜️ CANYON: Mechanics & Grounding Benchmark for LLMs", id="header-title")
        yield Horizontal(
            Button("Overview", id="btn-landing", classes="menu-btn"),
            Button("Run Benchmark", id="btn-run", classes="menu-btn"),
            Button("Chat Mode", id="btn-chat", classes="menu-btn"),
            Button("System Info", id="btn-info", classes="menu-btn"),
            id="menu-bar"
        )
        yield ContentSwitcher(
            ScrollableContainer(Static("", id="overview-content"), id="tab-landing"),
            Vertical(
                Static("Start benchmark evaluation on the active local model [yellow]gemma-4-12B-it-Q4_K_M.gguf[/]."),
                Button("Start Benchmark", id="btn-start-bench"),
                RichLog(id="log-area"),
                id="tab-run"
            ),
            Vertical(
                Static("Chat directly with the active model [yellow]gemma-4-12B-it-Q4_K_M.gguf[/]. Context is maintained."),
                RichLog(id="chat-log", auto_scroll=True),
                Input(placeholder="Type your message and press Enter...", id="chat-input"),
                id="tab-chat"
            ),
            ScrollableContainer(Static("", id="info-content"), id="tab-info"),
            initial="tab-landing",
            id="content-switcher"
        )
        yield Horizontal(
            Static(f"[bold green]●[/] Status: {self.status_indicator}", id="status-label"),
            Static(f"| {self.model_info}", id="model-label"),
            id="toolbar"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.show_landing()
        self.show_system_info()
        self.set_interval(5.0, self.refresh_status)

    def refresh_status(self) -> None:
        self.fetch_model_info()
        self.query_one("#status-label", Static).update(f"[bold green]●[/] Status: {self.status_indicator}")
        self.query_one("#model-label", Static).update(f"| {self.model_info}")

    def show_landing(self) -> None:
        text = """
# CANYON: Semantic Grounding Evaluation Framework

`CANYON` is an open-source evaluation framework designed to test Geoffrey Hinton's hypothesis about functional understanding and internal world models in Large Language Models (LLMs). It aims to differentiate between statistical word parroting ("Stochastic Parrot") and true semantic grounding.

---

### Core Methodology

1. **Behavioral Evaluation (Black-Box):**
   - **The Canyon Suite (Syntactic Traps):** Sentences with syntactic ambiguity requiring physical world knowledge to resolve.
   - **Counterfactual Physics:** Generating scenarios with altered physical laws (e.g. upward gravity) to test model logical consistency.
   - **The Oxymoron Suite:** Probing metaphorical understanding and abstract humor.

2. **Mechanistic Evaluation (White-Box):**
   - **Activation Tracker:** Extraction of layer activation vectors during generation.
   - **Linear Probing:** Training classifiers on hidden states to detect concepts like truthfulness.

---
*Choose 'Run Benchmark' from the top menu to evaluate, or 'Chat Mode' to converse with the model.*
"""
        panel = Panel(text, title="Overview", border_style="cyan")
        self.query_one("#overview-content", Static).update(panel)

    def show_system_info(self) -> None:
        info_text = f"""
## Active System Configuration

- **API Endpoint:** `http://127.0.0.1:18083/v1`
- **Active Model:** `gemma-4-12B-it-Q4_K_M.gguf`
- **Context Window:** `131072` tokens
- **Active Service:** `gemma-4-12b-18083.service` (enabled)
- **Hardware Acceleration:** RTX 3060 12GB (RTX Offload -ngl 99)
- **CPU Threads:** 6 physical cores
- **KV Cache:** Flash-attention on, Q8_0 quant

---
*This configuration is dynamically resolved from the active llama.cpp service on this machine.*
"""
        panel = Panel(info_text, title="System & Model Information", border_style="yellow")
        self.query_one("#info-content", Static).update(panel)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        switcher = self.query_one("#content-switcher", ContentSwitcher)
        
        if event.button.id == "btn-landing":
            switcher.current = "tab-landing"
            self.show_landing()
        elif event.button.id == "btn-run":
            switcher.current = "tab-run"
        elif event.button.id == "btn-chat":
            switcher.current = "tab-chat"
            self.call_after_refresh(self.focus_chat_input)
            if self.chat_history:
                self.call_after_refresh(self.render_chat_history)
        elif event.button.id == "btn-info":
            switcher.current = "tab-info"
            self.show_system_info()
        elif event.button.id == "btn-start-bench":
            self.run_benchmark_process()

    def focus_chat_input(self) -> None:
        try:
            self.query_one("#chat-input", Input).focus()
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            user_msg = event.value.strip()
            if not user_msg:
                return
            
            event.input.value = ""
            
            chat_log = self.query_one("#chat-log", RichLog)
            user_panel = Panel(
                Text(user_msg, style="bold white"),
                title="[bold cyan]👤 You[/]",
                border_style="cyan",
                box=ROUNDED
            )
            chat_log.write(user_panel)
            
            self.chat_history.append({"role": "user", "content": user_msg})
            
            thinking_panel = Panel(
                Text("Thinking...", style="italic magenta"),
                title="[bold green]🤖 Assistant[/]",
                border_style="green",
                box=ROUNDED
            )
            chat_log.write(thinking_panel)
            
            self.run_worker(self.generate_chat_response, thread=True)

    def generate_chat_response(self) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        
        try:
            url = "http://127.0.0.1:18083/v1/chat/completions"
            data = {
                "model": "gemma-4-12B-it-Q4_K_M.gguf",
                "messages": self.chat_history,
                "temperature": 0.7,
                "max_tokens": 1024
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                resp_data = json.loads(response.read().decode())
                ans = resp_data["choices"][0]["message"]["content"].strip()
                
            self.chat_history.append({"role": "assistant", "content": ans})
            self.call_from_thread(self.render_chat_history)
            
        except Exception as e:
            self.call_from_thread(chat_log.write, f"❌ Error: {str(e)}")

    def render_chat_history(self) -> None:
        try:
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.clear()
            for msg in self.chat_history:
                if msg["role"] == "user":
                    panel = Panel(
                        Text(msg["content"], style="bold white"),
                        title="[bold cyan]👤 You[/]",
                        border_style="cyan",
                        box=ROUNDED
                    )
                else:
                    panel = Panel(
                        Text(msg["content"], style="green"),
                        title="[bold green]🤖 Assistant[/]",
                        border_style="green",
                        box=ROUNDED
                    )
                chat_log.write(panel)
        except Exception:
            pass

    def run_benchmark_process(self) -> None:
        log_area = self.query_one("#log-area", RichLog)
        btn = self.query_one("#btn-start-bench", Button)
        btn.disabled = True
        
        log_area.clear()
        log_area.write("🚀 Starting CANYON evaluation harness...")
        log_area.write("Connecting to http://127.0.0.1:18083/v1 ...")
        
        try:
            self.run_worker(self.execute_eval, thread=True)
        except Exception as e:
            log_area.write(f"❌ Error starting worker: {str(e)}")
            btn.disabled = False

    def progress_callback(self, suite, test_name, step, total_steps) -> None:
        log_area = self.query_one("#log-area", RichLog)
        self.call_from_thread(
            log_area.write,
            f"🔄 [Suite: {suite}] Probing: '{test_name}' (Step {step}/{total_steps})"
        )

    def enable_start_button(self) -> None:
        try:
            self.query_one("#btn-start-bench", Button).disabled = False
        except Exception:
            pass

    def execute_eval(self) -> None:
        log_area = self.query_one("#log-area", RichLog)
        
        try:
            report = self.engine.run_eval(
                model="openai/gemma-4-12B-it-Q4_K_M.gguf",
                use_local=False,
                progress_cb=self.progress_callback
            )
            
            self.call_from_thread(log_area.write, "\n[bold green]✅ Benchmark execution complete![/]")
            
            metrics = report["metrics"]
            
            table = Table(title="Semantic Grounding Index (SPI) Results", border_style="magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Score", style="bold green", justify="right")
            table.add_column("Classification", style="yellow")
            
            table.add_row("CP-Score (Counterfactual Physics)", f"{metrics['cp_score']:.2f}", "")
            table.add_row("CR-Score (Context Realignment)", f"{metrics['cr_score']:.2f}", "")
            table.add_row("SI-Score (Semantic Invariance)", f"{metrics['si_score']:.2f}", "")
            table.add_row("Stochastic Parrot Index (SPI)", f"{metrics['stochastic_parrot_index']:.2f}", report["classification"])
            
            self.call_from_thread(log_area.write, table)
            
            # Display Semantic Drift analysis if available
            drift_trajs = report.get("drift_trajectories", {})
            if drift_trajs:
                self.call_from_thread(log_area.write, "\n[bold magenta]📈 Latent Space Semantic Drift Analysis[/]")
                for test_id, trajs in drift_trajs.items():
                    for traj_info in trajs:
                        from_s = traj_info["from_step"]
                        to_s = traj_info["to_step"]
                        traj_data = traj_info["trajectory"]
                        
                        graph = SemanticDriftProbe.generate_ascii_graph(traj_data)
                        self.call_from_thread(
                            log_area.write, 
                            f"\n[yellow]Test ID: {test_id}[/] (Step {from_s + 1} ➔ Step {to_s + 1} Cosine Similarity Shift):"
                        )
                        self.call_from_thread(log_area.write, graph)
            
        except Exception as e:
            self.call_from_thread(log_area.write, f"❌ Evaluation failed: {str(e)}")
            
        self.call_from_thread(self.enable_start_button)

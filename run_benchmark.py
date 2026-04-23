from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(
    dataset: str = "C:\\assignments-main\\Lab 16\\Day16-HuynhThaiBao-2A202600373\\data\\hotpot_extra.json",
    out_dir: str = "outputs/sample_run",
    reflexion_attempts: int = 2,
    mode: str = "ollama",
    react_model: str = "gemma3:1b",
    reflexion_model: str = "gemma3:4b",
) -> None:
    examples = load_dataset(dataset)
    react = ReActAgent(mode=mode, model=react_model or None)
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts, mode=mode, model=reflexion_model or None)
    react_records = [react.run(example) for example in examples]
    reflexion_records = [reflexion.run(example) for example in examples]
    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    report = build_report(all_records, dataset_name=Path(dataset).name, mode=mode)
    json_path, md_path = save_report(report, out_path)
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()

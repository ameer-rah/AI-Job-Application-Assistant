from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from job_assistant.claude_service import ClaudeService
from job_assistant.parser import extract_text

app = typer.Typer(
    name="job-assistant",
    help="AI-powered job application assistant. Tailor your resume, write cover letters, and check ATS compatibility.",
    add_completion=False,
)
console = Console()


def _load_jd(jd_file: Optional[Path], jd_text: Optional[str]) -> str:
    if jd_text:
        return jd_text.strip()
    if jd_file:
        return jd_file.read_text(encoding="utf-8").strip()
    raise typer.BadParameter("Provide either --jd (file path) or --jd-text (inline text).")


def _get_service(verbose: bool) -> ClaudeService:
    try:
        return ClaudeService(verbose=verbose)
    except EnvironmentError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def _parse_resume(resume: Path) -> str:
    try:
        return extract_text(str(resume))
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def tailor(
    resume: Path = typer.Option(..., "--resume", "-r", help="Path to your resume (.pdf or .docx)"),
    jd: Optional[Path] = typer.Option(None, "--jd", help="Path to job description .txt file"),
    jd_text: Optional[str] = typer.Option(None, "--jd-text", help="Job description as inline text"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show Claude token usage"),
):
    """Rewrite resume bullets to match a job description."""
    jd_content = _load_jd(jd, jd_text)
    resume_text = _parse_resume(resume)
    service = _get_service(verbose)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Tailoring resume with Claude...", total=None)
        result = service.tailor_resume(resume_text, jd_content)

    # Bullet revisions table
    table = Table(title="Tailored Bullets", show_lines=True, header_style="bold cyan")
    table.add_column("Original", style="dim", ratio=4)
    table.add_column("Revised", ratio=4)
    table.add_column("Why", style="italic", ratio=3)

    for item in result.get("tailored_bullets", []):
        table.add_row(item.get("original", ""), item.get("revised", ""), item.get("reason", ""))

    console.print(table)

    # Keywords
    added = result.get("keywords_added", [])
    missing = result.get("keywords_missing", [])
    if added:
        console.print(f"\n[bold green]Keywords added:[/bold green] {', '.join(added)}")
    if missing:
        console.print(f"[bold yellow]Keywords to add manually:[/bold yellow] {', '.join(missing)}")

    # Summary
    summary = result.get("summary_suggestion", "")
    if summary:
        console.print(Panel(summary, title="Suggested Summary", border_style="green"))


@app.command()
def cover(
    resume: Path = typer.Option(..., "--resume", "-r", help="Path to your resume (.pdf or .docx)"),
    jd: Optional[Path] = typer.Option(None, "--jd", help="Path to job description .txt file"),
    jd_text: Optional[str] = typer.Option(None, "--jd-text", help="Job description as inline text"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save cover letter to this file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show Claude token usage"),
):
    """Generate a personalized cover letter."""
    jd_content = _load_jd(jd, jd_text)
    resume_text = _parse_resume(resume)
    service = _get_service(verbose)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Generating cover letter with Claude...", total=None)
        result = service.generate_cover_letter(resume_text, jd_content)

    letter = result.get("cover_letter", "")
    selling_points = result.get("key_selling_points", [])

    console.print(Panel(letter, title="Cover Letter", border_style="cyan", padding=(1, 2)))

    if selling_points:
        console.print("\n[bold cyan]Key selling points:[/bold cyan]")
        for point in selling_points:
            console.print(f"  • {point}")

    if output:
        output.write_text(letter, encoding="utf-8")
        console.print(f"\n[bold green]Saved to:[/bold green] {output}")


@app.command()
def ats(
    resume: Path = typer.Option(..., "--resume", "-r", help="Path to your resume (.pdf or .docx)"),
    jd: Optional[Path] = typer.Option(None, "--jd", help="Path to job description .txt file"),
    jd_text: Optional[str] = typer.Option(None, "--jd-text", help="Job description as inline text"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show Claude token usage"),
):
    """Estimate ATS compatibility score for your resume against a job description."""
    jd_content = _load_jd(jd, jd_text)
    resume_text = _parse_resume(resume)
    service = _get_service(verbose)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Calculating ATS score with Claude...", total=None)
        result = service.estimate_ats_score(resume_text, jd_content)

    score = result.get("score", 0)
    color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
    score_text = Text(f"{score}/100", style=f"bold {color}")
    console.print(Panel(score_text, title="ATS Compatibility Score", border_style=color, width=30))

    matched = result.get("matched_keywords", [])
    missing_critical = result.get("missing_critical_keywords", [])
    missing_preferred = result.get("missing_preferred_keywords", [])
    formatting = result.get("formatting_issues", [])
    recs = result.get("recommendations", [])

    if matched:
        console.print(f"\n[bold green]Matched keywords:[/bold green] {', '.join(matched)}")
    if missing_critical:
        console.print(f"[bold red]Missing critical keywords:[/bold red] {', '.join(missing_critical)}")
    if missing_preferred:
        console.print(f"[bold yellow]Missing preferred keywords:[/bold yellow] {', '.join(missing_preferred)}")
    if formatting:
        console.print("\n[bold red]Formatting issues:[/bold red]")
        for issue in formatting:
            console.print(f"  • {issue}")
    if recs:
        console.print("\n[bold cyan]Recommendations:[/bold cyan]")
        for rec in recs:
            console.print(f"  • {rec}")

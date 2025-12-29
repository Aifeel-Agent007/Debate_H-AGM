"""CLI 인터페이스"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from debate_evaluator import __version__
from debate_evaluator.client import DebateEvaluatorClient
from debate_evaluator.config import Settings
from debate_evaluator.evaluators.base import EvaluatorFactory
from debate_evaluator.formatters.markdown import MarkdownFormatter
from debate_evaluator.models.base import EvaluationMode
from debate_evaluator.utils.file_io import read_transcript, write_output

# 평가자 모듈 import (등록을 위해)
from debate_evaluator.evaluators import dqi, aaf, hybrid, afra  # noqa: F401

app = typer.Typer(
    name="debate-eval",
    help="토론 담론 품질 평가 시스템 - 4가지 방법론 지원",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    """버전 출력 콜백"""
    if value:
        console.print(f"debate-evaluator v{__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        None,
        "--version", "-V",
        callback=version_callback,
        is_eager=True,
        help="버전 정보 출력"
    ),
):
    """Debate Evaluator - 토론 담론 품질 평가 시스템"""
    pass


@app.command()
def evaluate(
    input_file: Path = typer.Argument(
        ...,
        help="토론 스크립트 파일 경로",
        exists=True,
        readable=True,
    ),
    mode: str = typer.Option(
        "dqi",
        "--mode", "-m",
        help="평가 모드 (dqi, aaf, dqi-aaf, afra)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="출력 파일 경로 (미지정 시 터미널 출력)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="OpenAI 모델 (기본: gpt-4o)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="상세 출력 모드",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="LLM 원본 응답 출력",
    ),
):
    """토론 스크립트를 지정된 모드로 평가합니다.

    예시:
        debate-eval transcript.txt -m dqi
        debate-eval transcript.txt -m aaf -o result.md
    """
    try:
        # 평가 모드 파싱
        eval_mode = EvaluationMode.from_string(mode)
    except ValueError as e:
        console.print(f"[red]오류:[/] {e}")
        raise typer.Exit(1)

    # 설정 로드
    try:
        settings = Settings()
        if model:
            settings.openai_model = model
    except Exception as e:
        console.print(f"[red]설정 오류:[/] {e}")
        console.print("[yellow]힌트:[/] .env 파일에 DEBATE_EVAL_OPENAI_API_KEY를 설정하세요.")
        raise typer.Exit(1)

    # 스크립트 읽기
    try:
        transcript = read_transcript(input_file)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]파일 오류:[/] {e}")
        raise typer.Exit(1)

    if verbose:
        console.print(f"[blue]평가 모드:[/] {eval_mode.value}")
        console.print(f"[blue]입력 파일:[/] {input_file}")
        console.print(f"[blue]모델:[/] {settings.openai_model}")
        console.print(f"[blue]스크립트 길이:[/] {len(transcript)} 자")
        console.print()

    # 평가 실행
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"{eval_mode.value.upper()} 평가 중...", total=None)

        try:
            client = DebateEvaluatorClient(settings)
            evaluator = EvaluatorFactory.create(eval_mode, client)
            result = evaluator.evaluate(transcript)
        except Exception as e:
            progress.stop()
            console.print(f"[red]평가 오류:[/] {e}")
            raise typer.Exit(1)

        progress.update(task, completed=True)

    # 결과 출력
    if raw:
        formatted_output = result.raw_response
    else:
        formatter = MarkdownFormatter()
        formatted_output = formatter.format(result)

    if output:
        write_output(output, formatted_output)
        console.print(f"[green]결과 저장:[/] {output}")
    else:
        console.print()
        console.print(Panel(
            formatted_output,
            title=f"[bold]{eval_mode.value.upper()} 평가 결과[/]",
            border_style="blue",
        ))


@app.command("all")
def evaluate_all(
    input_file: Path = typer.Argument(
        ...,
        help="토론 스크립트 파일 경로",
        exists=True,
        readable=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="출력 파일 경로 (미지정 시 results/{파일명}_result.md)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="OpenAI 모델 (기본: gpt-4o)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="상세 출력 모드",
    ),
):
    """4가지 평가 방법론으로 한꺼번에 평가합니다.

    DQI, AAF, DQI-AAF, AFRA 모든 방법론을 순차적으로 실행하고
    통합 리포트를 생성합니다.

    -o 옵션 미지정 시 results/{입력파일명}_result.md로 자동 저장됩니다.

    예시:
        debate-eval all transcript.txt
        debate-eval all transcript.txt -o custom_report.md
    """
    # 설정 로드
    try:
        settings = Settings()
        if model:
            settings.openai_model = model
    except Exception as e:
        console.print(f"[red]설정 오류:[/] {e}")
        console.print("[yellow]힌트:[/] .env 파일에 DEBATE_EVAL_OPENAI_API_KEY를 설정하세요.")
        raise typer.Exit(1)

    # 스크립트 읽기
    try:
        transcript = read_transcript(input_file)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]파일 오류:[/] {e}")
        raise typer.Exit(1)

    if verbose:
        console.print(f"[blue]평가 모드:[/] 전체 (DQI, AAF, DQI-AAF, AFRA)")
        console.print(f"[blue]입력 파일:[/] {input_file}")
        console.print(f"[blue]모델:[/] {settings.openai_model}")
        console.print(f"[blue]스크립트 길이:[/] {len(transcript)} 자")
        console.print()

    # 모든 평가 모드 실행
    modes = [EvaluationMode.DQI, EvaluationMode.AAF, EvaluationMode.HYBRID, EvaluationMode.AFRA]
    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        for eval_mode in modes:
            task = progress.add_task(f"{eval_mode.value.upper()} 평가 중...", total=None)

            try:
                client = DebateEvaluatorClient(settings)
                evaluator = EvaluatorFactory.create(eval_mode, client)
                result = evaluator.evaluate(transcript)
                results[eval_mode] = result
            except Exception as e:
                progress.stop()
                console.print(f"[red]{eval_mode.value.upper()} 평가 오류:[/] {e}")
                raise typer.Exit(1)

            progress.update(task, completed=True)
            progress.remove_task(task)

    # 통합 결과 포매팅
    formatter = MarkdownFormatter()
    formatted_output = formatter.format_all(results)

    # 출력 파일 경로 결정
    if output is None:
        # results 디렉토리 생성
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        # 입력 파일명에서 확장자 제거하고 _result.md 추가
        output = results_dir / f"{input_file.stem}_result.md"

    write_output(output, formatted_output)
    console.print(f"[green]통합 결과 저장:[/] {output}")


@app.command("modes")
def list_modes():
    """사용 가능한 평가 모드를 표시합니다."""
    table = Table(title="사용 가능한 평가 모드")

    table.add_column("모드", style="cyan")
    table.add_column("설명")
    table.add_column("점수 체계")

    mode_info = [
        ("dqi", "Discourse Quality Index - 담론 품질 지수", "7개 범주, 0-3점"),
        ("aaf", "Argumentation, Authority, Flow", "3개 기준, 1-5점"),
        ("dqi-aaf", "DQI-AAF 하이브리드 모델", "논증 노드별 0-18점"),
        ("afra", "Rhetorical Analysis - 수사학적 분석", "10개 기준, 0-10점"),
    ]

    for mode, desc, scoring in mode_info:
        table.add_row(mode, desc, scoring)

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]사용 예: debate-eval transcript.txt -m dqi[/]")


@app.command("version")
def show_version():
    """버전 정보를 표시합니다."""
    console.print(f"[bold]debate-evaluator[/] v{__version__}")
    console.print()
    console.print("토론 담론 품질 평가 시스템")
    console.print("OpenAI GPT-4o 기반 4가지 평가 방법론 지원")


def main():
    """CLI 진입점"""
    app()


if __name__ == "__main__":
    main()

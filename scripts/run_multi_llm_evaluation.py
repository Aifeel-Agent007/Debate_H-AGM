"""Evaluate all debates from multiple LLMs using all 5 LLMs for evaluation."""

import asyncio
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.convert_debate_for_evaluation import convert_debate_to_transcript

# Supported LLM providers for evaluation
EVAL_LLM_PROVIDERS = ["gpt", "grok", "gemini", "claude", "qwen"]

# Evaluation modes
EVALUATION_MODES = ["dqi", "aaf", "dqi-aaf", "afra", "all"]

# LLM display names
LLM_DISPLAY_NAMES = {
    "gpt": "GPT (OpenAI)",
    "grok": "Grok (Groq)",
    "gemini": "Gemini (Google)",
    "claude": "Claude (Anthropic)",
    "qwen": "Qwen (Alibaba)"
}


def find_debate_files(debate_dir: Path, llm_provider: str) -> List[Path]:
    """Find all debate JSON files for a specific LLM.
    
    Args:
        debate_dir: Base debate directory
        llm_provider: LLM provider name
        
    Returns:
        List of debate JSON file paths
    """
    llm_dir = debate_dir / llm_provider
    if not llm_dir.exists():
        return []
    
    json_files = sorted(llm_dir.glob("*.json"))
    return json_files


def evaluate_debate_file(
    debate_file: Path,
    eval_llm_provider: str,
    evaluation_mode: str,
    output_dir: Path,
    evaluator_dir: Path,
    debate_index: int,
    total_debates: int
) -> Dict[str, Any]:
    """Evaluate a single debate file using a specific LLM.
    
    Args:
        debate_file: Path to debate JSON file
        eval_llm_provider: LLM provider for evaluation
        evaluation_mode: Evaluation mode (dqi, aaf, dqi-aaf, afra, all)
        output_dir: Output directory for results
        evaluator_dir: Debate evaluator directory
        debate_index: Current debate index
        total_debates: Total number of debates
        
    Returns:
        Dictionary with evaluation result information
    """
    print(f"\n[{eval_llm_provider.upper()}] [{evaluation_mode.upper()}] "
          f"평가 {debate_index}/{total_debates}: {debate_file.name}")
    
    try:
        # Convert debate to transcript
        transcript_file = output_dir / f"transcript_{debate_index:04d}_{debate_file.stem}.txt"
        
        try:
            transcript = convert_debate_to_transcript(debate_file)
            transcript_file.write_text(transcript, encoding='utf-8')
        except Exception as e:
            print(f"  ❌ 변환 실패: {e}")
            return {
                "debate_file": str(debate_file),
                "eval_llm": eval_llm_provider,
                "evaluation_mode": evaluation_mode,
                "success": False,
                "error": f"Conversion error: {e}",
                "output_file": None
            }
        
        # Set environment variable for evaluation LLM
        import os
        original_eval_provider = os.getenv("EVAL_LLM_PROVIDER")
        os.environ["EVAL_LLM_PROVIDER"] = eval_llm_provider
        
        try:
            # Determine output file name
            if evaluation_mode == "all":
                output_file = output_dir / f"evaluation_{debate_index:04d}_{debate_file.stem}_all.md"
                cmd = [
                    "uv", "run", "debate-eval", "all",
                    str(transcript_file.resolve()),
                    "-o", str(output_file.resolve())
                ]
            else:
                output_file = output_dir / f"evaluation_{debate_index:04d}_{debate_file.stem}_{evaluation_mode}.md"
                cmd = [
                    "uv", "run", "debate-eval",
                    str(transcript_file.resolve()),
                    "-m", evaluation_mode,
                    "-o", str(output_file.resolve())
                ]
            
            # Run evaluation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(evaluator_dir),
                timeout=300.0  # 5 minute timeout per evaluation
            )
            
            if result.returncode == 0:
                print(f"  ✅ 완료: {output_file.name}")
                return {
                    "debate_file": str(debate_file),
                    "eval_llm": eval_llm_provider,
                    "evaluation_mode": evaluation_mode,
                    "success": True,
                    "error": None,
                    "output_file": str(output_file),
                    "transcript_file": str(transcript_file)
                }
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                print(f"  ❌ 실패: {error_msg}")
                return {
                    "debate_file": str(debate_file),
                    "eval_llm": eval_llm_provider,
                    "evaluation_mode": evaluation_mode,
                    "success": False,
                    "error": error_msg,
                    "output_file": None
                }
        
        finally:
            # Restore original environment variable
            if original_eval_provider:
                os.environ["EVAL_LLM_PROVIDER"] = original_eval_provider
            else:
                os.environ.pop("EVAL_LLM_PROVIDER", None)
    
    except subprocess.TimeoutExpired:
        print(f"  ❌ 타임아웃 (5분 초과)")
        return {
            "debate_file": str(debate_file),
            "eval_llm": eval_llm_provider,
            "evaluation_mode": evaluation_mode,
            "success": False,
            "error": "Timeout (5 minutes)",
            "output_file": None
        }
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return {
            "debate_file": str(debate_file),
            "eval_llm": eval_llm_provider,
            "evaluation_mode": evaluation_mode,
            "success": False,
            "error": str(e),
            "output_file": None
        }


def evaluate_all_debates(
    debate_dir: Path = Path("debate"),
    eval_llm_providers: List[str] = None,
    evaluation_mode: str = "all",
    debate_llm_providers: List[str] = None,
    output_base_dir: Path = Path("debate_results"),
    delay_between_evaluations: float = 2.0,
) -> None:
    """Evaluate all debates from multiple LLMs using multiple evaluation LLMs.
    
    Args:
        debate_dir: Base directory containing LLM-specific debate directories
        eval_llm_providers: LLM providers to use for evaluation (default: all 5)
        evaluation_mode: Evaluation mode (default: all)
        debate_llm_providers: Debate LLM providers to evaluate (default: all found)
        output_base_dir: Base output directory for results
        delay_between_evaluations: Delay between evaluations in seconds
    """
    if eval_llm_providers is None:
        eval_llm_providers = EVAL_LLM_PROVIDERS
    
    if debate_llm_providers is None:
        # Find all LLM directories
        debate_llm_providers = []
        if debate_dir.exists():
            for subdir in debate_dir.iterdir():
                if subdir.is_dir() and subdir.name in EVAL_LLM_PROVIDERS:
                    debate_llm_providers.append(subdir.name)
    
    if not debate_llm_providers:
        print(f"❌ 오류: 토론 결과를 찾을 수 없습니다. {debate_dir} 디렉토리를 확인하세요.")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 다중 LLM 토론 평가")
    print(f"{'='*80}")
    print(f"토론 디렉토리: {debate_dir}")
    print(f"토론 LLM: {', '.join([LLM_DISPLAY_NAMES.get(p, p) for p in debate_llm_providers])}")
    print(f"평가 LLM: {', '.join([LLM_DISPLAY_NAMES.get(p, p) for p in eval_llm_providers])}")
    print(f"평가 모드: {evaluation_mode}")
    print(f"출력 디렉토리: {output_base_dir}")
    print(f"{'='*80}\n")
    
    # Check evaluator directory
    evaluator_dir = Path("debate-evaluator-main")
    if not evaluator_dir.exists():
        print(f"❌ 오류: debate-evaluator-main 디렉토리를 찾을 수 없습니다.")
        return
    
    # Find all debate files
    all_debate_files: Dict[str, List[Path]] = {}
    total_debates = 0
    
    for debate_llm in debate_llm_providers:
        files = find_debate_files(debate_dir, debate_llm)
        all_debate_files[debate_llm] = files
        total_debates += len(files)
        print(f"📁 {debate_llm}: {len(files)}개 토론 파일 발견")
    
    if total_debates == 0:
        print(f"❌ 평가할 토론 파일이 없습니다.")
        return
    
    total_evaluations = total_debates * len(eval_llm_providers)
    print(f"\n총 토론 수: {total_debates}")
    print(f"총 평가 수: {total_evaluations} (토론 {total_debates}개 × 평가 LLM {len(eval_llm_providers)}개)")
    print()
    
    # Create output directories
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    # Results tracking
    all_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    # Structure: all_results[debate_llm][eval_llm] = [results]
    
    evaluation_count = 0
    
    # Evaluate each debate with each evaluation LLM
    for debate_llm in debate_llm_providers:
        debate_files = all_debate_files[debate_llm]
        all_results[debate_llm] = {}
        
        print(f"\n{'#'*80}")
        print(f"# 토론 LLM: {LLM_DISPLAY_NAMES.get(debate_llm, debate_llm)} ({len(debate_files)}개 토론)")
        print(f"{'#'*80}\n")
        
        for eval_llm in eval_llm_providers:
            all_results[debate_llm][eval_llm] = []
            
            print(f"\n{'='*80}")
            print(f"평가 LLM: {LLM_DISPLAY_NAMES.get(eval_llm, eval_llm)}")
            print(f"{'='*80}\n")
            
            # Create output directory for this combination
            output_dir = output_base_dir / debate_llm / eval_llm
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for idx, debate_file in enumerate(debate_files, 1):
                evaluation_count += 1
                
                result = evaluate_debate_file(
                    debate_file,
                    eval_llm,
                    evaluation_mode,
                    output_dir,
                    evaluator_dir,
                    idx,
                    len(debate_files)
                )
                
                all_results[debate_llm][eval_llm].append(result)
                
                # Progress update
                print(f"  진행률: {evaluation_count}/{total_evaluations} "
                      f"({evaluation_count*100//total_evaluations}%)")
                
                # Delay between evaluations
                if evaluation_count < total_evaluations and delay_between_evaluations > 0:
                    import time
                    time.sleep(delay_between_evaluations)
    
    # Save summary
    summary_file = output_base_dir / "evaluation_multi_llm_summary.json"
    summary = {
        "timestamp": datetime.now().isoformat(),
        "debate_dir": str(debate_dir),
        "debate_llm_providers": debate_llm_providers,
        "eval_llm_providers": eval_llm_providers,
        "evaluation_mode": evaluation_mode,
        "total_debates": total_debates,
        "total_evaluations": total_evaluations,
        "statistics": {
            debate_llm: {
                eval_llm: {
                    "total": len(results),
                    "success": sum(1 for r in results if r["success"]),
                    "failed": sum(1 for r in results if not r["success"]),
                }
                for eval_llm, results in eval_results.items()
            }
            for debate_llm, eval_results in all_results.items()
        },
        "results": all_results
    }
    
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f"🎉 다중 LLM 평가 완료")
    print(f"{'='*80}")
    print(f"총 토론 수: {total_debates}")
    print(f"총 평가 수: {total_evaluations}")
    print(f"\n통계:")
    for debate_llm, eval_results in all_results.items():
        print(f"\n  토론 LLM: {LLM_DISPLAY_NAMES.get(debate_llm, debate_llm)}")
        for eval_llm, results in eval_results.items():
            success = sum(1 for r in results if r["success"])
            failed = sum(1 for r in results if not r["success"])
            print(f"    평가 LLM {LLM_DISPLAY_NAMES.get(eval_llm, eval_llm)}: "
                  f"성공 {success}, 실패 {failed}")
    print(f"\n전체 요약: {summary_file}")
    print(f"평가 결과: {output_base_dir}/")
    print(f"{'='*80}\n")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Evaluate all debates from multiple LLMs using all 5 LLMs for evaluation"
    )
    parser.add_argument(
        "--debate-dir",
        type=Path,
        default=Path("debate"),
        help="Base directory containing LLM-specific debate directories (default: debate)"
    )
    parser.add_argument(
        "--eval-llm-providers",
        type=str,
        nargs="+",
        choices=EVAL_LLM_PROVIDERS,
        default=EVAL_LLM_PROVIDERS,
        help=f"LLM providers for evaluation (default: all: {', '.join(EVAL_LLM_PROVIDERS)})"
    )
    parser.add_argument(
        "--debate-llm-providers",
        type=str,
        nargs="+",
        choices=EVAL_LLM_PROVIDERS,
        default=None,
        help="Debate LLM providers to evaluate (default: all found in debate directory)"
    )
    parser.add_argument(
        "--evaluation-mode",
        type=str,
        choices=EVALUATION_MODES,
        default="all",
        help="Evaluation mode (default: all)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("debate_results"),
        help="Output directory for results (default: debate_results)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between evaluations (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    evaluate_all_debates(
        debate_dir=args.debate_dir,
        eval_llm_providers=args.eval_llm_providers,
        evaluation_mode=args.evaluation_mode,
        debate_llm_providers=args.debate_llm_providers,
        output_base_dir=args.output_dir,
        delay_between_evaluations=args.delay,
    )


if __name__ == "__main__":
    main()


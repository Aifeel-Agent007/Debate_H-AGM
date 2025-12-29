"""Run batch debates and automatically evaluate all results."""

import asyncio
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.run_batch_debates import run_batch_debates, load_topics


async def run_batch_debates_with_evaluation(
    topic_file: Path,
    moderator_url: str = "http://localhost:10000",
    delay_between_debates: float = 5.0,
    evaluation_mode: str = "all",
    start_from: int = 1,
    evaluate_after_all: bool = True
):
    """Run batch debates and optionally evaluate results.
    
    Args:
        topic_file: Path to topic file
        moderator_url: Moderator server URL
        delay_between_debates: Delay between debates in seconds
        evaluation_mode: Evaluation mode (dqi, aaf, dqi-aaf, afra, all)
        start_from: Start from this topic index
        evaluate_after_all: If True, evaluate all debates after completion
    """
    print(f"\n{'='*80}")
    print(f"일괄 토론 실행 및 평가")
    print(f"{'='*80}")
    print(f"주제 파일: {topic_file}")
    print(f"평가 모드: {evaluation_mode}")
    print(f"평가 시점: {'모든 토론 완료 후' if evaluate_after_all else '각 토론 완료 후'}")
    print(f"{'='*80}\n")
    
    # Step 1: Run batch debates
    print("📋 Step 1: 일괄 토론 실행")
    print("-" * 80)
    
    await run_batch_debates(
        topic_file,
        moderator_url,
        delay_between_debates,
        start_from
    )
    
    if not evaluate_after_all:
        print("\n⚠️  각 토론 완료 후 평가는 아직 구현되지 않았습니다.")
        print("   모든 토론 완료 후 평가를 사용하세요.")
        return
    
    # Step 2: Load summary to get all debate files
    print("\n📊 Step 2: 토론 결과 평가")
    print("-" * 80)
    
    summary_file = Path("debate_batch_summary.json")
    if not summary_file.exists():
        print(f"❌ 오류: 요약 파일을 찾을 수 없습니다: {summary_file}")
        return
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # Get all successful debate files
    debate_files = [
        result["debate_file"]
        for result in summary.get("results", [])
        if result.get("success") and result.get("debate_file")
    ]
    
    if not debate_files:
        print("❌ 평가할 토론 결과가 없습니다.")
        return
    
    print(f"✅ 평가할 토론 수: {len(debate_files)}")
    print()
    
    # Step 3: Evaluate each debate
    evaluator_dir = Path("debate-evaluator-main")
    if not evaluator_dir.exists():
        print(f"❌ 오류: debate-evaluator-main 디렉토리를 찾을 수 없습니다.")
        return
    
    output_dir = Path("debate_results")
    output_dir.mkdir(exist_ok=True)
    
    import os
    original_cwd = Path.cwd()
    
    try:
        os.chdir(evaluator_dir)
        
        evaluation_results = []
        
        for i, debate_file in enumerate(debate_files, 1):
            debate_path = Path(debate_file)
            if not debate_path.exists():
                print(f"⚠️  파일을 찾을 수 없음: {debate_file}")
                continue
            
            print(f"[{i}/{len(debate_files)}] 평가 중: {debate_path.name}")
            
            # Convert to transcript
            from scripts.convert_debate_for_evaluation import convert_debate_to_transcript
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            transcript_file = output_dir / f"transcript_{i:03d}_{timestamp}.txt"
            
            try:
                transcript = convert_debate_to_transcript(debate_path)
                transcript_file.write_text(transcript, encoding='utf-8')
            except Exception as e:
                print(f"❌ 변환 실패: {e}")
                continue
            
            # Run evaluation
            output_file = output_dir / f"evaluation_{i:03d}_{debate_path.stem}_{evaluation_mode}.md"
            
            if evaluation_mode == "all":
                cmd = [
                    "uv", "run", "debate-eval", "all",
                    str(transcript_file.resolve()),
                    "-o", str(output_file.resolve())
                ]
            else:
                cmd = [
                    "uv", "run", "debate-eval",
                    str(transcript_file.resolve()),
                    "-m", evaluation_mode,
                    "-o", str(output_file.resolve())
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(evaluator_dir))
            
            if result.returncode == 0:
                print(f"   ✅ 완료: {output_file.name}")
                evaluation_results.append({
                    "debate_file": str(debate_path),
                    "evaluation_file": str(output_file),
                    "success": True
                })
            else:
                print(f"   ❌ 실패: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                evaluation_results.append({
                    "debate_file": str(debate_path),
                    "evaluation_file": None,
                    "success": False,
                    "error": result.stderr[:200] if result.stderr else "Unknown error"
                })
        
        # Save evaluation summary
        eval_summary_file = output_dir / "evaluation_summary.json"
        eval_summary = {
            "timestamp": datetime.now().isoformat(),
            "evaluation_mode": evaluation_mode,
            "total_debates": len(debate_files),
            "successful_evaluations": sum(1 for r in evaluation_results if r["success"]),
            "failed_evaluations": sum(1 for r in evaluation_results if not r["success"]),
            "results": evaluation_results
        }
        
        eval_summary_file.write_text(
            json.dumps(eval_summary, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        print(f"\n{'='*80}")
        print(f"평가 완료")
        print(f"{'='*80}")
        print(f"총 토론 수: {len(debate_files)}")
        print(f"성공: {eval_summary['successful_evaluations']}")
        print(f"실패: {eval_summary['failed_evaluations']}")
        print(f"평가 요약: {eval_summary_file}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ 평가 실행 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)


def main():
    """Main function."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description="Run batch debates and automatically evaluate results"
    )
    parser.add_argument(
        "topic_file",
        type=Path,
        help="Path to topic file (one topic per line)"
    )
    parser.add_argument(
        "--moderator-url",
        type=str,
        default="http://localhost:10000",
        help="Moderator server URL (default: http://localhost:10000)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Delay in seconds between debates (default: 5.0)"
    )
    parser.add_argument(
        "--evaluation-mode",
        type=str,
        default="all",
        choices=["dqi", "aaf", "dqi-aaf", "afra", "all"],
        help="Evaluation mode (default: all)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="Start from this topic index (1-based, default: 1)"
    )
    parser.add_argument(
        "--no-evaluation",
        action="store_true",
        help="Skip evaluation (only run debates)"
    )
    
    args = parser.parse_args()
    
    if not args.topic_file.exists():
        print(f"❌ 오류: 파일을 찾을 수 없습니다: {args.topic_file}")
        sys.exit(1)
    
    asyncio.run(run_batch_debates_with_evaluation(
        args.topic_file,
        args.moderator_url,
        args.delay,
        args.evaluation_mode,
        args.start_from,
        evaluate_after_all=not args.no_evaluation
    ))


if __name__ == "__main__":
    main()


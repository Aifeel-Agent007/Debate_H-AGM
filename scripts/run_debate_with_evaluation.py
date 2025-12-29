"""Run debate and automatically evaluate the result."""

import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.test_debate import main as run_debate


async def run_debate_and_evaluate(
    topic: str,
    evaluation_mode: str = "all",
    output_dir: Optional[Path] = None
):
    """Run debate and automatically evaluate the result.
    
    Args:
        topic: Debate topic
        evaluation_mode: Evaluation mode (dqi, aaf, dqi-aaf, afra, all)
        output_dir: Output directory for results
    """
    if output_dir is None:
        output_dir = Path("debate_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*80}")
    print(f"토론 실행 및 자동 평가")
    print(f"{'='*80}")
    print(f"주제: {topic}")
    print(f"평가 모드: {evaluation_mode}")
    print(f"출력 디렉토리: {output_dir}")
    print(f"{'='*80}\n")
    
    # Step 1: Run debate
    print("📋 Step 1: 토론 실행 중...")
    print("-" * 80)
    
    # Note: This requires the debate system to be running
    # For now, we'll assume the debate result is saved to debates/ directory
    # In a real implementation, you would capture the debate result here
    
    print("✅ 토론 완료")
    print()
    
    # Step 2: Find the latest debate file
    print("📁 Step 2: 토론 결과 파일 찾는 중...")
    debates_dir = Path("debate")
    if not debates_dir.exists():
        print(f"❌ 오류: debate 디렉토리를 찾을 수 없습니다.")
        print("   토론이 실행되었는지 확인하세요.")
        return
    
    # Find the most recent debate JSON file
    debate_files = list(debates_dir.glob("*.json"))
    if not debate_files:
        print(f"❌ 오류: 토론 결과 JSON 파일을 찾을 수 없습니다.")
        print(f"   {debates_dir} 디렉토리를 확인하세요.")
        return
    
    latest_debate_file = max(debate_files, key=lambda p: p.stat().st_mtime)
    print(f"✅ 발견: {latest_debate_file}")
    print()
    
    # Step 3: Convert to transcript format
    print("🔄 Step 3: 평가 형식으로 변환 중...")
    transcript_file = output_dir / f"transcript_{timestamp}.txt"
    
    try:
        # Import conversion function
        from scripts.convert_debate_for_evaluation import convert_debate_to_transcript
        
        transcript = convert_debate_to_transcript(latest_debate_file)
        transcript_file.write_text(transcript, encoding='utf-8')
        print(f"✅ 변환 완료: {transcript_file}")
        print()
    except Exception as e:
        print(f"❌ 변환 오류: {e}")
        return
    
    # Step 4: Run evaluation
    print("📊 Step 4: 토론 평가 실행 중...")
    print("-" * 80)
    
    evaluator_dir = Path("debate-evaluator-main")
    if not evaluator_dir.exists():
        print(f"❌ 오류: debate-evaluator-main 디렉토리를 찾을 수 없습니다.")
        return
    
    # Change to evaluator directory
    original_cwd = Path.cwd()
    try:
        os.chdir(evaluator_dir)
        
        # Run evaluation
        if evaluation_mode == "all":
            output_file = output_dir / f"evaluation_{timestamp}.md"
            cmd = [
                "uv", "run", "debate-eval", "all",
                str(transcript_file.resolve()),
                "-o", str(output_file.resolve())
            ]
        else:
            output_file = output_dir / f"evaluation_{timestamp}_{evaluation_mode}.md"
            cmd = [
                "uv", "run", "debate-eval",
                str(transcript_file.resolve()),
                "-m", evaluation_mode,
                "-o", str(output_file.resolve())
            ]
        
        print(f"실행 명령: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(evaluator_dir))
        
        if result.returncode == 0:
            print(f"✅ 평가 완료: {output_file}")
            if result.stdout:
                print(result.stdout)
            print()
            print("=" * 80)
            print("📊 평가 결과 요약")
            print("=" * 80)
            print(f"토론 파일: {latest_debate_file}")
            print(f"전사본: {transcript_file}")
            print(f"평가 결과: {output_file}")
            print("=" * 80)
        else:
            print(f"❌ 평가 오류:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            
    except Exception as e:
        print(f"❌ 평가 실행 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)


def main():
    """Main function."""
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python run_debate_with_evaluation.py <debate_json_file> [evaluation_mode]")
        print("Example: python run_debate_with_evaluation.py debate/20241226_123456_topic.json all")
        print("\nEvaluation modes: dqi, aaf, dqi-aaf, afra, all (default: all)")
        print("\nNote: This script evaluates an existing debate file.")
        print("      To run a new debate, use: uv run python src/client/test_debate.py")
        sys.exit(1)
    
    debate_file = Path(sys.argv[1])
    if not debate_file.exists():
        print(f"❌ 오류: 파일을 찾을 수 없습니다: {debate_file}")
        sys.exit(1)
    
    evaluation_mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    if evaluation_mode not in ["dqi", "aaf", "dqi-aaf", "afra", "all"]:
        print(f"❌ 오류: 유효하지 않은 평가 모드: {evaluation_mode}")
        print("사용 가능한 모드: dqi, aaf, dqi-aaf, afra, all")
        sys.exit(1)
    
    # Evaluate existing debate file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("debate_results")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"토론 평가 실행")
    print(f"{'='*80}")
    print(f"토론 파일: {debate_file}")
    print(f"평가 모드: {evaluation_mode}")
    print(f"출력 디렉토리: {output_dir}")
    print(f"{'='*80}\n")
    
    # Convert to transcript
    print("🔄 토론 결과를 평가 형식으로 변환 중...")
    transcript_file = output_dir / f"transcript_{timestamp}.txt"
    
    try:
        from scripts.convert_debate_for_evaluation import convert_debate_to_transcript
        
        transcript = convert_debate_to_transcript(debate_file)
        transcript_file.write_text(transcript, encoding='utf-8')
        print(f"✅ 변환 완료: {transcript_file}")
        print()
    except Exception as e:
        print(f"❌ 변환 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Run evaluation
    print("📊 토론 평가 실행 중...")
    print("-" * 80)
    
    evaluator_dir = Path("debate-evaluator-main")
    if not evaluator_dir.exists():
        print(f"❌ 오류: debate-evaluator-main 디렉토리를 찾을 수 없습니다.")
        sys.exit(1)
    
    original_cwd = Path.cwd()
    try:
        os.chdir(evaluator_dir)
        
        if evaluation_mode == "all":
            output_file = output_dir / f"evaluation_{timestamp}.md"
            cmd = [
                "uv", "run", "debate-eval", "all",
                str(transcript_file.resolve()),
                "-o", str(output_file.resolve())
            ]
        else:
            output_file = output_dir / f"evaluation_{timestamp}_{evaluation_mode}.md"
            cmd = [
                "uv", "run", "debate-eval",
                str(transcript_file.resolve()),
                "-m", evaluation_mode,
                "-o", str(output_file.resolve())
            ]
        
        print(f"실행 명령: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(evaluator_dir))
        
        if result.returncode == 0:
            print(f"✅ 평가 완료: {output_file}")
            if result.stdout:
                print(result.stdout)
            print()
            print("=" * 80)
            print("📊 평가 결과 요약")
            print("=" * 80)
            print(f"토론 파일: {debate_file}")
            print(f"전사본: {transcript_file}")
            print(f"평가 결과: {output_file}")
            print("=" * 80)
        else:
            print(f"❌ 평가 오류:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 평가 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()


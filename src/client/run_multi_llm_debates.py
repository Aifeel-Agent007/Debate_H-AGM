"""Run debates with all 5 LLMs for all topics."""

import asyncio
import logging
import httpx
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported LLM providers
LLM_PROVIDERS = ["gpt", "grok", "gemini", "claude", "qwen"]

# LLM display names
LLM_DISPLAY_NAMES = {
    "gpt": "GPT (OpenAI)",
    "grok": "Grok (Groq)",
    "gemini": "Gemini (Google)",
    "claude": "Claude (Anthropic)",
    "qwen": "Qwen (Alibaba)"
}


def load_topics(topic_file: Path) -> List[str]:
    """Load topics from a file.
    
    Args:
        topic_file: Path to topic file (one topic per line)
        
    Returns:
        List of topics
    """
    try:
        topics = []
        with open(topic_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    topics.append(line)
        return topics
    except Exception as e:
        logger.error(f"Error loading topics from {topic_file}: {e}")
        sys.exit(1)


async def run_single_debate(
    client: httpx.AsyncClient,
    moderator_url: str,
    topic: str,
    topic_index: int,
    total_topics: int,
    llm_provider: str
) -> Dict[str, Any]:
    """Run a single debate.
    
    Args:
        client: HTTP client
        moderator_url: Moderator server URL
        topic: Debate topic
        topic_index: Current topic index (1-based)
        total_topics: Total number of topics
        llm_provider: LLM provider name
        
    Returns:
        Dictionary with debate result information
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"[{llm_provider.upper()}] 토론 {topic_index}/{total_topics}: {topic}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Create JSON-RPC request
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": f"debate_{llm_provider}_{topic_index:03d}",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "messageId": f"msg_{llm_provider}_{topic_index:03d}",
                    "parts": [
                        {
                            "kind": "text",
                            "text": topic
                        }
                    ],
                    "role": "user"
                }
            }
        }
        
        # Send request
        logger.info(f"[{llm_provider.upper()}] 토론 시작 중...")
        response = await client.post(
            moderator_url,
            json=jsonrpc_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            logger.error(f"[{llm_provider.upper()}] HTTP 오류: {response.status_code}")
            logger.error(response.text)
            return {
                "topic": topic,
                "index": topic_index,
                "llm_provider": llm_provider,
                "success": False,
                "error": f"HTTP {response.status_code}",
                "debate_file": None
            }
        
        result = response.json()
        
        # Check for JSON-RPC error
        if "error" in result:
            logger.error(f"[{llm_provider.upper()}] JSON-RPC 오류: {result['error']}")
            return {
                "topic": topic,
                "index": topic_index,
                "llm_provider": llm_provider,
                "success": False,
                "error": str(result.get("error", "Unknown error")),
                "debate_file": None
            }
        
        # Extract debate data
        task = result.get("result", {})
        debate_data = None
        
        artifacts = task.get("artifacts", [])
        for artifact in artifacts:
            if artifact.get('name') == "debate_data":
                parts = artifact.get("parts", [])
                for part in parts:
                    if part.get("kind") == "text":
                        try:
                            debate_data = json.loads(part.get("text", "{}"))
                        except json.JSONDecodeError:
                            pass
                break
        
        # Find saved debate file (look in LLM-specific directory)
        debate_dir = Path("debate") / llm_provider
        debate_file = None
        if debate_dir.exists():
            # Find the most recent JSON file
            json_files = list(debate_dir.glob("*.json"))
            if json_files:
                debate_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        logger.info(f"✅ [{llm_provider.upper()}] 토론 완료: {topic}")
        if debate_file:
            logger.info(f"   저장 위치: {debate_file}")
        
        return {
            "topic": topic,
            "index": topic_index,
            "llm_provider": llm_provider,
            "success": True,
            "error": None,
            "debate_file": str(debate_file) if debate_file else None,
            "total_rounds": debate_data.get("total_rounds", 0) if debate_data else 0,
            "total_responses": debate_data.get("total_responses", 0) if debate_data else 0
        }
        
    except Exception as e:
        logger.error(f"[{llm_provider.upper()}] 토론 실행 중 오류 발생: {e}", exc_info=True)
        return {
            "topic": topic,
            "index": topic_index,
            "llm_provider": llm_provider,
            "success": False,
            "error": str(e),
            "debate_file": None
        }


async def run_debates_for_llm(
    topics: List[str],
    llm_provider: str,
    moderator_url: str = "http://localhost:10000",
    delay_between_debates: float = 5.0,
    start_from: int = 1
) -> List[Dict[str, Any]]:
    """Run all debates for a specific LLM provider.
    
    Args:
        topics: List of debate topics
        llm_provider: LLM provider name
        moderator_url: Moderator server URL
        delay_between_debates: Delay in seconds between debates
        start_from: Start from this topic index (1-based)
        
    Returns:
        List of debate results
    """
    total_topics = len(topics)
    results: List[Dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 [{llm_provider.upper()}] LLM으로 토론 시작")
    logger.info(f"{'='*80}")
    logger.info(f"LLM: {LLM_DISPLAY_NAMES.get(llm_provider, llm_provider)}")
    logger.info(f"총 주제 수: {total_topics}")
    logger.info(f"시작 위치: {start_from}")
    logger.info(f"주제 간 대기 시간: {delay_between_debates}초")
    logger.info(f"{'='*80}\n")
    
    # Set environment variable for this LLM
    original_provider = os.getenv("DEBATE_LLM_PROVIDER")
    os.environ["DEBATE_LLM_PROVIDER"] = llm_provider
    os.environ["PANELIST_LLM_PROVIDER"] = llm_provider
    os.environ["MODERATOR_LLM_PROVIDER"] = llm_provider
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            for i, topic in enumerate(topics, start=1):
                if i < start_from:
                    logger.info(f"⏭️  [{llm_provider.upper()}] 토론 {i}/{total_topics} 건너뜀 (시작 위치: {start_from})")
                    continue
                
                result = await run_single_debate(
                    client,
                    moderator_url,
                    topic,
                    i,
                    total_topics,
                    llm_provider
                )
                
                results.append(result)
                
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
                
                # Delay between debates (except for the last one)
                if i < total_topics and delay_between_debates > 0:
                    logger.info(f"⏳ [{llm_provider.upper()}] {delay_between_debates}초 대기 중...")
                    await asyncio.sleep(delay_between_debates)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ [{llm_provider.upper()}] LLM 토론 완료")
        logger.info(f"{'='*80}")
        logger.info(f"총 주제 수: {total_topics}")
        logger.info(f"성공: {success_count}")
        logger.info(f"실패: {fail_count}")
        logger.info(f"{'='*80}\n")
        
    finally:
        # Restore original environment variable
        if original_provider:
            os.environ["DEBATE_LLM_PROVIDER"] = original_provider
        else:
            os.environ.pop("DEBATE_LLM_PROVIDER", None)
        os.environ.pop("PANELIST_LLM_PROVIDER", None)
        os.environ.pop("MODERATOR_LLM_PROVIDER", None)
    
    return results


async def run_multi_llm_debates(
    topic_file: Path,
    llm_providers: List[str] = None,
    moderator_url: str = "http://localhost:10000",
    delay_between_debates: float = 5.0,
    delay_between_llms: float = 10.0,
    start_from_llm: int = 1,
    start_from_topic: int = 1,
) -> None:
    """Run debates with all specified LLM providers.
    
    Args:
        topic_file: Path to file with topics (one per line)
        llm_providers: List of LLM providers to use (default: all 5)
        moderator_url: Moderator server URL
        delay_between_debates: Delay in seconds between debates
        delay_between_llms: Delay in seconds between LLM providers
        start_from_llm: Start from this LLM index (1-based)
        start_from_topic: Start from this topic index (1-based)
    """
    if llm_providers is None:
        llm_providers = LLM_PROVIDERS
    
    # Load topics
    topics = load_topics(topic_file)
    total_topics = len(topics)
    total_llms = len(llm_providers)
    
    if total_topics == 0:
        logger.error("토론 주제가 없습니다.")
        return
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 다중 LLM 토론 실행")
    logger.info(f"{'='*80}")
    logger.info(f"주제 파일: {topic_file}")
    logger.info(f"총 주제 수: {total_topics}")
    logger.info(f"사용할 LLM: {', '.join([LLM_DISPLAY_NAMES.get(p, p) for p in llm_providers])}")
    logger.info(f"총 토론 수: {total_topics * total_llms}")
    logger.info(f"시작 LLM: {start_from_llm}")
    logger.info(f"시작 주제: {start_from_topic}")
    logger.info(f"주제 간 대기: {delay_between_debates}초")
    logger.info(f"LLM 간 대기: {delay_between_llms}초")
    logger.info(f"{'='*80}\n")
    
    # Check moderator connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as test_client:
            card_response = await test_client.get(f"{moderator_url}/.well-known/agent-card.json")
            agent_card = card_response.json()
            logger.info(f"✅ Moderator 연결 확인: {agent_card.get('name', 'Unknown')}")
    except Exception as e:
        logger.error(f"❌ Moderator 연결 실패: {e}")
        logger.error("   Moderator 서버가 실행 중인지 확인하세요.")
        return
    
    # Results tracking
    all_results: Dict[str, List[Dict[str, Any]]] = {}
    total_success = 0
    total_fail = 0
    
    # Run debates for each LLM
    for llm_idx, llm_provider in enumerate(llm_providers, start=1):
        if llm_idx < start_from_llm:
            logger.info(f"⏭️  LLM {llm_idx}/{total_llms} ({llm_provider}) 건너뜀")
            continue
        
        logger.info(f"\n{'#'*80}")
        logger.info(f"# LLM {llm_idx}/{total_llms}: {LLM_DISPLAY_NAMES.get(llm_provider, llm_provider)}")
        logger.info(f"{'#'*80}\n")
        
        # Create LLM-specific debate directory
        debate_dir = Path("debate") / llm_provider
        debate_dir.mkdir(parents=True, exist_ok=True)
        
        # Run debates for this LLM
        results = await run_debates_for_llm(
            topics,
            llm_provider,
            moderator_url,
            delay_between_debates,
            start_from_topic if llm_idx == start_from_llm else 1
        )
        
        all_results[llm_provider] = results
        
        # Count successes and failures
        llm_success = sum(1 for r in results if r["success"])
        llm_fail = sum(1 for r in results if not r["success"])
        total_success += llm_success
        total_fail += llm_fail
        
        # Save LLM-specific summary
        summary_file = Path(f"debate_batch_summary_{llm_provider}.json")
        summary = {
            "timestamp": datetime.now().isoformat(),
            "llm_provider": llm_provider,
            "llm_display_name": LLM_DISPLAY_NAMES.get(llm_provider, llm_provider),
            "topic_file": str(topic_file),
            "total_topics": total_topics,
            "success_count": llm_success,
            "fail_count": llm_fail,
            "results": results
        }
        
        summary_file.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.info(f"📊 [{llm_provider.upper()}] 요약 저장: {summary_file}")
        
        # Delay between LLMs (except for the last one)
        if llm_idx < total_llms and delay_between_llms > 0:
            logger.info(f"⏳ LLM 간 {delay_between_llms}초 대기 중...")
            await asyncio.sleep(delay_between_llms)
    
    # Save overall summary
    overall_summary_file = Path("debate_multi_llm_summary.json")
    overall_summary = {
        "timestamp": datetime.now().isoformat(),
        "topic_file": str(topic_file),
        "total_topics": total_topics,
        "total_llms": total_llms,
        "llm_providers": llm_providers,
        "total_debates": total_topics * total_llms,
        "total_success": total_success,
        "total_fail": total_fail,
        "llm_results": {
            provider: {
                "success_count": sum(1 for r in results if r["success"]),
                "fail_count": sum(1 for r in results if not r["success"]),
            }
            for provider, results in all_results.items()
        },
        "all_results": all_results
    }
    
    overall_summary_file.write_text(
        json.dumps(overall_summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Print final summary
    logger.info(f"\n{'='*80}")
    logger.info(f"🎉 다중 LLM 토론 완료")
    logger.info(f"{'='*80}")
    logger.info(f"총 LLM 수: {total_llms}")
    logger.info(f"총 주제 수: {total_topics}")
    logger.info(f"총 토론 수: {total_topics * total_llms}")
    logger.info(f"전체 성공: {total_success}")
    logger.info(f"전체 실패: {total_fail}")
    logger.info(f"\nLLM별 결과:")
    for provider, results in all_results.items():
        success = sum(1 for r in results if r["success"])
        fail = sum(1 for r in results if not r["success"])
        logger.info(f"  {LLM_DISPLAY_NAMES.get(provider, provider)}: 성공 {success}, 실패 {fail}")
    logger.info(f"\n전체 요약: {overall_summary_file}")
    logger.info(f"{'='*80}\n")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run debates with all 5 LLMs for all topics"
    )
    parser.add_argument(
        "topic_file",
        type=Path,
        help="Path to topic file (one topic per line)"
    )
    parser.add_argument(
        "--llm-providers",
        type=str,
        nargs="+",
        choices=LLM_PROVIDERS,
        default=LLM_PROVIDERS,
        help=f"LLM providers to use (default: all: {', '.join(LLM_PROVIDERS)})"
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
        "--delay-llms",
        type=float,
        default=10.0,
        help="Delay in seconds between LLM providers (default: 10.0)"
    )
    parser.add_argument(
        "--start-from-llm",
        type=int,
        default=1,
        help="Start from this LLM index (1-based, default: 1)"
    )
    parser.add_argument(
        "--start-from-topic",
        type=int,
        default=1,
        help="Start from this topic index for the first LLM (1-based, default: 1)"
    )
    
    args = parser.parse_args()
    
    if not args.topic_file.exists():
        logger.error(f"파일을 찾을 수 없습니다: {args.topic_file}")
        sys.exit(1)
    
    asyncio.run(run_multi_llm_debates(
        args.topic_file,
        args.llm_providers,
        args.moderator_url,
        args.delay,
        args.delay_llms,
        args.start_from_llm,
        args.start_from_topic,
    ))


if __name__ == "__main__":
    main()


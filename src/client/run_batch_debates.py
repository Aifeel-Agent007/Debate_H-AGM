"""Run multiple debates from a topic list file."""

import asyncio
import logging
import httpx
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_topics(topic_file: Path) -> List[str]:
    """Load topics from a file.
    
    Args:
        topic_file: Path to topic file (one topic per line)
        - Lines starting with # are treated as comments
        - Empty lines are ignored
        
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
    total_topics: int
) -> Dict[str, Any]:
    """Run a single debate.
    
    Args:
        client: HTTP client
        moderator_url: Moderator server URL
        topic: Debate topic
        topic_index: Current topic index (1-based)
        total_topics: Total number of topics
        
    Returns:
        Dictionary with debate result information
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"토론 {topic_index}/{total_topics}: {topic}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Create JSON-RPC request
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": f"debate_{topic_index:03d}",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "messageId": f"msg_{topic_index:03d}",
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
        logger.info(f"토론 시작 중...")
        response = await client.post(
            moderator_url,
            json=jsonrpc_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            logger.error(f"HTTP 오류: {response.status_code}")
            logger.error(response.text)
            return {
                "topic": topic,
                "index": topic_index,
                "success": False,
                "error": f"HTTP {response.status_code}",
                "debate_file": None
            }
        
        result = response.json()
        
        # Check for JSON-RPC error
        if "error" in result:
            logger.error(f"JSON-RPC 오류: {result['error']}")
            return {
                "topic": topic,
                "index": topic_index,
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
        
        # Find saved debate file
        debate_dir = Path("debate")
        debate_file = None
        if debate_dir.exists():
            # Find the most recent JSON file
            json_files = list(debate_dir.glob("*.json"))
            if json_files:
                debate_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        logger.info(f"✅ 토론 완료: {topic}")
        if debate_file:
            logger.info(f"   저장 위치: {debate_file}")
        
        return {
            "topic": topic,
            "index": topic_index,
            "success": True,
            "error": None,
            "debate_file": str(debate_file) if debate_file else None,
            "total_rounds": debate_data.get("total_rounds", 0) if debate_data else 0,
            "total_responses": debate_data.get("total_responses", 0) if debate_data else 0
        }
        
    except Exception as e:
        logger.error(f"토론 실행 중 오류 발생: {e}", exc_info=True)
        return {
            "topic": topic,
            "index": topic_index,
            "success": False,
            "error": str(e),
            "debate_file": None
        }


async def run_batch_debates(
    topic_file: Path,
    moderator_url: str = "http://localhost:10000",
    delay_between_debates: float = 5.0,
    start_from: int = 1
) -> None:
    """Run multiple debates from a topic list.
    
    Args:
        topic_file: Path to file with topics (one per line)
        moderator_url: Moderator server URL
        delay_between_debates: Delay in seconds between debates
        start_from: Start from this topic index (1-based)
    """
    # Load topics
    topics = load_topics(topic_file)
    total_topics = len(topics)
    
    if total_topics == 0:
        logger.error("토론 주제가 없습니다.")
        return
    
    logger.info(f"\n{'='*80}")
    logger.info(f"일괄 토론 실행")
    logger.info(f"{'='*80}")
    logger.info(f"주제 파일: {topic_file}")
    logger.info(f"총 주제 수: {total_topics}")
    logger.info(f"시작 위치: {start_from}")
    logger.info(f"주제 간 대기 시간: {delay_between_debates}초")
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
    results: List[Dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    
    # Run debates
    async with httpx.AsyncClient(timeout=600.0) as client:
        for i, topic in enumerate(topics, start=1):
            if i < start_from:
                logger.info(f"⏭️  토론 {i}/{total_topics} 건너뜀 (시작 위치: {start_from})")
                continue
            
            result = await run_single_debate(
                client,
                moderator_url,
                topic,
                i,
                total_topics
            )
            
            results.append(result)
            
            if result["success"]:
                success_count += 1
            else:
                fail_count += 1
            
            # Delay between debates (except for the last one)
            if i < total_topics and delay_between_debates > 0:
                logger.info(f"⏳ {delay_between_debates}초 대기 중...")
                await asyncio.sleep(delay_between_debates)
    
    # Save summary
    summary_file = Path("debate_batch_summary.json")
    summary = {
        "timestamp": datetime.now().isoformat(),
        "topic_file": str(topic_file),
        "total_topics": total_topics,
        "success_count": success_count,
        "fail_count": fail_count,
        "results": results
    }
    
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Print final summary
    logger.info(f"\n{'='*80}")
    logger.info(f"일괄 토론 완료")
    logger.info(f"{'='*80}")
    logger.info(f"총 주제 수: {total_topics}")
    logger.info(f"성공: {success_count}")
    logger.info(f"실패: {fail_count}")
    logger.info(f"요약 파일: {summary_file}")
    logger.info(f"{'='*80}\n")
    
    # Print failed topics
    if fail_count > 0:
        logger.warning("실패한 토론 주제:")
        for result in results:
            if not result["success"]:
                logger.warning(f"  [{result['index']}] {result['topic']}: {result['error']}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run multiple debates from a topic list file"
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
        "--start-from",
        type=int,
        default=1,
        help="Start from this topic index (1-based, default: 1)"
    )
    
    args = parser.parse_args()
    
    if not args.topic_file.exists():
        logger.error(f"파일을 찾을 수 없습니다: {args.topic_file}")
        sys.exit(1)
    
    asyncio.run(run_batch_debates(
        args.topic_file,
        args.moderator_url,
        args.delay,
        args.start_from
    ))


if __name__ == "__main__":
    main()


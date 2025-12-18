"""Test client for the debate system."""

import asyncio
import logging
import httpx
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run a test debate."""
    # Moderator URL
    moderator_url = "http://localhost:10000"

    logger.info(f"Connecting to moderator at {moderator_url}")

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:  # Increased to 10 minutes
            # Get agent card
            logger.info("Fetching moderator agent card...")
            card_response = await client.get(f"{moderator_url}/.well-known/agent-card.json")
            agent_card = card_response.json()
            logger.info(f"Connected to: {agent_card['name']}")
            logger.info(f"Description: {agent_card['description']}")

            # Get debate topic from user input
            print(f"\n{'='*80}")
            print("토론 시스템에 오신 것을 환영합니다!")
            print(f"{'='*80}\n")

            topic = input("토론 주제를 입력하세요: ").strip()

            if not topic:
                logger.error("주제가 입력되지 않았습니다. 종료합니다.")
                return

            logger.info(f"\n{'='*80}")
            logger.info(f"토론 주제: {topic}")
            logger.info(f"{'='*80}\n")

            # Create JSON-RPC request for message/send
            jsonrpc_request = {
                "jsonrpc": "2.0",
                "id": "test_debate_001",
                "method": "message/send",
                "params": {
                    "message": {
                        "kind": "message",
                        "messageId": "msg_001",
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

            # Send message
            logger.info("Starting debate...")
            response = await client.post(
                moderator_url,
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Error: HTTP {response.status_code}")
                logger.error(response.text)
                return

            result = response.json()

            logger.info(f"\n{'='*80}")
            logger.info("토론 결과")
            logger.info(f"{'='*80}\n")

            # Check for JSON-RPC error
            if "error" in result:
                logger.error(f"JSON-RPC Error: {result['error']}")
                return

            # Extract the task from the result
            task = result.get("result", {})

            logger.info(f"Task ID: {task.get('taskId', 'N/A')}")

            status = task.get("status", {})
            logger.info(f"상태: {status.get('state', 'N/A')}")

            # Display artifacts
            artifacts = task.get("artifacts", [])
            debate_data = None

            if artifacts:
                logger.info(f"\n생성된 아티팩트 수: {len(artifacts)}")

                # First pass: parse debate_data
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

                # Second pass: display formatted output
                for artifact in artifacts:
                    artifact_name = artifact.get('name', 'N/A')

                    # Display debate_history with formatted panelist responses
                    if artifact_name == "debate_history":
                        logger.info(f"\n{'='*80}")
                        logger.info("📋 토론 내용")
                        logger.info(f"{'='*80}\n")

                        if debate_data:
                            for round_data in debate_data.get("debate_history", []):
                                round_num = round_data.get("round_number", 0)
                                logger.info(f"\n{'─'*80}")
                                logger.info(f"🔵 Round {round_num}")
                                logger.info(f"{'─'*80}")

                                for response in round_data.get("panelist_responses", []):
                                    persona = response.get("persona", "Unknown")
                                    stance = response.get("stance", "")
                                    opinion = response.get("opinion", "")

                                    # Emoji for each persona
                                    persona_emoji = {
                                        "우파 정치인": "🔴",
                                        "우파 학자": "📘",
                                        "좌파 정치인": "🔵",
                                        "좌파 학자": "📗"
                                    }
                                    emoji = persona_emoji.get(persona, "💬")

                                    logger.info(f"\n{emoji} {persona} ({stance}):")
                                    logger.info(f"{opinion}\n")

                    # Display summary
                    elif artifact_name == "debate_summary":
                        logger.info(f"\n{'='*80}")
                        logger.info("📝 토론 요약")
                        logger.info(f"{'='*80}\n")

                        parts = artifact.get("parts", [])
                        for part in parts:
                            if part.get("kind") == "text":
                                text = part.get("text", "")
                                logger.info(text)

            # Display history
            history = task.get("history", [])
            if history:
                logger.info(f"\n{'='*80}")
                logger.info("대화 기록")
                logger.info(f"{'='*80}\n")

                for msg in history:
                    role = msg.get("role", "unknown")
                    logger.info(f"\n{role.upper()}:")
                    parts = msg.get("parts", [])
                    for part in parts:
                        if part.get("kind") == "text":
                            text = part.get("text", "")
                            preview = text[:200] + "..." if len(text) > 200 else text
                            logger.info(f"  {preview}")

            logger.info(f"\n{'='*80}")
            logger.info("토론 완료!")
            logger.info(f"{'='*80}\n")

    except Exception as e:
        logger.error(f"Error during debate: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

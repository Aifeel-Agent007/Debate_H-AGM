"""Test client for the debate system with streaming support."""

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
    """Run a test debate with streaming output."""
    # Moderator URL
    moderator_url = "http://localhost:10000"

    logger.info(f"Connecting to moderator at {moderator_url}")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Get agent card
            logger.info("Fetching moderator agent card...")
            card_response = await client.get(f"{moderator_url}/.well-known/agent-card.json")
            agent_card = card_response.json()
            logger.info(f"Connected to: {agent_card['name']}")
            logger.info(f"Description: {agent_card['description']}")

            # Debate topic
            topic = "인공지능이 인간의 일자리를 대체하는 것에 대해 어떻게 생각하는가?"

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

            # Send message and stream responses
            logger.info("Starting debate with streaming...")
            logger.info(f"\n{'='*80}")
            logger.info("실시간 토론 진행")
            logger.info(f"{'='*80}\n")

            # Track shown artifacts to avoid duplicates
            shown_artifacts = set()

            async with client.stream(
                'POST',
                moderator_url,
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code != 200:
                    logger.error(f"Error: HTTP {response.status_code}")
                    async for chunk in response.aiter_text():
                        logger.error(chunk)
                    return

                # Process streaming response
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk

                    # Try to parse complete JSON objects from buffer
                    while True:
                        try:
                            # Find the end of a JSON object
                            obj_end = buffer.find('\n')
                            if obj_end == -1:
                                break

                            json_str = buffer[:obj_end].strip()
                            buffer = buffer[obj_end + 1:]

                            if not json_str:
                                continue

                            # Parse the JSON-RPC notification or response
                            data = json.loads(json_str)

                            # Handle task updates
                            if data.get("method") == "task/update":
                                params = data.get("params", {})
                                artifacts = params.get("artifacts", [])

                                # Display new artifacts in real-time
                                for artifact in artifacts:
                                    artifact_name = artifact.get('name', '')

                                    # Skip if already shown
                                    if artifact_name in shown_artifacts:
                                        continue

                                    # Only show real-time panelist responses
                                    if artifact_name.startswith("panelist_response_"):
                                        shown_artifacts.add(artifact_name)

                                        parts = artifact.get("parts", [])
                                        for part in parts:
                                            if part.get("kind") == "text":
                                                text = part.get("text", "")
                                                logger.info(f"\n{text}")

                            # Handle final response
                            elif "result" in data:
                                task = data.get("result", {})
                                status = task.get("status", {})

                                if status.get("state") == "completed":
                                    logger.info(f"\n{'='*80}")
                                    logger.info("토론 완료!")
                                    logger.info(f"{'='*80}\n")

                                    # Display final summary if available
                                    artifacts = task.get("artifacts", [])
                                    for artifact in artifacts:
                                        if artifact.get('name') == "debate_summary":
                                            logger.info(f"\n{'='*80}")
                                            logger.info("📝 토론 요약")
                                            logger.info(f"{'='*80}\n")

                                            parts = artifact.get("parts", [])
                                            for part in parts:
                                                if part.get("kind") == "text":
                                                    text = part.get("text", "")
                                                    logger.info(text)
                                elif status.get("state") == "failed":
                                    logger.error("토론이 실패했습니다.")

                        except json.JSONDecodeError:
                            # Incomplete JSON, continue buffering
                            break
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            break

    except Exception as e:
        logger.error(f"Error during debate: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

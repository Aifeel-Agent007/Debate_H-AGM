"""
Simple test to verify panelist generates a response.
"""

import asyncio
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()


async def test():
    """Simple test."""
    print("\n" + "="*80)
    print("Simple Response Test")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        print("\n1. Creating agent...")
        panelist = PanelistAgent("right_scholar")
        print(f"   ✓ {panelist.persona_config['name']}")

        topic = "인공지능의 발전"
        print(f"\n2. Topic: {topic}")
        print("\n3. Generating response (no tools needed for this topic)...")

        result = await panelist.graph.ainvoke(
            {
                "topic": topic,
                "round_number": 1,
                "previous_context": "",
            },
            config={"configurable": {"thread_id": "simple-test"}},
        )

        print("\n4. Result:")
        print(f"   Type: {type(result)}")
        print(f"   Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        response_data = result.get("response")
        print(f"\n5. Response data:")
        print(f"   Type: {type(response_data)}")

        if isinstance(response_data, dict):
            opinion = response_data.get("opinion", "")
            reasoning = response_data.get("reasoning", "")

            print("\n6. Content:")
            print(f"\n[의견] ({len(opinion)}자)")
            print(opinion)
            print(f"\n[근거] ({len(reasoning)}자)")
            print(reasoning)

            print("\n✅ SUCCESS: Response generated!")
            return True
        else:
            print(f"\n❌ ERROR: Unexpected response type: {type(response_data)}")
            print(f"   Content: {response_data}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup():
    """Cleanup."""
    try:
        from src.shared.mcp_tools import MCPSearchManager
        if MCPSearchManager._instance:
            await MCPSearchManager._instance.close()
    except:
        pass


async def main():
    """Main."""
    try:
        result = await test()
        if result:
            print("\n" + "="*80)
            print("✅ Test passed!")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("❌ Test failed!")
            print("="*80)
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())

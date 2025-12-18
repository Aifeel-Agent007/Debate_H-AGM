"""
Test that panelist get_opinion returns proper PanelistResponse.
"""

import asyncio
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()


async def test():
    """Test get_opinion method."""
    print("\n" + "="*80)
    print("Test Panelist get_opinion Method")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        print("\n1. Creating agent...")
        panelist = PanelistAgent("right_scholar")
        print(f"   ✓ {panelist.persona_config['name']}")

        topic = "인공지능의 발전"
        print(f"\n2. Topic: {topic}")
        print("\n3. Calling get_opinion...")

        response = await panelist.get_opinion(
            topic=topic,
            round_number=1,
            context_id="test-response",
            previous_context=None
        )

        print("\n4. Response received:")
        print(f"   Type: {type(response)}")
        print(f"   Persona: {response.persona}")
        print(f"   Stance: {response.stance}")
        print(f"   Opinion length: {len(response.opinion)} chars")
        print(f"   Reasoning length: {len(response.reasoning)} chars")

        print(f"\n5. Opinion preview:")
        print(f"   {response.opinion[:200]}...")

        print(f"\n6. Reasoning preview:")
        print(f"   {response.reasoning[:200]}...")

        print("\n✅ SUCCESS: PanelistResponse properly formatted!")
        return True

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
            print("✅ Test passed - Ready for debate!")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("❌ Test failed")
            print("="*80)
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())

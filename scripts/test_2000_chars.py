"""
Quick test for 2000 chars/min setting.
"""

import asyncio
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()


async def test():
    """Quick test."""
    print("\n" + "="*80)
    print("Quick Test - 2000 chars/min setting")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        panelist = PanelistAgent("right_politician")
        print(f"\n✓ {panelist.persona_config['name']}")

        topic = "인공지능과 일자리"
        print(f"   Topic: {topic}")
        print(f"\n⏳ Generating response...")

        response = await panelist.get_opinion(
            topic=topic,
            round_number=1,
            context_id="test-2000",
            previous_context=None
        )

        opinion_len = len(response.opinion)
        reasoning_len = len(response.reasoning)
        total_len = opinion_len + reasoning_len

        print(f"\n📊 Results:")
        print(f"   의견: {opinion_len}자 (목표: 700~1000자)")
        print(f"   근거: {reasoning_len}자 (목표: 2800~5000자)")
        print(f"   총합: {total_len}자 (목표: ~4000자)")
        print(f"   예상 시간: {total_len/2000:.1f}분 (2000자/분 기준)")

        if 3000 <= total_len <= 6500:
            print(f"\n✅ SUCCESS: 적절한 길이!")
        else:
            print(f"\n⚠️  WARNING: 목표 범위 벗어남")

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
        await test()
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())

"""
Test actual response length from panelists.
"""

import asyncio
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()


async def test_length():
    """Test actual response length."""
    print("\n" + "="*80)
    print("Actual Response Length Test")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        # Test all 4 panelists
        personas = ["right_politician", "right_scholar", "left_politician", "left_scholar"]
        topic = "인공지능이 인간의 일자리를 대체하는 것에 대해 어떻게 생각하는가?"

        results = []

        for persona in personas:
            print(f"\n{'='*80}")
            print(f"Testing: {persona}")
            print(f"{'='*80}")

            panelist = PanelistAgent(persona)
            print(f"✓ Agent: {panelist.persona_config['name']}")

            response = await panelist.get_opinion(
                topic=topic,
                round_number=1,
                context_id=f"test-{persona}",
                previous_context=None
            )

            opinion_len = len(response.opinion)
            reasoning_len = len(response.reasoning)
            total_len = opinion_len + reasoning_len

            print(f"\n📊 Length Analysis:")
            print(f"   의견 (Opinion): {opinion_len}자")
            print(f"   근거 (Reasoning): {reasoning_len}자")
            print(f"   총합 (Total): {total_len}자")
            print(f"   예상 시간: {total_len/200:.1f}분 (200자/분 기준)")

            results.append({
                "persona": panelist.persona_config['name'],
                "opinion": opinion_len,
                "reasoning": reasoning_len,
                "total": total_len
            })

            print(f"\n📝 Content Preview:")
            print(f"   [의견] {response.opinion[:100]}...")
            print(f"   [근거] {response.reasoning[:100]}...")

        # Summary
        print("\n" + "="*80)
        print("Summary - All Panelists")
        print("="*80)

        for r in results:
            print(f"\n{r['persona']}:")
            print(f"  의견: {r['opinion']}자")
            print(f"  근거: {r['reasoning']}자")
            print(f"  총합: {r['total']}자 ({r['total']/200:.1f}분)")

            # Check if within target
            if 400 <= r['total'] <= 1400:
                print(f"  상태: ✅ 적절 (목표: 400~1200자)")
            elif r['total'] < 400:
                print(f"  상태: ⚠️  너무 짧음 (목표: 400~1200자)")
            else:
                print(f"  상태: ⚠️  너무 김 (목표: 400~1200자)")

        # Average
        avg_total = sum(r['total'] for r in results) / len(results)
        print(f"\n평균 길이: {avg_total:.0f}자 ({avg_total/200:.1f}분)")

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
        await test_length()
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())

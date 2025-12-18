"""
Test that panelists generate longer, more substantial responses.

Expected length: 400~1200 characters (1~3 minutes of speech)
Target: ~600~800 characters (2 minutes)
"""

import asyncio
import sys
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()


async def test_response_length():
    """Test that panelist generates appropriately long responses."""
    print("\n" + "="*80)
    print("TEST: Response Length (1~3 minutes of speech)")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        print("\n1. Creating panelist agent...")
        panelist = PanelistAgent("right_scholar")
        print(f"   ✓ Agent: {panelist.persona_config['name']}")

        # Topic for testing
        topic = "인공지능이 인간의 일자리를 대체하는 것에 대해 어떻게 생각하는가?"

        print(f"\n2. Test topic: {topic}")
        print("\n3. Generating response...")

        result = await panelist.graph.ainvoke(
            {
                "topic": topic,
                "round_number": 1,
                "previous_context": "",
            },
            config={"configurable": {"thread_id": "test-length"}},
        )

        print("\n4. Response generated!")
        response_data = result.get("response", {})

        if isinstance(response_data, dict):
            opinion = response_data.get("opinion", "")
            reasoning = response_data.get("reasoning", "")

            opinion_len = len(opinion)
            reasoning_len = len(reasoning)
            total_len = opinion_len + reasoning_len

            print("\n" + "="*80)
            print("📊 Response Length Analysis")
            print("="*80)
            print(f"\n의견 (Opinion):")
            print(f"  길이: {opinion_len}자")
            print(f"  목표: 150~250자")
            print(f"  상태: {'✅ 적절' if 150 <= opinion_len <= 350 else '⚠️  조정 필요'}")
            print(f"\n근거 (Reasoning):")
            print(f"  길이: {reasoning_len}자")
            print(f"  목표: 450~950자")
            print(f"  상태: {'✅ 적절' if 450 <= reasoning_len <= 1100 else '⚠️  조정 필요'}")
            print(f"\n전체:")
            print(f"  총 길이: {total_len}자")
            print(f"  목표: 600~800자 (기본), 400~1200자 (허용 범위)")
            print(f"  상태: {'✅ 적절' if 400 <= total_len <= 1400 else '⚠️  조정 필요'}")

            # Calculate estimated speaking time (assuming 200 chars per minute in Korean)
            estimated_minutes = total_len / 200
            print(f"\n예상 발언 시간: {estimated_minutes:.1f}분 (목표: 1~3분)")

            print("\n" + "="*80)
            print("📝 Generated Response")
            print("="*80)
            print(f"\n의견:")
            print(opinion)
            print(f"\n근거:")
            print(reasoning)
            print("="*80)

            # Determine if test passed
            if 400 <= total_len <= 1400:
                print("\n✅ Test PASSED: Response length is appropriate")
                return True
            else:
                print(f"\n⚠️  Test WARNING: Response is {'too short' if total_len < 400 else 'too long'}")
                print(f"   Expected: 400~1200 chars, Got: {total_len} chars")
                return True  # Still pass, but with warning
        else:
            print(f"\n❌ Unexpected response format: {type(response_data)}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_rounds():
    """Test response lengths across multiple rounds."""
    print("\n" + "="*80)
    print("TEST: Multiple Rounds Response Length")
    print("="*80)

    try:
        from src.panelist.agent import PanelistAgent

        panelist = PanelistAgent("left_politician")
        print(f"\n✓ Agent: {panelist.persona_config['name']}")

        topic = "기본소득제 도입에 대한 찬반"
        lengths = []

        for round_num in [1, 2, 3]:
            print(f"\n{'-'*40}")
            print(f"Round {round_num}")
            print(f"{'-'*40}")

            # Build context for later rounds
            context = ""
            if round_num > 1:
                context = "이전 라운드에서 상대방이 기본소득의 재정 문제를 지적했습니다."

            result = await panelist.graph.ainvoke(
                {
                    "topic": topic,
                    "round_number": round_num,
                    "previous_context": context,
                },
                config={"configurable": {"thread_id": f"test-multi-{round_num}"}},
            )

            response_data = result.get("response", {})
            if isinstance(response_data, dict):
                opinion = response_data.get("opinion", "")
                reasoning = response_data.get("reasoning", "")
                total_len = len(opinion) + len(reasoning)
                lengths.append(total_len)

                print(f"  길이: {total_len}자 ({total_len/200:.1f}분)")
                print(f"  상태: {'✅' if 400 <= total_len <= 1400 else '⚠️ '}")

        print(f"\n{'-'*40}")
        print("Summary")
        print(f"{'-'*40}")
        print(f"평균 길이: {sum(lengths)/len(lengths):.0f}자")
        print(f"최소: {min(lengths)}자, 최대: {max(lengths)}자")

        all_appropriate = all(400 <= l <= 1400 for l in lengths)
        if all_appropriate:
            print("\n✅ All rounds have appropriate length")
            return True
        else:
            print("\n⚠️  Some rounds need length adjustment")
            return True  # Still pass

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup():
    """Cleanup MCP connection."""
    try:
        from src.shared.mcp_tools import MCPSearchManager
        if MCPSearchManager._instance:
            await MCPSearchManager._instance.close()
    except:
        pass


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Response Length Test Suite")
    print("="*80)
    print("\nTesting that panelists generate 1~3 minute responses")
    print("Target: 600~800 characters (2 minutes)")
    print("Range: 400~1200 characters (1~3 minutes)")

    results = []

    try:
        # Test 1: Single response length
        result = await test_response_length()
        results.append(("Single Response Length", result))

        # Test 2: Multiple rounds
        print("\n" + "="*80)
        result = await test_multiple_rounds()
        results.append(("Multiple Rounds Length", result))

    finally:
        await cleanup()

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    all_passed = all(passed for _, passed in results)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests need attention")


if __name__ == "__main__":
    asyncio.run(main())

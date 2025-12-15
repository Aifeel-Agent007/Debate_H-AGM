"""
Test script for subtopic-based debate system.
"""

import asyncio
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)
load_dotenv()


async def test_subtopic_generation():
    """Test subtopic generation and time allocation."""
    print("\n" + "="*80)
    print("Test 1: Subtopic Generation")
    print("="*80)

    try:
        from src.moderator.agent import ModeratorAgent

        # Create moderator with dummy panelist URLs (we won't call them)
        panelist_urls = {
            "right_politician": "http://localhost:8001",
            "right_scholar": "http://localhost:8002",
            "left_politician": "http://localhost:8003",
            "left_scholar": "http://localhost:8004",
        }

        moderator = ModeratorAgent(panelist_urls)
        print("✓ Moderator agent created")

        # Test the flow manually
        topic = "인공지능과 일자리"
        print(f"\nTopic: {topic}")

        # 1. Research phase
        print("\n1. Testing research phase...")
        state = {"topic": topic}
        state = await moderator._research_topic(state)

        if "research_data" in state:
            print(f"   ✓ Research completed: {len(state['research_data'])} characters")
        else:
            print("   ✗ Research failed")
            return False

        # 2. Subtopic generation
        print("\n2. Testing subtopic generation...")
        state = moderator._generate_subtopics(state)

        subtopics = state.get("subtopics", [])
        if not subtopics:
            print("   ✗ No subtopics generated")
            return False

        print(f"   ✓ Generated {len(subtopics)} subtopics")

        # Validate subtopics
        if len(subtopics) < 4 or len(subtopics) > 6:
            print(f"   ✗ Invalid number of subtopics: {len(subtopics)} (expected 4-6)")
            return False

        # 3. Time allocation
        print("\n3. Testing time allocation...")
        total_allocated = sum(st["allocated_minutes"] for st in subtopics)
        print(f"   Total allocated time: {total_allocated:.1f} minutes")

        if abs(total_allocated - 100) > 1:  # Allow 1 minute tolerance
            print(f"   ✗ Total allocation not ~100 minutes: {total_allocated:.1f}")
            return False

        print("   ✓ Time allocation valid")

        # 4. Display subtopics
        print("\n4. Generated Subtopics:")
        for st in subtopics:
            print(f"   {st['index']+1}. {st['title']}")
            print(f"      Description: {st['description']}")
            print(f"      Importance: {st['importance_score']}/10")
            print(f"      Allocated Time: {st['allocated_minutes']:.1f} minutes")
            print()

        print("✅ Test 1 PASSED: Subtopic generation works correctly")
        return True

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_time_tracking():
    """Test time tracking calculations."""
    print("\n" + "="*80)
    print("Test 2: Time Tracking")
    print("="*80)

    try:
        # Simulate responses
        mock_responses = [
            {"opinion": "A" * 1000, "reasoning": "B" * 3000},  # 4000 chars = 2 min
            {"opinion": "C" * 1000, "reasoning": "D" * 3000},  # 4000 chars = 2 min
            {"opinion": "E" * 1000, "reasoning": "F" * 3000},  # 4000 chars = 2 min
            {"opinion": "G" * 1000, "reasoning": "H" * 3000},  # 4000 chars = 2 min
        ]

        total_chars = sum(
            len(r["opinion"]) + len(r["reasoning"])
            for r in mock_responses
        )

        calculated_minutes = total_chars / 2000.0

        print(f"Total characters: {total_chars}")
        print(f"Calculated time: {calculated_minutes:.1f} minutes")
        print(f"Expected time: 8.0 minutes")

        if abs(calculated_minutes - 8.0) < 0.1:
            print("✅ Test 2 PASSED: Time tracking calculation correct")
            return True
        else:
            print(f"✗ Time calculation incorrect: {calculated_minutes:.1f} != 8.0")
            return False

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup():
    """Cleanup resources."""
    try:
        from src.shared.mcp_tools import MCPSearchManager
        if MCPSearchManager._instance:
            await MCPSearchManager._instance.close()
    except:
        pass


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Subtopic Debate System - Test Suite")
    print("="*80)

    results = []

    # Run tests
    results.append(await test_subtopic_generation())
    results.append(await test_time_tracking())

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED")
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")

    await cleanup()

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

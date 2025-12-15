"""Test script to verify that each panelist has an independent memory system."""

import os
import asyncio
from dotenv import load_dotenv
from src.shared.memory_layer import AgenticMemorySystem

# Load environment variables
load_dotenv()

# Panelist personas
PANELISTS = [
    "right_politician",
    "right_scholar", 
    "left_politician",
    "left_scholar"
]

# 각 패널리스트마다 다른 Neo4j 포트 사용
NEO4J_PORTS = {
    "right_politician": 7687,  # Neo4j #1
    "right_scholar": 7688,      # Neo4j #2
    "left_politician": 7689,    # Neo4j #3
    "left_scholar": 7690,       # Neo4j #4
}


def test_memory_separation():
    """Test that each panelist has an independent memory system."""
    print("="*60)
    print("🧪 Testing Memory System Separation for Panelists")
    print("="*60)
    print()
    
    # Initialize memory systems for each panelist
    memory_systems = {}
    
    for persona in PANELISTS:
        user_id = f"panelist_{persona}"
        neo4j_port = NEO4J_PORTS[persona]
        neo4j_url = f"bolt://localhost:{neo4j_port}"
        print(f"📝 Initializing memory for {persona} (user_id: {user_id}, Neo4j: {neo4j_url})...")
        
        try:
            memory_system = AgenticMemorySystem(
                user_id=user_id,
                neo4j_url=neo4j_url,
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY")
            )
            memory_systems[persona] = memory_system
            print(f"   ✅ Memory system initialized for {persona}")
        except Exception as e:
            print(f"   ❌ Failed to initialize memory for {persona}: {e}")
            return False
    
    print()
    print("="*60)
    print("📊 Testing Memory Isolation")
    print("="*60)
    print()
    
    # Test 1: Save different content to each panelist's memory
    print("Test 1: Saving unique content to each panelist's memory...")
    saved_ids = {}
    
    for persona in PANELISTS:
        content = f"[{persona}] This is a unique memory for {persona}. Only this panelist should see this."
        memory_system = memory_systems[persona]
        
        try:
            memory_id = memory_system.add_note(content)
            saved_ids[persona] = memory_id
            print(f"   ✅ Saved memory for {persona}: {memory_id}")
        except Exception as e:
            print(f"   ❌ Failed to save memory for {persona}: {e}")
            return False
    
    print()
    
    # Test 2: Verify each panelist can only see their own memory
    print("Test 2: Verifying memory isolation (each panelist should only see their own memory)...")
    all_passed = True
    
    for persona in PANELISTS:
        memory_system = memory_systems[persona]
        search_query = f"unique memory for {persona}"
        
        try:
            results = memory_system.find_related_memories_raw(search_query, k=10)
            
            # Check if the result contains this panelist's unique content
            if persona in results:
                print(f"   ✅ {persona}: Found their own memory")
            else:
                print(f"   ⚠️  {persona}: Could not find their own memory in results")
                all_passed = False
            
            # Check if the result contains other panelists' content (should not)
            other_personas = [p for p in PANELISTS if p != persona]
            found_others = False
            for other in other_personas:
                if other in results:
                    print(f"   ❌ {persona}: Found memory from {other} (ISOLATION FAILED!)")
                    found_others = True
                    all_passed = False
            
            if not found_others:
                print(f"   ✅ {persona}: No memory leakage from other panelists")
                
        except Exception as e:
            print(f"   ❌ Failed to search memory for {persona}: {e}")
            all_passed = False
    
    print()
    print("="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED: Memory systems are properly isolated!")
    else:
        print("❌ SOME TESTS FAILED: Memory isolation may not be working correctly.")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set it in your .env file or environment")
        exit(1)
    
    success = test_memory_separation()
    exit(0 if success else 1)


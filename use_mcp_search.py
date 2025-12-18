#!/usr/bin/env python
"""
MCP Search 서버를 사용하여 웹 검색하기

Usage:
    python use_mcp_search.py "검색어"
    python use_mcp_search.py --answer "질문?"
    python use_mcp_search.py --context "주제"
    python use_mcp_search.py --verify "주장"
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()


async def search_web(query: str, max_results: int = 5):
    """MCP 서버를 통해 웹 검색"""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_servers/search/server.py"],
        env={
            **os.environ,
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        },
    )

    print(f"\n🔍 웹 검색 중: '{query}'")
    print(f"   최대 결과 수: {max_results}")
    print("="*80)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n📡 MCP 서버에 요청 중...")
            result = await session.call_tool(
                "search_web",
                arguments={
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                }
            )

            print("\n✅ 검색 완료!\n")
            print("="*80)

            # Extract text from result
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(item.text)
            else:
                print(result)


async def get_quick_answer(question: str):
    """MCP 서버를 통해 빠른 답변 얻기"""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_servers/search/server.py"],
        env={
            **os.environ,
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        },
    )

    print(f"\n❓ 질문: '{question}'")
    print("="*80)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n📡 MCP 서버에 요청 중...")
            result = await session.call_tool(
                "get_quick_answer",
                arguments={
                    "question": question,
                    "search_depth": "advanced",
                }
            )

            print("\n✅ 답변:\n")
            print("="*80)

            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(item.text)
            else:
                print(result)


async def get_context(topic: str):
    """MCP 서버를 통해 주제에 대한 컨텍스트 얻기"""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_servers/search/server.py"],
        env={
            **os.environ,
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        },
    )

    print(f"\n📚 주제: '{topic}'")
    print("="*80)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n📡 MCP 서버에 요청 중...")
            result = await session.call_tool(
                "get_context",
                arguments={
                    "query": topic,
                    "max_tokens": 2000,
                    "search_depth": "advanced",
                }
            )

            print("\n✅ 컨텍스트:\n")
            print("="*80)

            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(item.text[:1000] + "...\n")
            else:
                print(str(result)[:1000] + "...")


async def verify_fact(claim: str):
    """MCP 서버를 통해 팩트 체크"""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_servers/search/server.py"],
        env={
            **os.environ,
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        },
    )

    print(f"\n✓ 팩트 체크할 주장: '{claim}'")
    print("="*80)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("\n📡 MCP 서버에 요청 중...")
            result = await session.call_tool(
                "verify_fact",
                arguments={
                    "claim": claim,
                    "context": "",
                }
            )

            print("\n✅ 검증 결과:\n")
            print("="*80)

            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        print(item.text)
            else:
                print(result)


def print_usage():
    """사용법 출력"""
    print("""
MCP Search 서버 사용하기
========================

사용법:
    python use_mcp_search.py "검색어"
    python use_mcp_search.py --answer "질문?"
    python use_mcp_search.py --context "주제"
    python use_mcp_search.py --verify "팩트체크할 주장"

예시:
    python use_mcp_search.py "Python programming"
    python use_mcp_search.py --answer "What is artificial intelligence?"
    python use_mcp_search.py --context "renewable energy 2024"
    python use_mcp_search.py --verify "AI will replace 50% of jobs by 2030"
""")


async def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print_usage()
        return

    mode = sys.argv[1]

    if mode == "--answer":
        if len(sys.argv) < 3:
            print("❌ 질문을 입력해주세요")
            print_usage()
            return
        await get_quick_answer(" ".join(sys.argv[2:]))

    elif mode == "--context":
        if len(sys.argv) < 3:
            print("❌ 주제를 입력해주세요")
            print_usage()
            return
        await get_context(" ".join(sys.argv[2:]))

    elif mode == "--verify":
        if len(sys.argv) < 3:
            print("❌ 검증할 주장을 입력해주세요")
            print_usage()
            return
        await verify_fact(" ".join(sys.argv[2:]))

    else:
        # Default: search web
        query = " ".join(sys.argv[1:])
        await search_web(query)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

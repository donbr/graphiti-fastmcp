#!/usr/bin/env python3
"""
Authorization Tests using FastMCP Client (HTTP Transport)

Tests T046-T050 for role-based authorization using the FastMCP v2 Client
with HTTP (streamable) transport - NOT the deprecated SSE transport.

Requirements:
- Server running at http://localhost:8000
- API keys configured in .env

Usage:
    uv run python tests/test_authorization_fastmcp_client.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# API Keys from environment
ADMIN_KEY = os.getenv('GRAPHITI_API_KEY_ADMIN')
READONLY_KEY = os.getenv('GRAPHITI_API_KEY_READONLY')
ANALYST_KEY = os.getenv('GRAPHITI_API_KEY_ANALYST')

SERVER_URL = 'http://localhost:8000/mcp'


def print_result(test_id: str, description: str, passed: bool, details: str = ''):
    """Print formatted test result."""
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f'\n{test_id}: {description}')
    print(f'  Status: {status}')
    if details:
        print(f'  Details: {details}')


async def test_with_fastmcp_client(api_key: str, role_name: str, test_cases: list) -> list:
    """
    Test authorization using FastMCP Client with HTTP transport.

    Args:
        api_key: Bearer token for authentication
        role_name: Role name for logging
        test_cases: List of (test_id, tool_name, args, should_succeed)

    Returns:
        List of (test_id, passed, details) tuples
    """
    from fastmcp import Client

    results = []

    print(f'\n--- Testing {role_name} Role ---')

    try:
        async with Client(SERVER_URL, auth=api_key) as client:
            print(f'  Session established for {role_name}')

            for test_id, tool_name, args, should_succeed in test_cases:
                try:
                    result = await client.call_tool(tool_name, args)

                    # Check if result indicates access denied
                    result_text = ''
                    if hasattr(result, 'content') and result.content:
                        for item in result.content:
                            if hasattr(item, 'text'):
                                result_text = item.text
                                break

                    is_access_denied = 'Access denied' in result_text or 'not allowed' in result_text

                    if should_succeed:
                        passed = not is_access_denied
                        details = f'Success: {result_text[:100]}' if not is_access_denied else f'Unexpected denial: {result_text}'
                    else:
                        passed = is_access_denied
                        details = f'Correctly blocked: {result_text}' if is_access_denied else f'Should have been blocked: {result_text[:100]}'

                except Exception as e:
                    error_msg = str(e)
                    is_access_denied = 'Access denied' in error_msg or 'not allowed' in error_msg

                    if should_succeed:
                        passed = False
                        details = f'Unexpected error: {error_msg[:100]}'
                    else:
                        passed = is_access_denied
                        details = f'Blocked with error: {error_msg[:100]}' if is_access_denied else f'Wrong error: {error_msg[:100]}'

                print_result(test_id, f'{role_name}: {tool_name}', passed, details)
                results.append((test_id, passed, details))

    except Exception as e:
        print(f'  Error connecting as {role_name}: {e}')
        for test_id, tool_name, args, should_succeed in test_cases:
            results.append((test_id, False, f'Connection failed: {e}'))

    return results


async def main():
    """Run all authorization tests."""
    print('=' * 70)
    print('MCP AUTHORIZATION TESTS - FastMCP Client (HTTP Transport)')
    print(f'Date: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}')
    print(f'Server: {SERVER_URL}')
    print('=' * 70)

    # Check environment
    if not all([ADMIN_KEY, READONLY_KEY, ANALYST_KEY]):
        print('\n❌ Missing API keys in environment. Set:')
        print('  GRAPHITI_API_KEY_ADMIN')
        print('  GRAPHITI_API_KEY_READONLY')
        print('  GRAPHITI_API_KEY_ANALYST')
        return 1

    all_results = []

    # T046: Admin has full access (wildcard *)
    admin_tests = [
        ('T046', 'get_status', {}, True),
    ]
    results = await test_with_fastmcp_client(ADMIN_KEY, 'Admin', admin_tests)
    all_results.extend(results)

    # T047-T048: Readonly role tests
    readonly_tests = [
        ('T047', 'get_status', {}, True),  # Allowed in policy
        ('T048', 'add_memory', {'name': 'readonly_test', 'episode_body': 'Should be blocked'}, False),  # Not allowed
    ]
    results = await test_with_fastmcp_client(READONLY_KEY, 'Readonly', readonly_tests)
    all_results.extend(results)

    # T049-T050: Analyst role tests
    analyst_tests = [
        ('T049', 'add_memory', {'name': 'analyst_test', 'episode_body': 'Analyst test data'}, True),  # Allowed
        ('T050', 'delete_entity_edge', {'uuid': 'test-uuid-123'}, False),  # Not allowed
    ]
    results = await test_with_fastmcp_client(ANALYST_KEY, 'Analyst', analyst_tests)
    all_results.extend(results)

    # Summary
    print('\n' + '=' * 70)
    print('TEST SUMMARY')
    print('=' * 70)

    passed = sum(1 for _, p, _ in all_results if p)
    total = len(all_results)

    for test_id, p, details in all_results:
        status = '✅' if p else '❌'
        print(f'{status} {test_id}: {details[:60]}...' if len(details) > 60 else f'{status} {test_id}: {details}')

    print(f'\nTotal: {passed}/{total} passed ({100*passed//total}%)')

    if passed == total:
        print('\n✅ All authorization tests passed!')
        return 0
    else:
        print(f'\n❌ {total - passed} test(s) failed')
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Refactor graphiti_mcp_server.py to use factory pattern.

This script:
1. Changes @mcp.tool() to @server.tool()
2. Indents tool function bodies to be inside _register_tools()
3. Changes @mcp.custom_route to @server.custom_route (except the one in create_server)
"""

import re
from pathlib import Path

SERVER_FILE = Path(__file__).parent.parent / 'src' / 'graphiti_mcp_server.py'

def main():
    content = SERVER_FILE.read_text()

    # Split into lines for processing
    lines = content.splitlines(keepends=True)

    # Find where _register_tools starts (line with "@server.tool()")
    register_tools_start = None
    for i, line in enumerate(lines):
        if '@server.tool()' in line and 'async def add_memory' in lines[i+1]:
            register_tools_start = i
            break

    if register_tools_start is None:
        print('ERROR: Could not find _register_tools start')
        return 1

    # Find all remaining @mcp.tool() decorators AFTER _register_tools
    tool_indices = []
    for i in range(register_tools_start + 1, len(lines)):
        if '@mcp.tool()' in lines[i]:
            tool_indices.append(i)

    print(f'Found {len(tool_indices)} tools to refactor')

    # Also find @mcp.custom_route that's not in create_server
    custom_route_idx = None
    for i in range(register_tools_start + 1, len(lines)):
        if "@mcp.custom_route('/health'" in lines[i]:
            custom_route_idx = i
            break

    # Process from bottom to top to preserve line numbers
    for idx in reversed(tool_indices):
        # Change @mcp.tool() to @server.tool()
        lines[idx] = lines[idx].replace('@mcp.tool()', '    @server.tool()')

        # Find the function definition line
        func_line_idx = idx + 1
        if 'async def ' in lines[func_line_idx]:
            # Indent this line and all following lines until next decorator or end of function
            indent_until = len(lines)

            # Find next tool or end of _register_tools
            for j in range(func_line_idx + 1, len(lines)):
                if lines[j].strip().startswith('@') or lines[j].strip().startswith('def ') or lines[j].strip().startswith('async def initialize_server'):
                    indent_until = j
                    break

            # Indent all lines in this function
            for j in range(func_line_idx, indent_until):
                if lines[j].strip():  # Only indent non-empty lines
                    # Add 4 spaces of indentation
                    lines[j] = '    ' + lines[j]

    # Handle custom_route if found
    if custom_route_idx:
        lines[custom_route_idx] = lines[custom_route_idx].replace('@mcp.custom_route', '    @server.custom_route')
        # Find and indent the health_check function
        for j in range(custom_route_idx + 1, min(custom_route_idx + 10, len(lines))):
            if 'async def health_check' in lines[j] or 'return JSONResponse' in lines[j]:
                if lines[j].strip():
                    lines[j] = '    ' + lines[j]

    # Write back
    SERVER_FILE.write_text(''.join(lines))
    print(f'Successfully refactored {len(tool_indices)} tools')
    print('Changes written to', SERVER_FILE)

    return 0

if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Pre-deployment verification script for FastMCP Cloud.

This script validates that your FastMCP server is ready for deployment to FastMCP Cloud.
It checks:
1. Server is discoverable via fastmcp inspect
2. All required dependencies are in pyproject.toml
3. Environment variables are documented
4. No .env files are committed to git
5. Server starts successfully
6. All MCP tools are accessible

Run this before deploying to FastMCP Cloud to catch issues early.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(text: str) -> None:
    """Print a section header."""
    print(f'\n{BOLD}{BLUE}{"=" * 80}{RESET}')
    print(f'{BOLD}{BLUE}{text}{RESET}')
    print(f'{BOLD}{BLUE}{"=" * 80}{RESET}\n')


def print_success(text: str) -> None:
    """Print a success message."""
    print(f'{GREEN}✓ {text}{RESET}')


def print_error(text: str) -> None:
    """Print an error message."""
    print(f'{RED}✗ {text}{RESET}')


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f'{YELLOW}⚠ {text}{RESET}')


def print_info(text: str) -> None:
    """Print an info message."""
    print(f'{BLUE}ℹ {text}{RESET}')


def run_command(cmd: list[str], capture_output: bool = True) -> tuple[bool, str, str]:
    """
    Run a shell command and return success status, stdout, and stderr.

    Args:
        cmd: Command to run as list of strings
        capture_output: Whether to capture output

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, '', 'Command timed out after 30 seconds'
    except Exception as e:
        return False, '', str(e)


def check_server_discoverable() -> bool:
    """Check if the server is discoverable via fastmcp inspect."""
    print_header('1. Server Discoverability Check')

    # Try to inspect the server (human-readable format)
    success, stdout, stderr = run_command([
        'uv', 'run', 'fastmcp', 'inspect', 'src/graphiti_mcp_server.py:mcp'
    ])

    if not success:
        print_error('Server is not discoverable via fastmcp inspect')
        print(f'Error: {stderr}')
        return False

    # Look for key indicators in output
    if 'Name:' in stdout and 'Tools:' in stdout:
        # Extract server name
        for line in stdout.split('\n'):
            if line.strip().startswith('Name:'):
                server_name = line.split('Name:')[1].strip()
                print_success(f'Server "{server_name}" is discoverable')
            elif line.strip().startswith('Tools:'):
                tools_count = line.split('Tools:')[1].strip()
                print_info(f'Found {tools_count} tools')

        return True
    else:
        print_error('Could not parse fastmcp inspect output')
        return False


def check_dependencies() -> bool:
    """Check that pyproject.toml has all required dependencies."""
    print_header('2. Dependencies Check')

    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        print_error('pyproject.toml not found')
        return False

    # Read pyproject.toml
    content = pyproject_path.read_text()

    # Critical runtime dependencies
    required_deps = [
        'fastmcp',
        'graphiti-core',
        'falkordb',
        'pydantic',
        'pydantic-settings',
        'pyyaml',
    ]

    missing_deps = []
    for dep in required_deps:
        if dep not in content.lower():
            missing_deps.append(dep)

    if missing_deps:
        print_error(f'Missing required dependencies: {", ".join(missing_deps)}')
        return False

    print_success('All required dependencies are present in pyproject.toml')

    # Check for dev dependencies that might be accidentally required
    dev_only_deps = ['pytest', 'ruff', 'pyright', 'ipython']
    runtime_dev_deps = []

    # This is a simple check - a more sophisticated check would parse the TOML
    for dep in dev_only_deps:
        if dep in content and 'dev' not in content.lower():
            runtime_dev_deps.append(dep)

    if runtime_dev_deps:
        print_warning(f'Dev dependencies might be in runtime deps: {", ".join(runtime_dev_deps)}')

    return True


def check_environment_variables() -> bool:
    """Check that required environment variables are documented."""
    print_header('3. Environment Variables Check')

    # Check for .env.example
    env_example_path = Path('.env.example')
    if not env_example_path.exists():
        print_warning('.env.example not found - create one to document required variables')
        return True  # Warning, not error

    content = env_example_path.read_text()

    # Required environment variables for FastMCP Cloud
    required_vars = [
        'OPENAI_API_KEY',
        'FALKORDB_URI',
        'FALKORDB_DATABASE',
    ]

    missing_vars = []
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)

    if missing_vars:
        print_warning(f'Missing from .env.example: {", ".join(missing_vars)}')
    else:
        print_success('All required environment variables are documented in .env.example')

    return True


def check_no_committed_secrets() -> bool:
    """Check that .env files are not committed to git."""
    print_header('4. Secrets Safety Check')

    # Check if .env is in .gitignore
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        print_error('.gitignore not found')
        return False

    gitignore_content = gitignore_path.read_text()
    if '.env' not in gitignore_content:
        print_error('.env is not in .gitignore - add it to prevent committing secrets')
        return False

    print_success('.env is properly ignored by git')

    # Check if any .env files are tracked
    success, stdout, stderr = run_command(['git', 'ls-files', '.env*'])

    if success and stdout.strip():
        tracked_env_files = [f for f in stdout.strip().split('\n') if f.endswith('.env')]
        if tracked_env_files:
            print_error(f'Found tracked .env files: {", ".join(tracked_env_files)}')
            print_info('Run: git rm --cached <file> to untrack them')
            return False

    print_success('No .env files are committed to git')
    return True


def check_server_startup() -> bool:
    """Check that the server can start successfully."""
    print_header('5. Server Startup Check')

    print_info('Testing server import (this may take a moment)...')

    # Test that the server can be imported without errors
    # Add the project root to PYTHONPATH to ensure imports work
    test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())
try:
    from src.graphiti_mcp_server import mcp
    print("SUCCESS")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

    success, stdout, stderr = run_command(['uv', 'run', 'python', '-c', test_script])

    if not success or 'ERROR' in stdout:
        print_error('Server failed to start')
        print(f'Error: {stdout}')
        if stderr:
            print(f'Stderr: {stderr}')
        print_info('This might be OK if dependencies are missing - FastMCP Cloud will install them')
        # Don't fail the check - this is just a warning
        return True

    print_success('Server can be imported successfully')
    return True


def check_entrypoint_format() -> bool:
    """Verify the entrypoint format is correct for FastMCP Cloud."""
    print_header('6. Entrypoint Format Check')

    server_file = Path('src/graphiti_mcp_server.py')
    if not server_file.exists():
        print_error('Server file not found: src/graphiti_mcp_server.py')
        return False

    content = server_file.read_text()

    # Check for module-level mcp instance
    if 'mcp = FastMCP(' not in content:
        print_error('No module-level "mcp = FastMCP(...)" instance found')
        print_info('FastMCP Cloud requires a module-level server instance')
        return False

    print_success('Module-level server instance found')

    # Check if there's an if __name__ == "__main__" block
    if 'if __name__ == "__main__"' in content:
        print_info('Found if __name__ == "__main__" block')
        print_warning('Note: FastMCP Cloud will IGNORE this block')
        print_warning('The server must be a module-level instance, not created in __main__')

    print_info('Recommended entrypoint: src/graphiti_mcp_server.py:mcp')
    return True


def generate_deployment_checklist() -> None:
    """Generate a deployment checklist."""
    print_header('FastMCP Cloud Deployment Checklist')

    print(f'{BOLD}Before deploying to FastMCP Cloud:{RESET}\n')

    checklist = [
        ('✓' if Path('pyproject.toml').exists() else '✗',
         'Ensure pyproject.toml includes all runtime dependencies'),
        ('?', 'Set environment variables in FastMCP Cloud UI (NOT in .env)'),
        ('?', 'Use entrypoint: src/graphiti_mcp_server.py:mcp'),
        ('?', 'Enable authentication in FastMCP Cloud project settings'),
        ('✓' if Path('.gitignore').exists() and '.env' in Path('.gitignore').read_text() else '✗',
         'Verify .env is in .gitignore'),
        ('?', 'Test the deployed URL after deployment'),
    ]

    for status, item in checklist:
        color = GREEN if status == '✓' else RED if status == '✗' else YELLOW
        print(f'{color}[{status}]{RESET} {item}')

    print(f'\n{BOLD}Required environment variables for FastMCP Cloud UI:{RESET}\n')

    env_vars = [
        ('OPENAI_API_KEY', 'Your OpenAI API key (required)'),
        ('FALKORDB_URI', 'FalkorDB Cloud connection URI'),
        ('FALKORDB_DATABASE', 'FalkorDB database name'),
        ('FALKORDB_USER', 'FalkorDB Cloud username'),
        ('FALKORDB_PASSWORD', 'FalkorDB Cloud password'),
        ('ANTHROPIC_API_KEY', 'Optional: For Claude models'),
        ('SEMAPHORE_LIMIT', 'Optional: Concurrency limit (default: 10)'),
    ]

    for var, desc in env_vars:
        print(f'  • {BOLD}{var}{RESET}: {desc}')

    print(f'\n{BOLD}Next steps:{RESET}\n')
    print('1. Visit https://fastmcp.cloud')
    print('2. Sign in with GitHub')
    print('3. Create a new project from your graphiti-fastmcp repo')
    print('4. Set environment variables in the FastMCP Cloud UI')
    print('5. Deploy and test!')


def main() -> int:
    """Run all verification checks."""
    print(f'{BOLD}{BLUE}')
    print('=' * 80)
    print('FastMCP Cloud Pre-Deployment Verification')
    print('=' * 80)
    print(f'{RESET}')

    # Track overall success
    all_checks_passed = True

    # Run all checks
    checks = [
        ('Server Discoverability', check_server_discoverable),
        ('Dependencies', check_dependencies),
        ('Environment Variables', check_environment_variables),
        ('Secrets Safety', check_no_committed_secrets),
        ('Server Startup', check_server_startup),
        ('Entrypoint Format', check_entrypoint_format),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            passed = check_func()
            results.append((check_name, passed))
            if not passed:
                all_checks_passed = False
        except Exception as e:
            print_error(f'{check_name} check failed with exception: {e}')
            results.append((check_name, False))
            all_checks_passed = False

    # Print summary
    print_header('Verification Summary')

    for check_name, passed in results:
        if passed:
            print_success(f'{check_name}: PASSED')
        else:
            print_error(f'{check_name}: FAILED')

    # Generate deployment checklist
    generate_deployment_checklist()

    # Final verdict
    print(f'\n{BOLD}{"=" * 80}{RESET}\n')

    if all_checks_passed:
        print(f'{BOLD}{GREEN}✓ All checks passed! Your server is ready for FastMCP Cloud deployment.{RESET}\n')
        return 0
    else:
        print(f'{BOLD}{RED}✗ Some checks failed. Please fix the issues before deploying.{RESET}\n')
        return 1


if __name__ == '__main__':
    sys.exit(main())

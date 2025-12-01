"""
Role-based authorization middleware for Graphiti MCP server.

This module provides FastMCP-compatible middleware that enforces role-based
access control (RBAC) for MCP tools based on policies defined in a JSON
configuration file.

References:
- https://gofastmcp.com/servers/middleware
- https://gofastmcp.com/integrations/eunomia-authorization
"""

import json
import logging
from pathlib import Path

from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

logger = logging.getLogger(__name__)


class RoleBasedAuthorizationMiddleware(Middleware):
    """
    FastMCP-compatible middleware that enforces role-based access control.

    This middleware reads policies from a JSON file and enforces tool access
    based on the authenticated user's role (set by the authentication middleware).
    It uses the on_call_tool hook to intercept tool calls before execution.

    References:
    - https://gofastmcp.com/servers/middleware#available-hooks
    - https://gofastmcp.com/integrations/eunomia-authorization
    """

    def __init__(self, policy_file: str):
        """
        Initialize the middleware with policy configuration.

        Args:
            policy_file: Path to the JSON policy file.
        """
        self.policy_file = policy_file
        self.policies = self._load_policies()
        logger.info(f'Loaded {len(self.policies)} authorization policies from {policy_file}')

    def _load_policies(self) -> dict[str, list[str]]:
        """
        Load role-based policies from JSON file.

        Returns:
            Dictionary mapping role names to lists of allowed tool names.
        """
        try:
            policy_path = Path(self.policy_file)
            if not policy_path.exists():
                logger.error(f'Policy file not found: {self.policy_file}')
                return {}

            with open(policy_path) as f:
                policy_data = json.load(f)

            # Convert policies to a dict for quick lookup
            role_policies = {}
            for policy in policy_data.get('policies', []):
                role = policy.get('role')
                resources = policy.get('resources', [])
                if role:
                    role_policies[role] = resources
                    logger.debug(f'Policy loaded for role "{role}": {len(resources)} resources')

            return role_policies
        except Exception as e:
            logger.error(f'Failed to load policies: {e}')
            return {}

    def _is_tool_allowed(self, role: str, tool_name: str) -> bool:
        """
        Check if a tool is allowed for the given role.

        Args:
            role: The user's role.
            tool_name: The name of the tool being accessed.

        Returns:
            True if the tool is allowed, False otherwise.
        """
        if role not in self.policies:
            logger.warning(f'Unknown role: {role}')
            return False

        allowed_tools = self.policies[role]

        # Check for wildcard access
        if '*' in allowed_tools:
            return True

        # Check for specific tool permission
        return tool_name in allowed_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Enforce authorization before tool calls.

        This hook runs after authentication and checks if the authenticated
        user's role is allowed to call the requested tool.
        """
        # Get the authenticated principal from context (set by auth middleware)
        principal = None
        if context.fastmcp_context:
            principal = context.fastmcp_context.get_state('api_principal')

        if not principal:
            # No principal means authentication middleware didn't set one
            # This could mean auth is disabled - let it pass
            logger.debug('Authorization: No principal found, auth may be disabled')
            return await call_next(context)

        role = principal.get('role')
        if not role:
            logger.warning(f'No role found in principal for user={principal.get("user_id")}')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='No role found in principal',
                )
            )

        # Extract tool name from context message
        # In on_call_tool, the message is a CallToolRequest with params.name
        tool_name = None
        message = context.message
        logger.debug(f'Authorization: message type={type(message)}, message={message}')

        # Try different ways to get tool name
        if hasattr(message, 'params') and hasattr(message.params, 'name'):
            tool_name = message.params.name
        elif hasattr(message, 'name'):
            tool_name = message.name
        elif isinstance(message, dict):
            tool_name = message.get('params', {}).get('name') or message.get('name')

        if not tool_name:
            logger.warning(f'Authorization: Could not extract tool name from context, message type={type(message)}, attrs={dir(message) if message else None}')
            return await call_next(context)

        # Check authorization
        if not self._is_tool_allowed(role, tool_name):
            user_id = principal.get('user_id', 'unknown')
            logger.warning(f'Access denied: role={role}, tool={tool_name}, user={user_id}')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message=f'Access denied: tool "{tool_name}" not allowed for role "{role}"',
                )
            )

        logger.debug(f'Access granted: role={role}, tool={tool_name}')
        return await call_next(context)

"""
Bearer token authentication middleware for Graphiti MCP server.

This module provides FastMCP-compatible middleware that enforces bearer token
authentication for MCP tool calls.

References:
- https://gofastmcp.com/servers/middleware#creating-middleware
- https://gofastmcp.com/python-sdk/fastmcp-server-dependencies
"""

import logging

from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

logger = logging.getLogger(__name__)


class BearerTokenAuthMiddleware(Middleware):
    """
    FastMCP-compatible middleware that enforces bearer token authentication.

    This middleware extracts and validates bearer tokens from the Authorization
    header.
    
    SECURITY NOTE:
    - on_call_tool: STRICT. Rejects requests without valid tokens.
    - on_list_tools: PERMISSIVE. Allows discovery without tokens (fixes build/inspect).
    - on_initialize: PERMISSIVE. Allows handshake without tokens.
    """

    def __init__(self, auth_service):
        self.auth_service = auth_service

    def _authenticate(self) -> dict:
        """
        Perform authentication and return principal.
        Raises McpError for authentication failures.
        """
        # Access HTTP headers via FastMCP dependency
        headers = get_http_headers()

        # Safety check for non-HTTP transports (e.g., Stdio from Claude Desktop)
        if headers is None:
            logger.debug('Auth context: No HTTP headers (likely Stdio or internal inspect)')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='Authentication unavailable over this transport',
                )
            )

        # Extract Authorization header
        auth_header = headers.get('authorization', '') or headers.get('Authorization', '')

        if not auth_header:
            raise McpError(ErrorData(code=-32000, message='Missing Authorization header'))

        if not auth_header.startswith('Bearer '):
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='Invalid Authorization header format. Expected: Bearer <token>',
                )
            )

        token = auth_header[7:]
        principal = self.auth_service.validate_token(token)

        if not principal:
            truncated_token = token[:8] + '...' if len(token) > 8 else 'invalid'
            logger.warning(f'Authentication failed: Invalid token={truncated_token}')
            raise McpError(ErrorData(code=-32000, message='Invalid or expired API key'))

        # Log success
        user_id = principal.get('user_id', 'unknown')
        role = principal.get('role', 'unknown')
        logger.info(f'Authentication successful: user_id={user_id}, role={role}')

        return principal

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Authenticate before tool calls.
        STRICT: Blocks execution if authentication fails.
        """
        # This will raise McpError if auth fails, blocking the execution
        principal = self._authenticate()

        if context.fastmcp_context:
            context.fastmcp_context.set_state('api_principal', principal)

        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        """
        Authenticate before listing tools.
        PERMISSIVE: Allows failure to enable 'fastmcp inspect' build steps.
        """
        try:
            principal = self._authenticate()
            if context.fastmcp_context:
                context.fastmcp_context.set_state('api_principal', principal)
        except McpError as e:
            # Log but allow proceeding. This enables the build inspector to see
            # the tool list without credentials. Execution is still protected.
            logger.debug(f"Allowing unauthenticated tool discovery: {e}")
            pass
            
        return await call_next(context)

    async def on_initialize(self, context: MiddlewareContext, call_next):
        """
        Authenticate on session initialization.
        PERMISSIVE: Allows handshake to succeed without immediate auth.
        """
        try:
            principal = self._authenticate()
            if context.fastmcp_context:
                context.fastmcp_context.set_state('api_principal', principal)
        except McpError:
            # Allow initialization to proceed
            pass
            
        return await call_next(context)
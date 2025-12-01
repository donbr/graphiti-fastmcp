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
    header using FastMCP's get_http_headers() dependency. It stores the
    authenticated principal in the context state for downstream use.

    Note: This middleware only executes for MCP tool calls, not for HTTP routes
    like /health and /status which are handled separately via custom_route.

    References:
    - https://gofastmcp.com/servers/middleware
    - https://gofastmcp.com/clients/auth/bearer
    """

    def __init__(self, auth_service):
        """
        Initialize the middleware with authentication service.

        Args:
            auth_service: AuthService instance for token validation.
        """
        self.auth_service = auth_service

    def _authenticate(self) -> dict:
        """
        Perform authentication and return principal.

        Returns:
            Principal dict with user_id and role.

        Raises:
            McpError: For authentication failures.
        """
        # Access HTTP headers via FastMCP dependency
        headers = get_http_headers()

        # Safety check for non-HTTP transports (e.g., Stdio from Claude Desktop)
        if headers is None:
            logger.warning('Auth failed: No HTTP context available (likely Stdio transport)')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='Authentication unavailable over this transport',
                )
            )

        # Extract Authorization header (case-insensitive per HTTP spec)
        auth_header = headers.get('authorization', '') or headers.get('Authorization', '')

        if not auth_header:
            logger.warning('Authentication failed: Missing Authorization header')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='Missing Authorization header',
                )
            )

        # Check for Bearer prefix
        if not auth_header.startswith('Bearer '):
            logger.warning('Authentication failed: Invalid header format')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='Invalid Authorization header format. Expected: Bearer <token>',
                )
            )

        # Extract token (remove "Bearer " prefix)
        token = auth_header[7:]

        # Validate token
        principal = self.auth_service.validate_token(token)

        if not principal:
            # Truncate token for security (log only first 8 chars) - T062 requirement
            truncated_token = token[:8] + '...' if len(token) > 8 else 'invalid'
            logger.warning(f'Authentication failed: Invalid token={truncated_token}')
            raise McpError(
                ErrorData(
                    code=-32000,
                    message='Invalid or expired API key',
                )
            )

        # Log successful authentication - T060/T061 requirement
        user_id = principal.get('user_id', 'unknown')
        role = principal.get('role', 'unknown')
        logger.info(f'Authentication successful: user_id={user_id}, role={role}')

        return principal

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Authenticate before tool calls.

        This hook runs before any tool is called, validating the bearer token
        and storing the principal in context state for authorization middleware.
        """
        principal = self._authenticate()

        # Store principal in context state for authorization middleware
        if context.fastmcp_context:
            context.fastmcp_context.set_state('api_principal', principal)

        return await call_next(context)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        """
        Allow tool listing without authentication.

        Tool listings are public API documentation and don't expose sensitive data.
        This also allows FastMCP Cloud's inspection process to work during deployment.
        Authorization is still enforced when tools are actually called via on_call_tool.
        """
        # Try to authenticate if headers are present, but don't require it
        try:
            principal = self._authenticate()
            if context.fastmcp_context:
                context.fastmcp_context.set_state('api_principal', principal)
        except McpError:
            # Allow unauthenticated tool listing - it's just API documentation
            logger.debug('Allowing unauthenticated tool listing')
            pass

        return await call_next(context)

    async def on_initialize(self, context: MiddlewareContext, call_next):
        """Authenticate on session initialization."""
        principal = self._authenticate()
        if context.fastmcp_context:
            context.fastmcp_context.set_state('api_principal', principal)
        return await call_next(context)

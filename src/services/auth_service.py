"""
Authentication service for Graphiti MCP server.

This module provides API key validation and principal extraction
for bearer token authentication.
"""


class AuthService:
    """
    Service for validating API keys and extracting user principals.

    This service manages API key validation for bearer token authentication,
    mapping API keys to user principals with role information.
    """

    def __init__(self, api_keys: dict[str, dict]):
        """
        Initialize the AuthService with API key mappings.

        Args:
            api_keys: Dictionary mapping API keys to principal dictionaries.
                     Each principal dict should contain 'user_id' and 'role'.
        """
        self.api_keys = api_keys

    def validate_token(self, token: str) -> dict | None:
        """
        Validate an API token and return the associated principal.

        Args:
            token: The API key token to validate.

        Returns:
            Dictionary containing user_id and role if valid, None otherwise.
        """
        return self.api_keys.get(token)

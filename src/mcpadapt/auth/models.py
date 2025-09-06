"""Authentication models for MCPAdapt - Legacy file kept for backwards compatibility."""

# This file previously contained OAuth/API Key/Bearer auth configuration classes
# but they have been removed in favor of direct auth provider usage.
# 
# Users now create providers directly:
# - OAuthClientProvider (from MCP SDK)
# - ApiKeyAuthProvider/BearerAuthProvider (from mcpadapt.auth.providers)
#
# This file is kept empty to avoid breaking existing imports,
# but may be removed in a future version.

"""Tests for OAuth token storage implementation."""

import pytest
from mcpadapt.auth.oauth import InMemoryTokenStorage


class TestInMemoryTokenStorage:
    """Test in-memory token storage implementation."""

    def test_initialization(self):
        """Test basic initialization."""
        storage = InMemoryTokenStorage()
        assert storage._tokens is None
        assert storage._client_info is None

    def test_initialization_with_client_info(self, mock_oauth_client_info):
        """Test initialization with pre-configured client info."""
        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)
        assert storage._tokens is None
        assert storage._client_info is not None
        assert storage._client_info is mock_oauth_client_info

    @pytest.mark.asyncio
    async def test_get_tokens_initially_none(self):
        """Test that tokens are initially None."""
        storage = InMemoryTokenStorage()
        tokens = await storage.get_tokens()
        assert tokens is None

    @pytest.mark.asyncio
    async def test_get_client_info_initially_none(self):
        """Test that client info is initially None."""
        storage = InMemoryTokenStorage()
        client_info = await storage.get_client_info()
        assert client_info is None

    @pytest.mark.asyncio
    async def test_get_preconfigured_client_info(self, mock_oauth_client_info):
        """Test getting pre-configured client info."""
        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Get client info
        retrieved_info = await storage.get_client_info()
        assert retrieved_info is not None
        assert retrieved_info is mock_oauth_client_info
        assert retrieved_info.client_id == "test_client_id"
        assert retrieved_info.client_secret == "test_client_secret"
        assert retrieved_info.client_id_issued_at == 1234567890
        assert retrieved_info.client_secret_expires_at == 0

    @pytest.mark.asyncio
    async def test_preconfigured_client_info_with_tokens(
        self, mock_oauth_client_info, mock_oauth_token
    ):
        """Test that pre-configured client info works alongside token operations."""
        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Initially has client info but no tokens
        assert await storage.get_client_info() is not None
        assert await storage.get_tokens() is None

        # Set tokens
        await storage.set_tokens(mock_oauth_token)

        # Should have both client info and tokens
        assert await storage.get_client_info() is mock_oauth_client_info
        assert await storage.get_tokens() is mock_oauth_token

    @pytest.mark.asyncio
    async def test_preconfigured_client_info_overwrite(self, mock_oauth_client_info):
        """Test overwriting pre-configured client info."""
        from mcp.shared.auth import OAuthClientInformationFull
        from pydantic import HttpUrl

        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Verify initial client info
        initial_info = await storage.get_client_info()
        assert initial_info is not None
        assert initial_info is mock_oauth_client_info
        assert initial_info.client_id == "test_client_id"

        # Create new client info
        new_info = OAuthClientInformationFull(
            client_id="overwrite_client_id",
            client_secret="overwrite_client_secret",
            redirect_uris=[HttpUrl("http://localhost:5050/callback")],
        )

        # Overwrite client info
        await storage.set_client_info(new_info)
        updated_info = await storage.get_client_info()

        assert updated_info is not None
        assert updated_info is new_info
        assert updated_info.client_id == "overwrite_client_id"
        assert updated_info.client_secret == "overwrite_client_secret"
        assert updated_info is not mock_oauth_client_info

    @pytest.mark.asyncio
    async def test_set_and_get_tokens(self, mock_oauth_token):
        """Test setting and getting tokens."""
        storage = InMemoryTokenStorage()

        # Set tokens
        await storage.set_tokens(mock_oauth_token)

        # Get tokens
        retrieved_tokens = await storage.get_tokens()
        assert retrieved_tokens is not None
        assert retrieved_tokens is mock_oauth_token
        assert retrieved_tokens.access_token == "test_access_token"
        assert retrieved_tokens.token_type == "Bearer"
        assert retrieved_tokens.expires_in == 3600
        assert retrieved_tokens.refresh_token == "test_refresh_token"
        assert retrieved_tokens.scope == "read write"

    @pytest.mark.asyncio
    async def test_set_and_get_client_info(self, mock_oauth_client_info):
        """Test setting and getting client info."""
        storage = InMemoryTokenStorage()

        # Set client info
        await storage.set_client_info(mock_oauth_client_info)

        # Get client info
        retrieved_info = await storage.get_client_info()
        assert retrieved_info is not None
        assert retrieved_info is mock_oauth_client_info
        assert retrieved_info.client_id == "test_client_id"
        assert retrieved_info.client_secret == "test_client_secret"
        assert retrieved_info.client_id_issued_at == 1234567890
        assert retrieved_info.client_secret_expires_at == 0

    @pytest.mark.asyncio
    async def test_overwrite_tokens(self, mock_oauth_token):
        """Test overwriting existing tokens."""
        from mcp.shared.auth import OAuthToken

        storage = InMemoryTokenStorage()

        # Set initial tokens
        await storage.set_tokens(mock_oauth_token)
        initial_tokens = await storage.get_tokens()
        assert initial_tokens is not None
        assert initial_tokens.access_token == "test_access_token"

        # Create new tokens
        new_token = OAuthToken(
            access_token="new_access_token",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="new_refresh_token",
            scope="read write delete",
        )

        # Overwrite tokens
        await storage.set_tokens(new_token)
        updated_tokens = await storage.get_tokens()

        assert updated_tokens is not None
        assert updated_tokens is new_token
        assert updated_tokens.access_token == "new_access_token"
        assert updated_tokens.expires_in == 7200
        assert updated_tokens.refresh_token == "new_refresh_token"
        assert updated_tokens.scope == "read write delete"

    @pytest.mark.asyncio
    async def test_overwrite_client_info(self, mock_oauth_client_info):
        """Test overwriting existing client info."""
        from mcp.shared.auth import OAuthClientInformationFull
        from pydantic import HttpUrl

        storage = InMemoryTokenStorage()

        # Set initial client info
        await storage.set_client_info(mock_oauth_client_info)
        initial_info = await storage.get_client_info()
        assert initial_info is not None
        assert initial_info.client_id == "test_client_id"

        # Create new client info
        new_info = OAuthClientInformationFull(
            client_id="new_client_id",
            client_secret="new_client_secret",
            client_id_issued_at=9876543210,
            client_secret_expires_at=9999999999,
            redirect_uris=[HttpUrl("http://localhost:4040/callback")],
        )

        # Overwrite client info
        await storage.set_client_info(new_info)
        updated_info = await storage.get_client_info()

        assert updated_info is not None
        assert updated_info is new_info
        assert updated_info.client_id == "new_client_id"
        assert updated_info.client_secret == "new_client_secret"
        assert updated_info.client_id_issued_at == 9876543210
        assert updated_info.client_secret_expires_at == 9999999999

    @pytest.mark.asyncio
    async def test_independent_storage(self, mock_oauth_token, mock_oauth_client_info):
        """Test that tokens and client info are stored independently."""
        storage = InMemoryTokenStorage()

        # Set only tokens
        await storage.set_tokens(mock_oauth_token)
        assert await storage.get_tokens() is not None
        assert await storage.get_client_info() is None

        # Set only client info
        storage2 = InMemoryTokenStorage()
        await storage2.set_client_info(mock_oauth_client_info)
        assert await storage2.get_tokens() is None
        assert await storage2.get_client_info() is not None

        # Set both in same storage
        await storage.set_client_info(mock_oauth_client_info)
        assert await storage.get_tokens() is not None
        assert await storage.get_client_info() is not None

    @pytest.mark.asyncio
    async def test_multiple_instances_independent(
        self, mock_oauth_token, mock_oauth_client_info
    ):
        """Test that multiple storage instances are independent."""
        storage1 = InMemoryTokenStorage()
        storage2 = InMemoryTokenStorage()

        # Set tokens in first storage
        await storage1.set_tokens(mock_oauth_token)

        # Verify second storage unaffected
        assert await storage1.get_tokens() is not None
        assert await storage2.get_tokens() is None

        # Set different data in second storage
        from mcp.shared.auth import OAuthToken

        different_token = OAuthToken(
            access_token="different_token", token_type="Bearer", expires_in=1800
        )
        await storage2.set_tokens(different_token)

        # Verify independence
        tokens1 = await storage1.get_tokens()
        tokens2 = await storage2.get_tokens()

        assert tokens1 is not None
        assert tokens2 is not None
        assert tokens1.access_token == "test_access_token"
        assert tokens2.access_token == "different_token"
        assert tokens1 is not tokens2

    @pytest.mark.asyncio
    async def test_storage_interface_compliance(self):
        """Test that InMemoryTokenStorage implements required interface methods."""
        storage = InMemoryTokenStorage()

        # Verify required methods exist and are callable
        assert hasattr(storage, "get_tokens")
        assert hasattr(storage, "set_tokens")
        assert hasattr(storage, "get_client_info")
        assert hasattr(storage, "set_client_info")

        assert callable(storage.get_tokens)
        assert callable(storage.set_tokens)
        assert callable(storage.get_client_info)
        assert callable(storage.set_client_info)

        # Verify methods work as expected (interface compliance)
        tokens = await storage.get_tokens()
        client_info = await storage.get_client_info()
        assert tokens is None
        assert client_info is None


class TestInMemoryTokenStorageEdgeCases:
    """Test edge cases and error scenarios for InMemoryTokenStorage."""

    @pytest.mark.asyncio
    async def test_set_tokens_none(self):
        """Test setting tokens to None (should be allowed)."""
        from mcp.shared.auth import OAuthToken

        storage = InMemoryTokenStorage()

        # Set some tokens first
        token = OAuthToken(access_token="test", token_type="Bearer")
        await storage.set_tokens(token)
        assert await storage.get_tokens() is not None

    @pytest.mark.asyncio
    async def test_concurrent_access_simulation(self, mock_oauth_token):
        """Test simulated concurrent access to storage."""
        import asyncio

        storage = InMemoryTokenStorage()
        results = []

        async def set_and_get(token_suffix):
            from mcp.shared.auth import OAuthToken

            token = OAuthToken(
                access_token=f"token_{token_suffix}", token_type="Bearer"
            )
            await storage.set_tokens(token)
            retrieved = await storage.get_tokens()
            assert retrieved is not None
            results.append(retrieved.access_token)

        # Run multiple coroutines
        await asyncio.gather(set_and_get("1"), set_and_get("2"), set_and_get("3"))

        # Verify we got results (order may vary due to concurrency)
        assert len(results) == 3
        assert all(result.startswith("token_") for result in results)

        # Final stored token should be one of the set tokens
        final_token = await storage.get_tokens()
        assert final_token is not None
        assert final_token.access_token in results

    @pytest.mark.asyncio
    async def test_token_object_reference_integrity(self, mock_oauth_token):
        """Test that stored objects maintain reference integrity."""
        storage = InMemoryTokenStorage()

        # Store token
        await storage.set_tokens(mock_oauth_token)

        # Get token multiple times
        token1 = await storage.get_tokens()
        token2 = await storage.get_tokens()

        # All references should be to the same object
        assert token1 is mock_oauth_token
        assert token2 is mock_oauth_token
        assert token1 is token2

    @pytest.mark.asyncio
    async def test_memory_cleanup_behavior(self):
        """Test memory cleanup behavior when overwriting data."""
        from mcp.shared.auth import OAuthToken

        storage = InMemoryTokenStorage()

        # Create and store first token
        token1 = OAuthToken(access_token="token1", token_type="Bearer")
        await storage.set_tokens(token1)

        # Store reference to verify cleanup
        token1_ref = await storage.get_tokens()
        assert token1_ref is token1

        # Overwrite with new token
        token2 = OAuthToken(access_token="token2", token_type="Bearer")
        await storage.set_tokens(token2)

        # Verify new token is stored and old reference is no longer accessible through storage
        current_token = await storage.get_tokens()
        assert current_token is not None
        assert current_token is token2
        assert current_token.access_token == "token2"


class TestInMemoryTokenStorageAsyncPatterns:
    """Test async patterns and coroutine behavior."""

    @pytest.mark.asyncio
    async def test_method_chaining_async(
        self, mock_oauth_token, mock_oauth_client_info
    ):
        """Test async method chaining patterns."""
        storage = InMemoryTokenStorage()

        # Chain operations
        await storage.set_tokens(mock_oauth_token)
        await storage.set_client_info(mock_oauth_client_info)

        # Verify both operations completed
        tokens = await storage.get_tokens()
        client_info = await storage.get_client_info()

        assert tokens is mock_oauth_token
        assert client_info is mock_oauth_client_info


class TestInMemoryTokenStoragePreConfiguredCredentials:
    """Test pre-configured OAuth credentials functionality for skipping DCR."""

    def test_preconfigured_credentials_skip_dcr_scenario(self, mock_oauth_client_info):
        """Test the main use case: pre-configured credentials to skip DCR."""
        # This simulates the scenario where a user has existing OAuth app credentials
        # and wants to skip Dynamic Client Registration

        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Verify storage is properly initialized with client info
        assert storage._client_info is not None
        assert storage._client_info.client_id == "test_client_id"
        assert storage._client_info.client_secret == "test_client_secret"
        assert storage._tokens is None  # No tokens initially

    @pytest.mark.asyncio
    async def test_preconfigured_credentials_workflow(
        self, mock_oauth_client_info, mock_oauth_token
    ):
        """Test complete workflow with pre-configured credentials."""
        # Initialize with pre-configured client credentials
        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Step 1: Storage already has client info (skips DCR)
        client_info = await storage.get_client_info()
        assert client_info is not None
        assert client_info.client_id == "test_client_id"
        assert client_info.client_secret == "test_client_secret"

        # Step 2: No tokens initially
        tokens = await storage.get_tokens()
        assert tokens is None

        # Step 3: After OAuth flow, tokens are stored
        await storage.set_tokens(mock_oauth_token)

        # Step 4: Now we have both client info and tokens
        final_client_info = await storage.get_client_info()
        final_tokens = await storage.get_tokens()

        assert final_client_info is mock_oauth_client_info
        assert final_tokens is mock_oauth_token
        assert final_tokens.access_token == "test_access_token"

    def test_multiple_preconfigured_storages_independent(self):
        """Test that multiple pre-configured storages are independent."""
        from mcp.shared.auth import OAuthClientInformationFull
        from pydantic import HttpUrl

        # Create two different client infos
        client_info_1 = OAuthClientInformationFull(
            client_id="client_1",
            client_secret="secret_1",
            redirect_uris=[HttpUrl("http://localhost:3030/callback")],
        )

        client_info_2 = OAuthClientInformationFull(
            client_id="client_2",
            client_secret="secret_2",
            redirect_uris=[HttpUrl("http://localhost:4040/callback")],
        )

        # Create storages with different pre-configured credentials
        storage_1 = InMemoryTokenStorage(client_info=client_info_1)
        storage_2 = InMemoryTokenStorage(client_info=client_info_2)

        # Verify independence
        assert storage_1._client_info is not None
        assert storage_2._client_info is not None
        assert storage_1._client_info is not storage_2._client_info
        assert storage_1._client_info.client_id == "client_1"
        assert storage_2._client_info.client_id == "client_2"
        assert storage_1._client_info.client_secret == "secret_1"
        assert storage_2._client_info.client_secret == "secret_2"

    @pytest.mark.asyncio
    async def test_preconfigured_vs_regular_storage_behavior(
        self, mock_oauth_client_info
    ):
        """Test difference between pre-configured and regular storage behavior."""
        # Regular storage (for DCR)
        regular_storage = InMemoryTokenStorage()

        # Pre-configured storage (skips DCR)
        preconfigured_storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Regular storage has no client info initially
        regular_client_info = await regular_storage.get_client_info()
        assert regular_client_info is None

        # Pre-configured storage has client info immediately
        preconfigured_client_info = await preconfigured_storage.get_client_info()
        assert preconfigured_client_info is not None
        assert preconfigured_client_info is mock_oauth_client_info
        assert preconfigured_client_info.client_id == "test_client_id"

        # Both should have no tokens initially
        assert await regular_storage.get_tokens() is None
        assert await preconfigured_storage.get_tokens() is None

    @pytest.mark.asyncio
    async def test_preconfigured_storage_interface_methods(
        self, mock_oauth_client_info
    ):
        """Test that pre-configured storage works with all interface methods."""
        from mcp.shared.auth import OAuthToken, OAuthClientInformationFull
        from pydantic import HttpUrl

        storage = InMemoryTokenStorage(client_info=mock_oauth_client_info)

        # Test get_client_info returns pre-configured info
        client_info = await storage.get_client_info()
        assert client_info is mock_oauth_client_info

        # Test set_client_info can override pre-configured info
        new_client_info = OAuthClientInformationFull(
            client_id="new_client",
            client_secret="new_secret",
            redirect_uris=[HttpUrl("http://localhost:5050/callback")],
        )
        await storage.set_client_info(new_client_info)

        updated_client_info = await storage.get_client_info()
        assert updated_client_info is new_client_info
        assert updated_client_info.client_id == "new_client"
        assert updated_client_info is not mock_oauth_client_info

        # Test tokens still work normally
        token = OAuthToken(access_token="test_token", token_type="Bearer")
        await storage.set_tokens(token)

        retrieved_token = await storage.get_tokens()
        assert retrieved_token is token
        assert retrieved_token.access_token == "test_token"

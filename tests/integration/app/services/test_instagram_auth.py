import logging

import pytest

from app.config import settings
from app.services.instagram_auth import (
    InstagramTokenManager,
    get_refreshed_instagram_token,
)

logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    not (
        settings.instagram_app_id
        and settings.instagram_app_secret
        and settings.access_token
    ),
    reason="Instagram credentials not configured - add INSTAGRAM_APP_SECRET to .env",
)
class TestInstagramTokenManagerIntegration:
    """Real integration tests for Instagram token management using actual API endpoints."""

    def test_token_validation_with_real_api(self):
        """Test token validation with real Instagram API."""
        token_manager = InstagramTokenManager(
            app_id=settings.instagram_app_id,
            app_secret=settings.instagram_app_secret,
            current_token=settings.access_token,
        )

        # Test with real API
        is_valid = token_manager.is_token_valid()
        logger.info(f"Token validation result: {is_valid}")

        # Should return a boolean
        assert isinstance(is_valid, bool)

    def test_get_token_info_with_real_api(self):
        """Test getting token info from real Facebook API."""
        token_manager = InstagramTokenManager(
            app_id=settings.instagram_app_id,
            app_secret=settings.instagram_app_secret,
            current_token=settings.access_token,
        )

        # Get token info from real API
        token_info = token_manager.get_token_info()
        logger.info(f"Token info: {token_info}")

        # Should return dict with info or None
        assert token_info is None or isinstance(token_info, dict)

        if token_info:
            # If we get info, check for expected fields
            logger.info(
                f"Token expires in: {token_info.get('expires_in', 'unknown')} seconds"
            )

    def test_token_refresh_with_real_api(self):
        """Test token refresh with real Instagram/Facebook API."""
        token_manager = InstagramTokenManager(
            app_id=settings.instagram_app_id,
            app_secret=settings.instagram_app_secret,
            current_token=settings.access_token,
        )

        # Try to refresh token
        new_token = token_manager.refresh_long_lived_token()
        logger.info(f"Token refresh result: {'Success' if new_token else 'Failed'}")

        # Should return new token string or None
        assert new_token is None or isinstance(new_token, str)

        if new_token:
            # If refresh succeeded, token should be different or same (if already refreshed recently)
            logger.info(f"New token length: {len(new_token)}")
            assert len(new_token) > 50  # Instagram tokens are long

    def test_ensure_valid_token_workflow(self):
        """Test the complete ensure_valid_token workflow."""
        token_manager = InstagramTokenManager(
            app_id=settings.instagram_app_id,
            app_secret=settings.instagram_app_secret,
            current_token=settings.access_token,
        )

        # This should either return current token or refresh it
        try:
            valid_token = token_manager.ensure_valid_token()
            logger.info("Successfully ensured valid token")

            # Should return a token string
            assert isinstance(valid_token, str)
            assert len(valid_token) > 50

        except Exception as e:
            # If it fails, log the error for debugging
            logger.error(f"Token validation workflow failed: {e}")
            # Re-raise to fail the test
            raise

    def test_convenience_function(self):
        """Test the convenience function with real API."""
        try:
            valid_token = get_refreshed_instagram_token(
                app_id=settings.instagram_app_id,
                app_secret=settings.instagram_app_secret,
                current_token=settings.access_token,
            )

            logger.info("Convenience function succeeded")
            assert isinstance(valid_token, str)
            assert len(valid_token) > 50

        except Exception as e:
            logger.error(f"Convenience function failed: {e}")
            raise


@pytest.mark.skipif(
    not settings.access_token, reason="ACCESS_TOKEN not configured in .env"
)
def test_token_manager_initialization():
    """Test token manager can be initialized with current config."""
    # Test that we can create a token manager
    token_manager = InstagramTokenManager(
        app_id=settings.instagram_app_id or "test_app_id",
        app_secret=settings.instagram_app_secret or "test_secret",
        current_token=settings.access_token,
    )

    assert token_manager.app_id is not None
    assert token_manager.current_token == settings.access_token
    assert token_manager.secret_name == "my-env-secrets"
    assert token_manager.token_key == "ACCESS_TOKEN"


def test_instagram_token_manager_without_credentials():
    """Test token manager behavior when credentials are missing."""
    # This should work even without real credentials
    token_manager = InstagramTokenManager(
        app_id="fake_app_id", app_secret="fake_secret", current_token="fake_token"
    )

    # Token validation should fail gracefully
    is_valid = token_manager.is_token_valid()
    assert is_valid is False  # Should return False for invalid credentials

    # Token refresh should fail gracefully
    new_token = token_manager.refresh_long_lived_token()
    assert new_token is None  # Should return None for failed refresh

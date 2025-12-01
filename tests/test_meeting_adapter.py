"""Tests for the Meeting license verification functionality.

This module tests the MeetingAdapter class and its license verification
against the Meeting backend API. All HTTP requests are mocked.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from jupiter.server.meeting_adapter import (
    MeetingAdapter,
    MeetingLicenseCheckResult,
    MeetingLicenseStatus,
)


@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root for testing."""
    return tmp_path


class TestMeetingLicenseStatus:
    """Tests for the MeetingLicenseStatus enum."""

    def test_status_values(self):
        """Verify all expected status values exist."""
        assert MeetingLicenseStatus.VALID.value == "valid"
        assert MeetingLicenseStatus.INVALID.value == "invalid"
        assert MeetingLicenseStatus.NETWORK_ERROR.value == "network_error"
        assert MeetingLicenseStatus.CONFIG_ERROR.value == "config_error"


class TestMeetingLicenseCheckResult:
    """Tests for the MeetingLicenseCheckResult dataclass."""

    def test_to_dict(self):
        """Verify to_dict serializes all fields correctly."""
        result = MeetingLicenseCheckResult(
            status=MeetingLicenseStatus.VALID,
            message="License valid",
            device_key="TEST_KEY",
            http_status=200,
            authorized=True,
            device_type="Jupiter",
            token_count=10,
            checked_at="2025-06-01T12:00:00",
            meeting_base_url="https://meeting.ygsoft.fr/api",
            device_type_expected="Jupiter",
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["status"] == "valid"
        assert result_dict["message"] == "License valid"
        assert result_dict["device_key"] == "TEST_KEY"
        assert result_dict["http_status"] == 200
        assert result_dict["authorized"] is True
        assert result_dict["device_type"] == "Jupiter"
        assert result_dict["token_count"] == 10
        assert result_dict["checked_at"] == "2025-06-01T12:00:00"
        assert result_dict["meeting_base_url"] == "https://meeting.ygsoft.fr/api"
        assert result_dict["device_type_expected"] == "Jupiter"


class TestMeetingAdapterCheckLicense:
    """Tests for the check_jupiter_devicekey method."""

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_valid_license(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: License is VALID when all conditions are met."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
            base_url="https://meeting.ygsoft.fr/api",
            device_type_expected="Jupiter",
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.VALID
        assert result.authorized is True
        assert result.device_type == "Jupiter"
        assert result.token_count == 10
        assert result.http_status == 200

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_device_not_found_404(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: License is INVALID when device not found (HTTP 404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="UNKNOWN_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("UNKNOWN_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert result.http_status == 404
        assert "not found" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_device_not_authorized(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: License is INVALID when authorized == false."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": False,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert result.authorized is False
        assert "not authorized" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_wrong_device_type(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: License is INVALID when device_type != expected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "SomeOtherDevice",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
            device_type_expected="Jupiter",
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert result.device_type == "SomeOtherDevice"
        assert "device_type" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_zero_tokens(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: License is INVALID when token_count == 0."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 0,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert result.token_count == 0
        assert "token_count" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_network_error(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: NETWORK_ERROR when requests raises an exception."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.NETWORK_ERROR
        assert "network error" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_timeout_error(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: NETWORK_ERROR when request times out."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.NETWORK_ERROR
        assert "network error" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_invalid_json_response(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: INVALID when JSON is malformed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert "json" in result.message.lower()

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_missing_fields_in_response(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: INVALID when JSON fields are missing or None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            # Missing: authorized, device_type, token_count
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        # Should handle gracefully without crashing
        assert result.status == MeetingLicenseStatus.INVALID
        # authorized is False when missing
        assert result.authorized is False

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_http_500_error(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: INVALID when Meeting API returns HTTP 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert result.http_status == 500
        assert "500" in result.message

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_http_401_unauthorized(self, mock_get: MagicMock, mock_project_root: Path):
        """Test case: INVALID when Meeting API returns HTTP 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        result = adapter.check_jupiter_devicekey("TEST_KEY")
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert result.http_status == 401


class TestMeetingAdapterNoDeviceKey:
    """Tests for MeetingAdapter when no device_key is configured."""

    def test_no_device_key_config_error(self, mock_project_root: Path):
        """Test case: CONFIG_ERROR when device_key is None."""
        adapter = MeetingAdapter(
            device_key=None,
            project_root=mock_project_root,
        )
        
        result = adapter.get_license_status()
        
        assert result.status == MeetingLicenseStatus.CONFIG_ERROR
        assert "device_key" in result.message.lower()

    def test_is_enabled_without_key(self, mock_project_root: Path):
        """Test that is_enabled returns False when no device_key."""
        adapter = MeetingAdapter(
            device_key=None,
            project_root=mock_project_root,
        )
        
        assert adapter.is_enabled() is False

    def test_is_licensed_without_key(self, mock_project_root: Path):
        """Test that is_licensed returns False when no device_key."""
        adapter = MeetingAdapter(
            device_key=None,
            project_root=mock_project_root,
        )
        
        assert adapter.is_licensed() is False


class TestMeetingAdapterLegacyInterface:
    """Tests for backward compatibility with existing check_license() method."""

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_check_license_valid(self, mock_get: MagicMock, mock_project_root: Path):
        """Test legacy check_license() returns correct dict for valid license."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        status = adapter.check_license()
        
        assert status["is_licensed"] is True
        assert status["status"] == "active"
        assert status["session_active"] is True

    def test_check_license_trial_mode(self, mock_project_root: Path):
        """Test legacy check_license() returns trial mode info when unlicensed."""
        adapter = MeetingAdapter(
            device_key=None,
            project_root=mock_project_root,
        )
        
        status = adapter.check_license()
        
        assert status["is_licensed"] is False
        assert status["status"] == "limited"
        assert status["session_active"] is True
        assert status["session_remaining_seconds"] is not None


class TestMeetingAdapterRefreshLicense:
    """Tests for the refresh_license method."""

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_refresh_updates_status(self, mock_get: MagicMock, mock_project_root: Path):
        """Test that refresh_license updates internal state."""
        # First call returns valid
        mock_response_valid = MagicMock()
        mock_response_valid.status_code = 200
        mock_response_valid.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        
        # Second call returns invalid (tokens depleted)
        mock_response_invalid = MagicMock()
        mock_response_invalid.status_code = 200
        mock_response_invalid.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 0,
        }
        
        mock_get.return_value = mock_response_valid
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
        )
        
        assert adapter.is_licensed() is True
        
        # Now simulate refresh with new response
        mock_get.return_value = mock_response_invalid
        result = adapter.refresh_license()
        
        assert result.status == MeetingLicenseStatus.INVALID
        assert adapter.is_licensed() is False


class TestMeetingAdapterCustomConfig:
    """Tests for custom configuration parameters."""

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_custom_base_url(self, mock_get: MagicMock, mock_project_root: Path):
        """Test that custom base_url is used in requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        custom_url = "https://custom.meeting.server/api"
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
            base_url=custom_url,
        )
        
        # Verify the request was made to the custom URL
        mock_get.assert_called()
        called_url = mock_get.call_args[0][0]
        assert called_url.startswith(custom_url)

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_custom_device_type(self, mock_get: MagicMock, mock_project_root: Path):
        """Test that custom device_type_expected is used for validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "CustomType",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
            device_type_expected="CustomType",
        )
        
        result = adapter.get_license_status()
        assert result.status == MeetingLicenseStatus.VALID

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_custom_timeout(self, mock_get: MagicMock, mock_project_root: Path):
        """Test that custom timeout is passed to requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
            timeout_seconds=15.0,
        )
        
        # Verify timeout was passed
        mock_get.assert_called()
        _, kwargs = mock_get.call_args
        assert kwargs.get("timeout") == 15.0

    @patch("jupiter.server.meeting_adapter.requests.get")
    def test_auth_token_in_header(self, mock_get: MagicMock, mock_project_root: Path):
        """Test that auth_token is added to request headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_key": "TEST_KEY",
            "authorized": True,
            "device_type": "Jupiter",
            "token_count": 10,
        }
        mock_get.return_value = mock_response
        
        adapter = MeetingAdapter(
            device_key="TEST_KEY",
            project_root=mock_project_root,
            auth_token="my-secret-token",
        )
        
        # Verify auth header was passed
        mock_get.assert_called()
        _, kwargs = mock_get.call_args
        headers = kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my-secret-token"

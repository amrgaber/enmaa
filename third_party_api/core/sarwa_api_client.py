"""Sarwa Life Insurance API client for check status updates.

Handles authentication (token management) and check status change calls.
Token is stored in ir.config_parameter and automatically refreshed on expiry.

Flow:
    1. Try with stored token
    2. If 401 (expired/invalid) → call /odoo/signin to get new token
    3. Retry /odoo/changestatus with new token
"""

import logging
from datetime import datetime

import requests

_logger = logging.getLogger(__name__)

# System parameter keys for Sarwa API config
SARWA_BASE_URL_PARAM = "third_party_api.sarwa_base_url"
SARWA_USERNAME_PARAM = "third_party_api.sarwa_username"
SARWA_PASSWORD_PARAM = "third_party_api.sarwa_password"
SARWA_TOKEN_PARAM = "third_party_api.sarwa_token"
SARWA_TOKEN_EXPIRY_PARAM = "third_party_api.sarwa_token_expiry"

# Request timeout in seconds
REQUEST_TIMEOUT = 30


class SarwaApiClient:
    """Client for Sarwa Life Insurance Check Status API."""

    def __init__(self, env):
        """Initialize with Odoo environment to access config parameters.

        Args:
            env: Odoo environment (self.env from a model)
        """
        self.env = env
        params = self.env["ir.config_parameter"].sudo()
        self.base_url = (params.get_param(SARWA_BASE_URL_PARAM) or "").rstrip("/")
        self.username = params.get_param(SARWA_USERNAME_PARAM) or ""
        self.password = params.get_param(SARWA_PASSWORD_PARAM) or ""

    def _get_stored_token(self):
        """Get stored token if still valid (not expired).

        Returns:
            str: Valid token or None if expired/missing
        """
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_param(SARWA_TOKEN_PARAM) or ""
        expiry_str = params.get_param(SARWA_TOKEN_EXPIRY_PARAM) or ""

        if token and expiry_str:
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
                if expiry > datetime.now():
                    return token
            except (ValueError, TypeError):
                pass

        return None

    def _authenticate(self):
        """Call /odoo/signin to get a new token.

        Stores the new token and expiry in ir.config_parameter.

        Returns:
            str: New access token

        Raises:
            Exception: If authentication fails
        """
        if not self.base_url or not self.username or not self.password:
            raise Exception(
                "Sarwa API not configured. Please set Base URL, Username, "
                "and Password in Accounting > Configuration > Third Party API > Sarwa API Settings."
            )

        url = f"{self.base_url}/odoo/signin"
        payload = {
            "username": self.username,
            "password": self.password,
        }

        _logger.info("Sarwa API: Authenticating with %s", url)

        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Sarwa API connection error: {e}") from e

        if data.get("status") == "SUCCESS" and data.get("token"):
            # Store token and expiry
            params = self.env["ir.config_parameter"].sudo()
            params.set_param(SARWA_TOKEN_PARAM, data["token"])
            params.set_param(SARWA_TOKEN_EXPIRY_PARAM, data.get("expire_date", ""))
            _logger.info(
                "Sarwa API: Authentication successful, token valid until %s",
                data.get("expire_date"),
            )
            return data["token"]

        error_msg = data.get("message", "Unknown authentication error")
        raise Exception(f"Sarwa API authentication failed: {error_msg}")

    def _get_token(self):
        """Get a valid token — from storage or by authenticating.

        Returns:
            str: Valid access token
        """
        token = self._get_stored_token()
        if token:
            return token
        return self._authenticate()

    def _call_change_status(self, token, odoo_check_code, status_id, collection_amount):
        """Make the actual HTTP call to /odoo/changestatus.

        Args:
            token: Access token
            odoo_check_code: The check code to update
            status_id: Numeric status ID (2-8)
            collection_amount: Amount (required > 0 for status 2 and 8)

        Returns:
            dict: API response data
        """
        url = f"{self.base_url}/odoo/changestatus"
        payload = {
            "token": token,
            "odoo_check_code": odoo_check_code,
            "status_id": status_id,
            "collection_amount": collection_amount,
        }

        _logger.info(
            "Sarwa API: Calling changestatus - check=%s, status_id=%s, amount=%s",
            odoo_check_code,
            status_id,
            collection_amount,
        )

        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "ERROR", "code": 500, "message": f"Connection error: {e}"}

    def change_status(self, odoo_check_code, status_id, collection_amount=0):
        """Update check status via Sarwa API with automatic token refresh.

        Flow:
            1. Get stored token (or authenticate if none)
            2. Call changestatus
            3. If 401 → re-authenticate → retry changestatus

        Args:
            odoo_check_code: The check code (cheque_no from payment)
            status_id: Numeric status ID (2=Collected, 3=Cashed, etc.)
            collection_amount: Amount for status 2 and 8 (default: 0)

        Returns:
            dict: API response with status, code, message, etc.
        """
        # Step 1: Get token
        token = self._get_token()

        # Step 2: Call changestatus
        result = self._call_change_status(
            token, odoo_check_code, status_id, collection_amount
        )

        # Step 3: If token expired (401), re-authenticate and retry
        if result.get("code") == 401:
            _logger.warning(
                "Sarwa API: Token expired/invalid for check %s, re-authenticating...",
                odoo_check_code,
            )
            token = self._authenticate()
            result = self._call_change_status(
                token, odoo_check_code, status_id, collection_amount
            )

        # Log result
        if result.get("status") == "SUCCESS":
            _logger.info(
                "Sarwa API: Successfully updated check %s to status %s",
                odoo_check_code,
                status_id,
            )
        else:
            _logger.error(
                "Sarwa API: Failed to update check %s - %s",
                odoo_check_code,
                result.get("message", "Unknown error"),
            )

        return result

    def _call_change_finance_bank(self, token, odoo_cheque_id, finance_bank):
        """Make the actual HTTP call to /odoo/changefinbank.

        Args:
            token: Access token
            odoo_cheque_id: The cheque ID (payment.id) to update
            finance_bank: The finance bank name string

        Returns:
            dict: API response data
        """
        url = f"{self.base_url}/odoo/changefinbank"
        payload = {
            "token": token,
            "odoo_cheque_id": odoo_cheque_id,
            "finance_bank": finance_bank,
        }

        _logger.info(
            "Sarwa API: Calling changefinbank - cheque_id=%s, finance_bank=%s",
            odoo_cheque_id,
            finance_bank,
        )

        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "ERROR", "code": 500, "message": f"Connection error: {e}"}

    def change_finance_bank(self, odoo_cheque_id, finance_bank):
        """Update finance bank via Sarwa API with automatic token refresh.

        Flow:
            1. Get stored token (or authenticate if none)
            2. Call changefinbank
            3. If 401 → re-authenticate → retry changefinbank

        Args:
            odoo_cheque_id: The cheque ID (payment.id)
            finance_bank: The finance bank name string

        Returns:
            dict: API response with status, code, message, etc.
        """
        # Step 1: Get token
        token = self._get_token()

        # Step 2: Call changefinbank
        result = self._call_change_finance_bank(token, odoo_cheque_id, finance_bank)

        # Step 3: If token expired (401), re-authenticate and retry
        if result.get("code") == 401:
            _logger.warning(
                "Sarwa API: Token expired/invalid for cheque %s, re-authenticating...",
                odoo_cheque_id,
            )
            token = self._authenticate()
            result = self._call_change_finance_bank(token, odoo_cheque_id, finance_bank)

        # Log result
        if result.get("status") == "SUCCESS":
            _logger.info(
                "Sarwa API: Successfully updated cheque %s finance bank to '%s'",
                odoo_cheque_id,
                finance_bank,
            )
        else:
            _logger.error(
                "Sarwa API: Failed to update cheque %s finance bank - %s",
                odoo_cheque_id,
                result.get("message", "Unknown error"),
            )

        return result

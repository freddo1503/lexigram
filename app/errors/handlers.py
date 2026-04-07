"""
Error handling utilities for the Lexigram application.

This module provides utilities for handling errors, including retry mechanisms
for transient errors and error classification helpers.
"""

import logging
from typing import Any, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.errors.exceptions import (
    APIError,
    AuthenticationError,
    ClientError,
    DataParsingError,
    LexigramError,
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def classify_http_error(response: requests.Response, api_name: str = "API") -> APIError:
    """Classify an HTTP error based on the response status code."""
    status_code: int = response.status_code  # ty: ignore[invalid-assignment]
    error_message = "%s request failed with status code %s" % (api_name, status_code)

    try:
        error_details = response.json()
    except Exception:
        error_details = {"response_text": response.text}

    details = {
        "status_code": status_code,
        "url": response.url,
        "method": response.request.method if response.request else "UNKNOWN",
        "error_details": error_details,
    }

    if status_code == 401:
        return AuthenticationError(
            f"{error_message}: Authentication failed", details=details
        )
    elif status_code == 403:
        return AuthenticationError(
            f"{error_message}: Permission denied", details=details
        )
    elif status_code == 404:
        return ResourceNotFoundError(
            f"{error_message}: Resource not found", details=details
        )
    elif status_code == 422:
        return ValidationError(f"{error_message}: Validation failed", details=details)
    elif status_code == 429:
        retry_after = response.headers.get("Retry-After")
        retry_seconds = (
            int(retry_after) if retry_after and retry_after.isdigit() else None
        )
        return RateLimitError(
            f"{error_message}: Rate limit exceeded",
            details=details,
            retry_after=retry_seconds,
        )
    elif 400 <= status_code < 500:
        return ClientError(f"{error_message}: Client error", details=details)
    elif 500 <= status_code < 600:
        return ServerError(f"{error_message}: Server error", details=details)
    else:
        return APIError(f"{error_message}: Unknown error", details=details)


# Re-export tenacity's retry with project defaults for convenience.
# Usage: @retry(stop=stop_after_attempt(3))
# The raw tenacity decorators are re-exported so callers don't need to import tenacity directly.
__all__ = [
    "classify_http_error",
    "retry",
    "stop_after_attempt",
    "wait_exponential",
    "safe_request",
    "safe_parse_json",
]


def safe_request(
    method: str,
    url: str,
    api_name: str = "API",
    max_attempts: int = 3,
    **kwargs: Any,
) -> requests.Response:
    """Make a safe HTTP request with retries and proper error handling."""

    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=1, max=60),
        reraise=True,
    )
    def _make_request() -> requests.Response:
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            raise classify_http_error(e.response, api_name)
        except requests.ConnectionError as e:
            raise NetworkError(
                "Connection error while connecting to %s: %s" % (api_name, e),
                original_exception=e,
            )
        except requests.Timeout as e:
            raise TimeoutError(
                "Timeout while connecting to %s: %s" % (api_name, e),
                original_exception=e,
            )
        except requests.RequestException as e:
            raise APIError(
                "Error while connecting to %s: %s" % (api_name, e),
                original_exception=e,
            )
        except Exception as e:
            raise LexigramError(
                "Unexpected error while connecting to %s: %s" % (api_name, e),
                original_exception=e,
            )

    return _make_request()


def safe_parse_json(
    response: requests.Response, api_name: str = "API"
) -> Dict[str, Any]:
    """
    Safely parse JSON from a response with proper error handling.

    Args:
        response: HTTP response object.
        api_name: Name of the API for error messages.

    Returns:
        Parsed JSON data as a dictionary.

    Raises:
        DataParsingError: If JSON parsing fails.
    """
    try:
        return response.json()
    except ValueError as e:
        raise DataParsingError(
            f"Failed to parse {api_name} response as JSON",
            original_exception=e,
            details={"response_text": response.text},
        )

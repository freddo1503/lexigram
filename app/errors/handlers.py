"""
Error handling utilities for the Lexigram application.

This module provides utilities for handling errors, including retry mechanisms
for transient errors and error classification helpers.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

import requests

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

# Type variables for better type hinting
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def classify_http_error(response: requests.Response, api_name: str = "API") -> APIError:
    """
    Classify an HTTP error based on the response status code.

    Args:
        response: The HTTP response object.
        api_name: The name of the API for error messages.

    Returns:
        An appropriate APIError subclass instance.
    """
    status_code = response.status_code
    error_message = f"{api_name} request failed with status code {status_code}"

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


def retry(
    max_attempts: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    retryable_status_codes: Optional[List[int]] = None,
) -> Callable[[F], F]:
    """
    Decorator that retries a function call on specified exceptions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        retry_delay: Initial delay between retries in seconds.
        backoff_factor: Factor by which the delay increases with each retry.
        max_delay: Maximum delay between retries in seconds.
        retryable_exceptions: List of exception types that should trigger a retry.
        retryable_status_codes: List of HTTP status codes that should trigger a retry.

    Returns:
        The decorated function.
    """
    if retryable_exceptions is None:
        retryable_exceptions = [
            NetworkError,
            TimeoutError,
            ServerError,
            RateLimitError,
            requests.ConnectionError,
            requests.Timeout,
            requests.HTTPError,
        ]

    if retryable_status_codes is None:
        retryable_status_codes = [408, 429, 500, 502, 503, 504]

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = retry_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(retryable_exceptions) as e:
                    last_exception = e

                    # Check if it's a rate limit error with a specific retry time
                    if isinstance(e, RateLimitError) and e.retry_after is not None:
                        current_delay = e.retry_after

                    # Check if it's an HTTP error with a retryable status code
                    if isinstance(e, requests.HTTPError):
                        response = getattr(e, "response", None)
                        if (
                            response
                            and response.status_code not in retryable_status_codes
                        ):
                            raise

                        # Check for Retry-After header
                        retry_after = (
                            response.headers.get("Retry-After") if response else None
                        )
                        if retry_after and retry_after.isdigit():
                            current_delay = int(retry_after)

                    # Log the error and retry information
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed with error: {e}. "
                            f"Retrying in {current_delay:.2f} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay = min(current_delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {e}"
                        )
                        raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            return None  # To satisfy the type checker

        return cast(F, wrapper)

    return decorator


def safe_request(
    method: str,
    url: str,
    api_name: str = "API",
    max_attempts: int = 3,
    **kwargs: Any,
) -> requests.Response:
    """
    Make a safe HTTP request with retries and proper error handling.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: URL to request.
        api_name: Name of the API for error messages.
        max_attempts: Maximum number of retry attempts.
        **kwargs: Additional arguments to pass to requests.request.

    Returns:
        The HTTP response.

    Raises:
        APIError: If the request fails after all retry attempts.
    """

    @retry(max_attempts=max_attempts)
    def _make_request() -> requests.Response:
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            raise classify_http_error(e.response, api_name)
        except requests.ConnectionError as e:
            raise NetworkError(
                f"Connection error while connecting to {api_name}: {e}",
                original_exception=e,
            )
        except requests.Timeout as e:
            raise TimeoutError(
                f"Timeout while connecting to {api_name}: {e}",
                original_exception=e,
            )
        except requests.RequestException as e:
            raise APIError(
                f"Error while connecting to {api_name}: {e}",
                original_exception=e,
            )
        except Exception as e:
            raise LexigramError(
                f"Unexpected error while connecting to {api_name}: {e}",
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

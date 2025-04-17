"""
Custom exceptions for the Lexigram application.

This module defines a hierarchy of custom exceptions for different types of errors
that can occur in the Lexigram application, allowing for more precise error handling.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LexigramError(Exception):
    """Base exception for all Lexigram-specific errors."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.original_exception = original_exception
        self.details = details or {}

        # Log the error with details
        log_message = f"{message}"
        if original_exception:
            log_message += f" Original exception: {original_exception}"
        if details:
            log_message += f" Details: {details}"

        logger.error(log_message)

        super().__init__(message)


# API-related exceptions
class APIError(LexigramError):
    """Base exception for all API-related errors."""

    pass


class AuthenticationError(APIError):
    """Exception raised when authentication with an API fails."""

    pass


class RateLimitError(APIError):
    """Exception raised when an API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, original_exception, details)


class NetworkError(APIError):
    """Exception raised when a network-related error occurs."""

    pass


class TimeoutError(NetworkError):
    """Exception raised when an API request times out."""

    pass


class ServerError(APIError):
    """Exception raised when a server-side error occurs."""

    pass


class ClientError(APIError):
    """Exception raised when a client-side error occurs."""

    pass


class ResourceNotFoundError(ClientError):
    """Exception raised when a requested resource is not found."""

    pass


class ValidationError(ClientError):
    """Exception raised when input validation fails."""

    pass


# Data-related exceptions
class DataError(LexigramError):
    """Base exception for all data-related errors."""

    pass


class DataParsingError(DataError):
    """Exception raised when parsing data fails."""

    pass


class DataIntegrityError(DataError):
    """Exception raised when data integrity is compromised."""

    pass


# Service-specific exceptions
class LegifranceError(APIError):
    """Base exception for all Legifrance API-related errors."""

    pass


class InstagramError(APIError):
    """Base exception for all Instagram API-related errors."""

    pass


class DynamoDBError(APIError):
    """Base exception for all DynamoDB-related errors."""

    pass


class CrewError(LexigramError):
    """Exception raised when an error occurs in the crew processing."""

    pass


# Processing-related exceptions
class ProcessingError(LexigramError):
    """Exception raised when processing fails."""

    pass


class PublishingError(ProcessingError):
    """Exception raised when publishing content fails."""

    pass

"""
Custom exception classes for the application.
"""


class EasymartException(Exception):
    """Base exception for all Easymart errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProductNotFoundException(EasymartException):
    """Raised when a product is not found"""
    pass


class SearchException(EasymartException):
    """Raised when search fails"""
    pass


class IndexingException(EasymartException):
    """Raised when indexing fails"""
    pass


class SessionException(EasymartException):
    """Raised for session-related errors"""
    pass


class ExternalServiceException(EasymartException):
    """Raised when external service (Node.js, Shopify) fails"""
    pass

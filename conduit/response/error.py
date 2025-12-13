"""
Error Wrapper

Creates standardized error responses for RPC handlers.
"""

from typing import Any, Optional, Dict
from enum import IntEnum


class ErrorCode(IntEnum):
    """Standard error codes."""
    
    # General errors (1xxx)
    UNKNOWN = 1000
    INTERNAL = 1001
    TIMEOUT = 1002
    CANCELLED = 1003
    
    # Validation errors (2xxx)
    VALIDATION = 2000
    MISSING_FIELD = 2001
    INVALID_TYPE = 2002
    INVALID_VALUE = 2003
    
    # Authentication errors (3xxx)
    AUTH_REQUIRED = 3000
    AUTH_FAILED = 3001
    AUTH_EXPIRED = 3002
    PERMISSION_DENIED = 3003
    
    # RPC errors (4xxx)
    METHOD_NOT_FOUND = 4000
    INVALID_PARAMS = 4001
    EXECUTION_ERROR = 4002
    
    # Connection errors (5xxx)
    CONNECTION_ERROR = 5000
    DISCONNECTED = 5001
    RECONNECTING = 5002
    
    # Rate limiting (6xxx)
    RATE_LIMITED = 6000
    QUOTA_EXCEEDED = 6001


class Error:
    """
    Error wrapper for RPC handlers.
    
    Usage:
        error = Error()
        
        @server.rpc
        async def my_method(request):
            if something_wrong:
                return error("Something went wrong")
            if validation_failed:
                return error("Invalid input", code=ErrorCode.VALIDATION)
    
    The wrapped response will have:
    - success: False
    - error: The error message
    - code: Optional error code
    """
    
    def __call__(
        self,
        message: str,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
            code: Optional error code (use ErrorCode enum)
            details: Optional additional error details
            
        Returns:
            Dict with success=False and error info
        """
        result = {
            "success": False,
            "error": message,
        }
        
        if code is not None:
            result["code"] = code
            
        if details:
            result["details"] = details
            
        return result
    
    def validation(
        self,
        message: str,
        field: Optional[str] = None,
        expected: Optional[str] = None,
        received: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create a validation error response.
        
        Args:
            message: Error message
            field: Field that failed validation
            expected: Expected value/type
            received: Actual value/type received
            
        Returns:
            Validation error response
        """
        details = {}
        if field:
            details["field"] = field
        if expected:
            details["expected"] = expected
        if received is not None:
            details["received"] = str(received)
            
        return self(
            message,
            code=ErrorCode.VALIDATION,
            details=details if details else None
        )
    
    def not_found(self, resource: str, identifier: Any = None) -> Dict[str, Any]:
        """
        Create a not found error response.
        
        Args:
            resource: Type of resource not found
            identifier: Optional identifier that wasn't found
            
        Returns:
            Not found error response
        """
        if identifier:
            message = f"{resource} not found: {identifier}"
        else:
            message = f"{resource} not found"
            
        return self(message, code=ErrorCode.METHOD_NOT_FOUND)
    
    def permission_denied(self, action: str = "") -> Dict[str, Any]:
        """
        Create a permission denied error response.
        
        Args:
            action: Action that was denied
            
        Returns:
            Permission denied error response
        """
        if action:
            message = f"Permission denied: {action}"
        else:
            message = "Permission denied"
            
        return self(message, code=ErrorCode.PERMISSION_DENIED)
    
    def internal(self, message: str = "Internal server error") -> Dict[str, Any]:
        """
        Create an internal error response.
        
        Args:
            message: Error message
            
        Returns:
            Internal error response
        """
        return self(message, code=ErrorCode.INTERNAL)
    
    def timeout(self, operation: str = "") -> Dict[str, Any]:
        """
        Create a timeout error response.
        
        Args:
            operation: Operation that timed out
            
        Returns:
            Timeout error response
        """
        if operation:
            message = f"Operation timed out: {operation}"
        else:
            message = "Operation timed out"
            
        return self(message, code=ErrorCode.TIMEOUT)
    
    def rate_limited(self, retry_after: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a rate limited error response.
        
        Args:
            retry_after: Seconds until retry is allowed
            
        Returns:
            Rate limited error response
        """
        details = {"retry_after": retry_after} if retry_after else None
        return self("Rate limit exceeded", code=ErrorCode.RATE_LIMITED, details=details)

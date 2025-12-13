"""
Response Wrapper

Wraps RPC return values in a standardized success response format.
"""

from typing import Any, Optional, Dict
from pydantic import BaseModel


class Response:
    """
    Response wrapper for RPC handlers.
    
    Usage:
        response = Response()
        
        @server.rpc
        async def my_method(request):
            result = do_something()
            return response(result)
    
    The wrapped response will have:
    - success: True
    - data: The wrapped value (serialized if Pydantic model)
    """
    
    def __call__(
        self,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Wrap data in a success response.
        
        Args:
            data: The response data. Can be:
                  - A Pydantic BaseModel (will be serialized to dict)
                  - Any JSON-serializable value
            metadata: Optional metadata to include in response
            
        Returns:
            Dict with success=True and serialized data
        """
        # Serialize Pydantic models
        if isinstance(data, BaseModel):
            serialized_data = data.model_dump()
        elif hasattr(data, '__dict__') and not isinstance(data, (dict, list, str, int, float, bool, type(None))):
            # Handle dataclasses and similar
            serialized_data = vars(data)
        else:
            serialized_data = data
        
        result = {
            "success": True,
            "data": serialized_data,
        }
        
        if metadata:
            result["metadata"] = metadata
            
        return result
    
    def ok(self, data: Any = None, message: str = "") -> Dict[str, Any]:
        """
        Create a simple success response.
        
        Args:
            data: Optional response data
            message: Optional success message
            
        Returns:
            Success response dict
        """
        result = {"success": True}
        
        if data is not None:
            if isinstance(data, BaseModel):
                result["data"] = data.model_dump()
            else:
                result["data"] = data
                
        if message:
            result["message"] = message
            
        return result
    
    def with_pagination(
        self,
        data: list,
        total: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Create a paginated response.
        
        Args:
            data: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page
            
        Returns:
            Paginated response dict
        """
        return {
            "success": True,
            "data": data,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": page * page_size < total,
                "has_prev": page > 1,
            }
        }

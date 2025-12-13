"""
RPC Dispatcher

Dispatches RPC requests to handlers and handles responses.
"""

import asyncio
import traceback
from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError

from .registry import RPCRegistry, RPCMethod
from ..response import Response, Error


class RPCDispatcher:
    """
    Dispatches RPC requests to registered handlers.
    
    Handles parameter validation, execution, and response wrapping.
    """
    
    def __init__(self, registry: RPCRegistry):
        """
        Initialize dispatcher.
        
        Args:
            registry: RPC registry containing registered methods
        """
        self.registry = registry
        self._response = Response()
        self._error = Error()
    
    async def dispatch(
        self,
        method: str,
        params: Dict[str, Any],
        authenticated: bool = False
    ) -> Dict[str, Any]:
        """
        Dispatch an RPC request to the appropriate handler.
        
        Args:
            method: RPC method name
            params: Method parameters
            authenticated: Whether the caller is authenticated
            
        Returns:
            Response dictionary (success or error)
        """
        # Handle built-in listall method
        if method == "listall":
            return self._handle_listall()
        
        # Find the method
        rpc_method = self.registry.get(method)
        
        if rpc_method is None:
            return self._error.not_found("RPC method", method)
        
        # Check authentication requirement
        if rpc_method.requires_auth and not authenticated:
            return self._error.permission_denied(f"Method '{method}' requires authentication")
        
        try:
            # Validate and convert parameters using Pydantic model if available
            validated_params = self._validate_params(rpc_method, params)
            
            # Execute the handler
            result = await self._execute_handler(rpc_method, validated_params)
            
            # If handler returns a dict with 'success' key, it's already formatted
            if isinstance(result, dict) and 'success' in result:
                return result
            
            # Otherwise wrap it
            return self._response(result)
            
        except ValidationError as e:
            # Pydantic validation error
            error_details = []
            for err in e.errors():
                error_details.append({
                    "field": ".".join(str(loc) for loc in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"],
                })
            return self._error(
                f"Validation error in {method}",
                code=2000,  # VALIDATION
                details={"errors": error_details}
            )
            
        except TypeError as e:
            # Parameter type error
            return self._error.validation(str(e))
            
        except asyncio.CancelledError:
            raise  # Re-raise cancellation
            
        except Exception as e:
            # Unexpected error
            tb = traceback.format_exc()
            return self._error.internal(f"Error in {method}: {str(e)}")
    
    def _validate_params(
        self,
        rpc_method: RPCMethod,
        params: Dict[str, Any]
    ) -> Any:
        """
        Validate parameters against the method's expected types.
        
        Args:
            rpc_method: The RPC method
            params: Raw parameters
            
        Returns:
            Validated parameters (may be Pydantic model instance)
        """
        if rpc_method.pydantic_model is not None:
            # Validate using Pydantic model
            return rpc_method.pydantic_model(**params)
        
        # Return as-is if no model
        return params
    
    async def _execute_handler(
        self,
        rpc_method: RPCMethod,
        params: Any
    ) -> Any:
        """
        Execute the RPC handler.
        
        Args:
            rpc_method: The RPC method
            params: Validated parameters
            
        Returns:
            Handler result
        """
        handler = rpc_method.handler
        
        # If params is a Pydantic model, pass it as single argument
        if isinstance(params, BaseModel):
            result = handler(params)
        elif isinstance(params, dict):
            result = handler(**params)
        else:
            result = handler(params)
        
        # Await if coroutine
        if asyncio.iscoroutine(result):
            result = await result
        
        return result
    
    def _handle_listall(self) -> Dict[str, Any]:
        """
        Handle the built-in listall method.
        
        Returns:
            List of available RPC methods
        """
        method_info = self.registry.get_method_info()
        return self._response({
            "methods": method_info,
            "count": len(method_info),
        })
    
    async def dispatch_batch(
        self,
        requests: list[Dict[str, Any]],
        authenticated: bool = False
    ) -> list[Dict[str, Any]]:
        """
        Dispatch multiple RPC requests.
        
        Args:
            requests: List of request dicts with 'method' and 'params'
            authenticated: Whether caller is authenticated
            
        Returns:
            List of response dicts
        """
        results = []
        for request in requests:
            method = request.get("method", "")
            params = request.get("params", {})
            result = await self.dispatch(method, params, authenticated)
            results.append(result)
        return results

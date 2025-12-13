"""
RPC Registry

Stores and manages registered RPC methods on the server side.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, get_type_hints
from dataclasses import dataclass, field
from pydantic import BaseModel


@dataclass
class RPCMethod:
    """Represents a registered RPC method."""
    
    name: str
    handler: Callable
    description: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)
    return_type: str = "Any"
    requires_auth: bool = True
    pydantic_model: Optional[type] = None  # Parameter model if using Pydantic
    
    def to_info_dict(self) -> Dict[str, Any]:
        """Convert to info dictionary for discovery."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "requires_auth": self.requires_auth,
        }


class RPCRegistry:
    """
    Registry for RPC methods.
    
    Stores all registered methods and provides lookup functionality.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._methods: Dict[str, RPCMethod] = {}
        
        # Register built-in listall method
        self._register_builtin_methods()
    
    def _register_builtin_methods(self) -> None:
        """Register built-in RPC methods."""
        # The listall method is handled specially by the dispatcher
        pass
    
    def register(
        self,
        handler: Callable,
        name: Optional[str] = None,
        requires_auth: bool = True
    ) -> RPCMethod:
        """
        Register an RPC method.
        
        Args:
            handler: The async function to register
            name: Optional method name (defaults to function name)
            requires_auth: Whether authentication is required
            
        Returns:
            The registered RPCMethod
        """
        # Use function name if not provided
        method_name = name or handler.__name__
        
        # Get docstring
        description = inspect.getdoc(handler) or ""
        
        # Extract parameter info from type hints
        parameters = {}
        pydantic_model = None
        
        try:
            hints = get_type_hints(handler)
            
            for param_name, param_type in hints.items():
                if param_name == 'return':
                    continue
                    
                # Check if it's a Pydantic model
                if isinstance(param_type, type) and issubclass(param_type, BaseModel):
                    pydantic_model = param_type
                    # Extract fields from the model
                    for field_name, field_info in param_type.model_fields.items():
                        field_type = field_info.annotation
                        type_name = getattr(field_type, '__name__', str(field_type))
                        parameters[field_name] = type_name
                else:
                    type_name = getattr(param_type, '__name__', str(param_type))
                    parameters[param_name] = type_name
            
            # Get return type
            return_type = "Any"
            if 'return' in hints:
                return_hint = hints['return']
                return_type = getattr(return_hint, '__name__', str(return_hint))
                
        except Exception:
            # If type hint extraction fails, continue without them
            pass
        
        # Create method entry
        method = RPCMethod(
            name=method_name,
            handler=handler,
            description=description,
            parameters=parameters,
            return_type=return_type,
            requires_auth=requires_auth,
            pydantic_model=pydantic_model,
        )
        
        self._methods[method_name] = method
        return method
    
    def unregister(self, name: str) -> bool:
        """
        Unregister an RPC method.
        
        Args:
            name: Method name to unregister
            
        Returns:
            True if method was removed, False if not found
        """
        if name in self._methods:
            del self._methods[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[RPCMethod]:
        """
        Get an RPC method by name.
        
        Args:
            name: Method name
            
        Returns:
            RPCMethod if found, None otherwise
        """
        return self._methods.get(name)
    
    def exists(self, name: str) -> bool:
        """Check if a method exists."""
        return name in self._methods
    
    def list_methods(self) -> List[RPCMethod]:
        """Get all registered methods."""
        return list(self._methods.values())
    
    def list_method_names(self) -> List[str]:
        """Get all registered method names."""
        return list(self._methods.keys())
    
    def get_method_info(self) -> List[Dict[str, Any]]:
        """Get info for all methods (for discovery)."""
        return [method.to_info_dict() for method in self._methods.values()]
    
    def clear(self) -> None:
        """Clear all registered methods."""
        self._methods.clear()
        self._register_builtin_methods()
    
    def __len__(self) -> int:
        return len(self._methods)
    
    def __contains__(self, name: str) -> bool:
        return name in self._methods

"""
RPC Helper Functions

Utility functions for RPC calls.
"""

from typing import Any, Dict


def data(**kwargs: Any) -> Dict[str, Any]:
    """
    Build a data dictionary for RPC calls.
    
    This is a convenience function that makes RPC calls more readable.
    
    Usage:
        result = await rpc.call("calculate", args=data(
            operation="add",
            a=10,
            b=20
        ))
    
    Args:
        **kwargs: Key-value pairs to include in the data
        
    Returns:
        Dictionary containing all provided key-value pairs
    """
    return kwargs


def params(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Build a params dictionary for RPC calls with positional args support.
    
    Usage:
        # Keyword args only
        result = await rpc.call("func", args=params(x=1, y=2))
        
        # Positional args (will be named _0, _1, etc.)
        result = await rpc.call("func", args=params(10, 20, z=30))
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Dictionary containing all arguments
    """
    result = {}
    
    # Add positional args with numeric keys
    for i, arg in enumerate(args):
        result[f"_{i}"] = arg
    
    # Add keyword args
    result.update(kwargs)
    
    return result

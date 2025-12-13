"""
Server and Client Descriptor Re-exports

Provides the descriptor classes at the package level.
"""

from .data.descriptors import ServerDescriptor, ClientDescriptor

__all__ = ["ServerDescriptor", "ClientDescriptor"]

"""VizBind -- a reference engine for declarative, notation-independent
visualization of RDFS/OWL models.

The engine is deliberately small: the contribution of the accompanying paper is
the *binding vocabulary* (``vocab/vizbind.ttl``), and this package exists to
demonstrate that the vocabulary is executable and engine-independent.
"""

from .engine import Engine, apply_notation
from .model import AVM, Decorator, Edge, Node
from .notation import Notation, load_notation

__version__ = "0.1.0"

__all__ = [
    "AVM",
    "Decorator",
    "Edge",
    "Engine",
    "Node",
    "Notation",
    "apply_notation",
    "load_notation",
    "__version__",
]

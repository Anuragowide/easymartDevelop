"""
Generic index document model
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class IndexDocument:
    """Generic document for indexing"""
    id: str                    # Document identifier
    content: str              # Searchable text content
    metadata: Dict[str, Any]  # Additional fields

"""
Tork Governance adapter for txtai.

Provides governance for txtai's embeddings and pipeline framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.txtai_adapter import TorkTxtaiEmbeddings

    embeddings = TorkTxtaiEmbeddings(tork=tork)
    embeddings.index(["My SSN is 123-45-6789"])
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkTxtaiEmbeddings:
    """Governed txtai Embeddings wrapper."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        **config
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy initialize the txtai Embeddings."""
        if self._client is None:
            try:
                from txtai.embeddings import Embeddings
                self._client = Embeddings(**self.config)
            except ImportError:
                raise ImportError(
                    "txtai is required. Install with: pip install txtai"
                )
        return self._client

    def index(self, documents: List[str]) -> Dict[str, Any]:
        """Index documents with governance."""
        receipts = []
        governed_docs = []

        if self.govern_input and self.tork:
            for doc in documents:
                result = self.tork.govern(doc)
                receipts.append(result.receipt)
                governed_docs.append(
                    result.output if result.action in ('redact', 'REDACT') else doc
                )
        else:
            governed_docs = documents

        client = self._get_client()
        client.index(governed_docs)

        return {
            "indexed": len(governed_docs),
            "_tork_receipts": receipts,
        }

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search with governed query and results."""
        receipts = []

        governed_query = query
        if self.govern_input and self.tork:
            result = self.tork.govern(query)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_query = result.output

        client = self._get_client()
        results = client.search(governed_query, limit=limit)

        return {
            "results": results,
            "_tork_receipts": receipts,
        }


class TorkTxtaiPipeline:
    """Governed txtai Pipeline wrapper."""

    def __init__(
        self,
        pipeline_type: str = "summary",
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.pipeline_type = pipeline_type
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._pipeline = None

    def _get_pipeline(self):
        """Lazy initialize the txtai pipeline."""
        if self._pipeline is None:
            try:
                from txtai.pipeline import Summary, Translation
                pipelines = {"summary": Summary, "translation": Translation}
                cls = pipelines.get(self.pipeline_type)
                if cls:
                    self._pipeline = cls()
                else:
                    raise ValueError(f"Unknown pipeline type: {self.pipeline_type}")
            except ImportError:
                raise ImportError(
                    "txtai is required. Install with: pip install txtai"
                )
        return self._pipeline

    def run(self, text: str, **kwargs) -> Dict[str, Any]:
        """Run the pipeline with governance."""
        receipts = []

        governed_text = text
        if self.govern_input and self.tork:
            result = self.tork.govern(text)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_text = result.output

        pipeline = self._get_pipeline()
        output = pipeline(governed_text, **kwargs)

        content = str(output)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "output": content,
            "_tork_receipts": receipts,
        }


def txtai_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern txtai operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input:
                new_args = list(args)
                for i, arg in enumerate(new_args):
                    if isinstance(arg, str):
                        result = tork.govern(arg)
                        if result.action in ('redact', 'REDACT'):
                            new_args[i] = result.output
                    elif isinstance(arg, list):
                        new_args[i] = []
                        for item in arg:
                            if isinstance(item, str):
                                result = tork.govern(item)
                                new_args[i].append(
                                    result.output if result.action in ('redact', 'REDACT') else item
                                )
                            else:
                                new_args[i].append(item)
                args = tuple(new_args)
            return func(*args, **kwargs)
        return wrapper
    return decorator

"""
Haystack adapter for Tork Governance.

Provides components and pipeline wrappers for deepset Haystack.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkHaystackComponent:
    """
    Haystack component for Tork governance.

    Can be used in Haystack pipelines to govern documents and queries.

    Example:
        >>> from tork_governance.adapters.haystack import TorkHaystackComponent
        >>> from haystack import Pipeline
        >>>
        >>> pipeline = Pipeline()
        >>> tork_component = TorkHaystackComponent()
        >>> pipeline.add_component("tork", tork_component)
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def run(
        self,
        documents: Optional[List[Any]] = None,
        query: Optional[str] = None,
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run governance on documents and/or query.

        Args:
            documents: List of Haystack documents
            query: Query string
            text: Plain text to govern

        Returns:
            Dict with governed outputs and receipts
        """
        results: Dict[str, Any] = {}

        # Govern query
        if query:
            governed = self.tork.govern(query)
            results["query"] = governed.output
            results["governed_query"] = governed.output  # Alias for convenience
            results["query_receipt"] = {
                "receipt_id": governed.receipt.receipt_id,
                "action": governed.action.value,
                "has_pii": governed.pii.has_pii
            }
            self.receipts.append(results["query_receipt"])

        # Govern text
        if text:
            governed = self.tork.govern(text)
            results["text"] = governed.output
            results["text_receipt"] = {
                "receipt_id": governed.receipt.receipt_id,
                "action": governed.action.value
            }
            self.receipts.append(results["text_receipt"])

        # Govern documents
        if documents:
            governed_docs = []
            doc_receipts = []
            for doc in documents:
                content = getattr(doc, "content", str(doc))
                governed = self.tork.govern(content)

                # Create governed document
                if hasattr(doc, "content"):
                    doc.content = governed.output
                    governed_docs.append(doc)
                else:
                    governed_docs.append(governed.output)

                doc_receipt = {
                    "receipt_id": governed.receipt.receipt_id,
                    "has_pii": governed.pii.has_pii
                }
                doc_receipts.append(doc_receipt)
                self.receipts.append(doc_receipt)

            results["documents"] = governed_docs
            results["document_receipts"] = doc_receipts

        return results

    def get_receipts(self) -> List[Dict]:
        """Get all governance receipts."""
        return self.receipts


class TorkHaystackPipeline:
    """
    Wrapper for Haystack Pipeline with governance.

    Example:
        >>> from tork_governance.adapters.haystack import TorkHaystackPipeline
        >>>
        >>> pipeline = Pipeline()
        >>> # ... add components ...
        >>> governed_pipeline = TorkHaystackPipeline(pipeline)
        >>>
        >>> result = governed_pipeline.run({"query": "user data"})
    """

    def __init__(self, pipeline: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.pipeline = pipeline
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run pipeline with governance on inputs and outputs.

        Args:
            inputs: Pipeline inputs

        Returns:
            Governed pipeline outputs
        """
        # Govern inputs
        governed_inputs = self._govern_dict(inputs, "input")

        # Run pipeline
        outputs = self.pipeline.run(governed_inputs)

        # Govern outputs
        governed_outputs = self._govern_dict(outputs, "output")

        return governed_outputs

    def _govern_dict(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Govern string values in a dictionary."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": f"pipeline_{direction}",
                    "key": key,
                    "receipt_id": result.receipt.receipt_id
                })
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value, direction)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value, direction)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, items: List[Any], direction: str) -> List[Any]:
        """Govern string values in a list."""
        governed = []
        for item in items:
            if isinstance(item, str):
                result = self.tork.govern(item)
                governed.append(result.output)
            elif isinstance(item, dict):
                governed.append(self._govern_dict(item, direction))
            else:
                governed.append(item)
        return governed

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkDocumentProcessor:
    """
    Haystack document processor with governance.

    Use to process documents before indexing.
    """

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def process(self, documents: List[Any]) -> List[Any]:
        """Process and govern documents."""
        processed = []
        for doc in documents:
            content = getattr(doc, "content", str(doc))
            result = self.tork.govern(content)

            if hasattr(doc, "content"):
                doc.content = result.output
                # Add governance metadata
                if hasattr(doc, "meta"):
                    doc.meta["tork_receipt_id"] = result.receipt.receipt_id
                    doc.meta["tork_has_pii"] = result.pii.has_pii
                processed.append(doc)
            else:
                processed.append(result.output)

            self.receipts.append({
                "receipt_id": result.receipt.receipt_id,
                "has_pii": result.pii.has_pii
            })

        return processed

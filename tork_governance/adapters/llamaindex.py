"""
LlamaIndex adapter for Tork Governance.

Provides callbacks, query engine wrappers, and retriever wrappers.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkLlamaIndexCallback:
    """
    Callback handler for LlamaIndex with Tork governance.

    Example:
        >>> from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback
        >>> from llama_index.core import Settings
        >>>
        >>> callback = TorkLlamaIndexCallback()
        >>> # Use with LlamaIndex callback manager
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern_query(self, query: str) -> str:
        """Govern query - standalone method (alias for on_query_start)."""
        return self.on_query_start(query)

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def on_query_start(self, query: str) -> str:
        """Govern query before execution."""
        result = self.tork.govern(query)
        self.receipts.append({
            "type": "query_start",
            "receipt_id": result.receipt.receipt_id,
            "action": result.action.value,
            "has_pii": result.pii.has_pii
        })
        return result.output

    def on_query_end(self, response: str) -> str:
        """Govern query response."""
        result = self.tork.govern(response)
        self.receipts.append({
            "type": "query_end",
            "receipt_id": result.receipt.receipt_id,
            "action": result.action.value
        })
        return result.output

    def on_llm_start(self, prompt: str) -> str:
        """Govern LLM prompt."""
        result = self.tork.govern(prompt)
        self.receipts.append({
            "type": "llm_start",
            "receipt_id": result.receipt.receipt_id
        })
        return result.output

    def on_llm_end(self, response: str) -> str:
        """Govern LLM response."""
        result = self.tork.govern(response)
        self.receipts.append({
            "type": "llm_end",
            "receipt_id": result.receipt.receipt_id
        })
        return result.output

    def on_retrieve_start(self, query: str) -> str:
        """Govern retrieval query."""
        result = self.tork.govern(query)
        return result.output

    def on_retrieve_end(self, nodes: List[Any]) -> List[Any]:
        """Govern retrieved nodes."""
        governed_nodes = []
        for node in nodes:
            if hasattr(node, "text"):
                result = self.tork.govern(node.text)
                node.text = result.output
            governed_nodes.append(node)
        return governed_nodes

    def get_receipts(self) -> List[Dict]:
        """Get all governance receipts."""
        return self.receipts


class TorkQueryEngine:
    """
    Wrapper for LlamaIndex QueryEngine with governance.

    Example:
        >>> from tork_governance.adapters.llamaindex import TorkQueryEngine
        >>> from llama_index.core import VectorStoreIndex
        >>>
        >>> index = VectorStoreIndex.from_documents(documents)
        >>> engine = index.as_query_engine()
        >>> governed_engine = TorkQueryEngine(engine)
        >>>
        >>> response = governed_engine.query("Find user data")
    """

    def __init__(self, engine: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.engine = engine
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern_query(self, query: str) -> str:
        """Govern query - standalone method."""
        return self.tork.govern(query).output

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def query(self, query_str: str) -> Any:
        """Execute governed query."""
        # Govern input
        input_result = self.tork.govern(query_str)
        self.receipts.append({
            "type": "query_input",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Query blocked: {input_result.receipt.receipt_id}")

        # Execute query
        response = self.engine.query(input_result.output)

        # Govern response
        if hasattr(response, "response"):
            output_result = self.tork.govern(str(response.response))
            response.response = output_result.output
            self.receipts.append({
                "type": "query_output",
                "receipt_id": output_result.receipt.receipt_id
            })

        return response

    async def aquery(self, query_str: str) -> Any:
        """Async governed query."""
        input_result = self.tork.govern(query_str)

        if hasattr(self.engine, "aquery"):
            response = await self.engine.aquery(input_result.output)
        else:
            response = self.engine.query(input_result.output)

        if hasattr(response, "response"):
            output_result = self.tork.govern(str(response.response))
            response.response = output_result.output

        return response

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkRetriever:
    """
    Wrapper for LlamaIndex Retriever with governance.

    Example:
        >>> retriever = index.as_retriever()
        >>> governed_retriever = TorkRetriever(retriever)
        >>> nodes = governed_retriever.retrieve("query")
    """

    def __init__(self, retriever: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.retriever = retriever
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern_query(self, query: str) -> str:
        """Govern query - standalone method."""
        return self.tork.govern(query).output

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def retrieve(self, query_str: str) -> List[Any]:
        """Retrieve with governance."""
        # Govern query
        query_result = self.tork.govern(query_str)
        self.receipts.append({
            "type": "retrieve_query",
            "receipt_id": query_result.receipt.receipt_id
        })

        # Retrieve
        nodes = self.retriever.retrieve(query_result.output)

        # Govern node content
        for node in nodes:
            if hasattr(node, "text"):
                result = self.tork.govern(node.text)
                node.text = result.output
                self.receipts.append({
                    "type": "retrieved_node",
                    "receipt_id": result.receipt.receipt_id,
                    "has_pii": result.pii.has_pii
                })

        return nodes

    def get_receipts(self) -> List[Dict]:
        return self.receipts

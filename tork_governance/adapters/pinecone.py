"""
Pinecone adapter for Tork Governance.

Provides governance integration for Pinecone, a managed vector database.
Governs metadata and text before upserting and query results.

Example:
    from pinecone import Pinecone
    from tork_governance.adapters.pinecone import TorkPineconeIndex, govern_upsert

    # Use governed index
    pc = Pinecone(api_key="your-api-key")
    index = TorkPineconeIndex(pc.Index("my-index"))
    index.upsert(vectors=[{"id": "1", "values": [...], "metadata": {"text": "My SSN is 123-45-6789"}}])

    # Use convenience function
    govern_upsert(index, vectors=[...])
"""

from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkPineconeIndex:
    """
    Governed Pinecone Index wrapper.

    Wraps a Pinecone index with automatic governance applied to
    metadata on upsert and results on query.
    """

    def __init__(
        self,
        index: Any,
        api_key: Optional[str] = None,
        govern_on_upsert: bool = True,
        govern_on_query: bool = True,
        text_metadata_keys: Optional[List[str]] = None,
    ):
        self._index = index
        self.tork = Tork(api_key=api_key)
        self.govern_on_upsert = govern_on_upsert
        self.govern_on_query = govern_on_query
        # Keys in metadata that contain text to govern
        self.text_metadata_keys = text_metadata_keys or [
            "text", "content", "document", "chunk", "passage",
            "description", "summary", "title", "message"
        ]
        self._receipts: List[str] = []

    def _govern_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Govern string values in metadata."""
        governed = {}
        for key, value in metadata.items():
            if isinstance(value, str) and key in self.text_metadata_keys:
                result = self.tork.govern(value)
                governed[key] = result.output
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
            else:
                governed[key] = value
        return governed

    def upsert(
        self,
        vectors: Union[List[Dict[str, Any]], List[tuple]],
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upsert vectors with governance applied to metadata.

        Vectors can be:
        - List of dicts: [{"id": "1", "values": [...], "metadata": {...}}]
        - List of tuples: [("1", [...], {...})]
        """
        if not self.govern_on_upsert:
            return self._index.upsert(vectors=vectors, namespace=namespace, **kwargs)

        governed_vectors = []
        for vec in vectors:
            if isinstance(vec, dict):
                governed_vec = vec.copy()
                if "metadata" in vec and vec["metadata"]:
                    governed_vec["metadata"] = self._govern_metadata(vec["metadata"])
                governed_vectors.append(governed_vec)
            elif isinstance(vec, tuple):
                # Tuple format: (id, values, metadata) or (id, values)
                if len(vec) >= 3 and vec[2]:
                    governed_meta = self._govern_metadata(vec[2])
                    governed_vectors.append((vec[0], vec[1], governed_meta))
                else:
                    governed_vectors.append(vec)
            else:
                governed_vectors.append(vec)

        return self._index.upsert(vectors=governed_vectors, namespace=namespace, **kwargs)

    def query(
        self,
        vector: Optional[List[float]] = None,
        id: Optional[str] = None,
        queries: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        include_values: bool = False,
        include_metadata: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Query with governance applied to results.

        Metadata in results is governed before being returned.
        """
        results = self._index.query(
            vector=vector,
            id=id,
            queries=queries,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_values=include_values,
            include_metadata=include_metadata,
            **kwargs
        )

        if not self.govern_on_query:
            return results

        # Govern result metadata
        if "matches" in results:
            for match in results["matches"]:
                if "metadata" in match and match["metadata"]:
                    match["metadata"] = self._govern_metadata(match["metadata"])

        # Handle multiple query results
        if "results" in results:
            for result in results["results"]:
                if "matches" in result:
                    for match in result["matches"]:
                        if "metadata" in match and match["metadata"]:
                            match["metadata"] = self._govern_metadata(match["metadata"])

        return results

    def fetch(
        self,
        ids: List[str],
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch vectors with governance applied to metadata.
        """
        results = self._index.fetch(ids=ids, namespace=namespace, **kwargs)

        if not self.govern_on_query:
            return results

        # Govern metadata in fetched vectors
        if "vectors" in results:
            for vec_id, vec_data in results["vectors"].items():
                if "metadata" in vec_data and vec_data["metadata"]:
                    vec_data["metadata"] = self._govern_metadata(vec_data["metadata"])

        return results

    def update(
        self,
        id: str,
        values: Optional[List[float]] = None,
        set_metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a vector with governance applied to metadata.
        """
        if self.govern_on_upsert and set_metadata:
            set_metadata = self._govern_metadata(set_metadata)

        return self._index.update(
            id=id,
            values=values,
            set_metadata=set_metadata,
            namespace=namespace,
            **kwargs
        )

    def delete(
        self,
        ids: Optional[List[str]] = None,
        delete_all: bool = False,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Delete vectors (passthrough)."""
        return self._index.delete(
            ids=ids,
            delete_all=delete_all,
            namespace=namespace,
            filter=filter,
            **kwargs
        )

    def describe_index_stats(
        self,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get index statistics."""
        return self._index.describe_index_stats(filter=filter, **kwargs)

    def list(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        pagination_token: Optional[str] = None,
        namespace: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """List vector IDs."""
        return self._index.list(
            prefix=prefix,
            limit=limit,
            pagination_token=pagination_token,
            namespace=namespace,
            **kwargs
        )

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


class TorkPineconeClient:
    """
    Governed Pinecone client wrapper.

    Wraps the Pinecone client to return governed indexes.
    """

    def __init__(
        self,
        pinecone_api_key: str,
        tork_api_key: Optional[str] = None,
        govern_on_upsert: bool = True,
        govern_on_query: bool = True,
        text_metadata_keys: Optional[List[str]] = None,
        environment: Optional[str] = None,
    ):
        self.pinecone_api_key = pinecone_api_key
        self.tork_api_key = tork_api_key
        self.govern_on_upsert = govern_on_upsert
        self.govern_on_query = govern_on_query
        self.text_metadata_keys = text_metadata_keys
        self.environment = environment
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the Pinecone client."""
        if self._client is None:
            try:
                from pinecone import Pinecone
            except ImportError:
                raise ImportError("pinecone-client is required: pip install pinecone-client")

            self._client = Pinecone(api_key=self.pinecone_api_key)
        return self._client

    def Index(self, name: str, **kwargs) -> TorkPineconeIndex:
        """Get a governed index."""
        client = self._get_client()
        index = client.Index(name, **kwargs)
        return TorkPineconeIndex(
            index,
            api_key=self.tork_api_key,
            govern_on_upsert=self.govern_on_upsert,
            govern_on_query=self.govern_on_query,
            text_metadata_keys=self.text_metadata_keys,
        )

    def create_index(
        self,
        name: str,
        dimension: int,
        metric: str = "cosine",
        **kwargs
    ) -> Any:
        """Create an index."""
        return self._get_client().create_index(
            name=name,
            dimension=dimension,
            metric=metric,
            **kwargs
        )

    def delete_index(self, name: str) -> None:
        """Delete an index."""
        self._get_client().delete_index(name=name)

    def list_indexes(self) -> List[Any]:
        """List all indexes."""
        return self._get_client().list_indexes()

    def describe_index(self, name: str) -> Any:
        """Describe an index."""
        return self._get_client().describe_index(name=name)


def govern_upsert(
    index: Any,
    vectors: Union[List[Dict[str, Any]], List[tuple]],
    api_key: Optional[str] = None,
    text_metadata_keys: Optional[List[str]] = None,
    namespace: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Upsert vectors to Pinecone with governance.

    Convenience function for one-off governed upserts.

    Example:
        govern_upsert(
            index,
            vectors=[
                {"id": "1", "values": [...], "metadata": {"text": "My SSN is 123-45-6789"}}
            ]
        )
    """
    tork = Tork(api_key=api_key)
    text_keys = text_metadata_keys or [
        "text", "content", "document", "chunk", "passage",
        "description", "summary", "title", "message"
    ]

    def govern_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: tork.govern(v).output if isinstance(v, str) and k in text_keys else v
            for k, v in metadata.items()
        }

    governed_vectors = []
    for vec in vectors:
        if isinstance(vec, dict):
            governed_vec = vec.copy()
            if "metadata" in vec and vec["metadata"]:
                governed_vec["metadata"] = govern_metadata(vec["metadata"])
            governed_vectors.append(governed_vec)
        elif isinstance(vec, tuple) and len(vec) >= 3 and vec[2]:
            governed_vectors.append((vec[0], vec[1], govern_metadata(vec[2])))
        else:
            governed_vectors.append(vec)

    return index.upsert(vectors=governed_vectors, namespace=namespace, **kwargs)


def govern_query(
    index: Any,
    vector: List[float],
    api_key: Optional[str] = None,
    text_metadata_keys: Optional[List[str]] = None,
    top_k: int = 10,
    include_metadata: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Query Pinecone with governance applied to results.

    Convenience function for one-off governed queries.

    Example:
        results = govern_query(
            index,
            vector=[0.1, 0.2, ...],
            top_k=5
        )
    """
    tork = Tork(api_key=api_key)
    text_keys = text_metadata_keys or [
        "text", "content", "document", "chunk", "passage",
        "description", "summary", "title", "message"
    ]

    results = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=include_metadata,
        **kwargs
    )

    # Govern result metadata
    if "matches" in results:
        for match in results["matches"]:
            if "metadata" in match and match["metadata"]:
                match["metadata"] = {
                    k: tork.govern(v).output if isinstance(v, str) and k in text_keys else v
                    for k, v in match["metadata"].items()
                }

    return results


def pinecone_governed(
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """
    Decorator to add Tork governance to Pinecone-based functions.

    Example:
        @pinecone_governed()
        def my_search_function(query_vector: List[float]) -> List[Dict]:
            results = index.query(vector=query_vector, top_k=5)
            return results["matches"]
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Govern output
            if govern_output:
                if isinstance(result, str):
                    result = tork.govern(result).output
                elif isinstance(result, list):
                    governed = []
                    for item in result:
                        if isinstance(item, dict) and "metadata" in item:
                            governed_item = item.copy()
                            governed_item["metadata"] = {
                                k: tork.govern(v).output if isinstance(v, str) else v
                                for k, v in item["metadata"].items()
                            }
                            governed.append(governed_item)
                        else:
                            governed.append(item)
                    result = governed
                elif isinstance(result, dict) and "matches" in result:
                    for match in result["matches"]:
                        if "metadata" in match:
                            match["metadata"] = {
                                k: tork.govern(v).output if isinstance(v, str) else v
                                for k, v in match["metadata"].items()
                            }

            return result

        return wrapper
    return decorator

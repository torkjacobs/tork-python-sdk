"""
ChromaDB adapter for Tork Governance.

Provides governance integration for ChromaDB, an AI-native vector database.
Governs documents before adding and query results before returning.

Example:
    import chromadb
    from tork_governance.adapters.chromadb import TorkChromaClient, TorkChromaCollection

    # Use governed client
    client = TorkChromaClient()
    collection = client.get_or_create_collection("my_collection")
    collection.add(documents=["My SSN is 123-45-6789"], ids=["doc1"])

    # Query with governance
    results = collection.query(query_texts=["Find sensitive data"])
"""

from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkChromaCollection:
    """
    Governed ChromaDB Collection wrapper.

    Wraps a ChromaDB collection with automatic governance applied to
    documents on add/update and results on query.
    """

    def __init__(
        self,
        collection: Any,
        api_key: Optional[str] = None,
        govern_on_add: bool = True,
        govern_on_query: bool = True,
        govern_metadata: bool = True,
    ):
        self._collection = collection
        self.tork = Tork(api_key=api_key)
        self.govern_on_add = govern_on_add
        self.govern_on_query = govern_on_query
        self.govern_metadata = govern_metadata
        self._receipts: List[str] = []

    @property
    def name(self) -> str:
        """Get collection name."""
        return self._collection.name

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Get collection metadata."""
        return self._collection.metadata

    def add(
        self,
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Add documents with governance applied.

        Documents are governed (PII redacted) before being added
        to the collection.
        """
        # Govern documents
        if self.govern_on_add and documents:
            governed_docs = []
            for doc in documents:
                result = self.tork.govern(doc)
                governed_docs.append(result.output)
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
            documents = governed_docs

        # Govern metadata string values
        if self.govern_metadata and metadatas:
            governed_metas = []
            for meta in metadatas:
                governed_meta = {}
                for key, value in meta.items():
                    if isinstance(value, str):
                        result = self.tork.govern(value)
                        governed_meta[key] = result.output
                        if result.receipt:
                            self._receipts.append(result.receipt.receipt_id)
                    else:
                        governed_meta[key] = value
                governed_metas.append(governed_meta)
            metadatas = governed_metas

        self._collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
            **kwargs
        )

    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> None:
        """
        Update documents with governance applied.
        """
        # Govern documents
        if self.govern_on_add and documents:
            governed_docs = []
            for doc in documents:
                result = self.tork.govern(doc)
                governed_docs.append(result.output)
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
            documents = governed_docs

        # Govern metadata
        if self.govern_metadata and metadatas:
            governed_metas = []
            for meta in metadatas:
                governed_meta = {}
                for key, value in meta.items():
                    if isinstance(value, str):
                        result = self.tork.govern(value)
                        governed_meta[key] = result.output
                    else:
                        governed_meta[key] = value
                governed_metas.append(governed_meta)
            metadatas = governed_metas

        self._collection.update(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            **kwargs
        )

    def upsert(
        self,
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Upsert documents with governance applied.
        """
        # Govern documents
        if self.govern_on_add and documents:
            documents = [self.tork.govern(doc).output for doc in documents]

        # Govern metadata
        if self.govern_metadata and metadatas:
            governed_metas = []
            for meta in metadatas:
                governed_meta = {
                    k: self.tork.govern(v).output if isinstance(v, str) else v
                    for k, v in meta.items()
                }
                governed_metas.append(governed_meta)
            metadatas = governed_metas

        self._collection.upsert(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
            **kwargs
        )

    def query(
        self,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Query with governance applied to results.

        Query texts are governed before searching, and returned
        documents are governed before being returned.
        """
        # Govern query texts
        if self.govern_on_query and query_texts:
            query_texts = [self.tork.govern(qt).output for qt in query_texts]

        # Execute query
        results = self._collection.query(
            query_embeddings=query_embeddings,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
            **kwargs
        )

        # Govern result documents
        if self.govern_on_query and "documents" in results and results["documents"]:
            governed_docs = []
            for doc_list in results["documents"]:
                governed_list = []
                for doc in doc_list:
                    if doc:
                        result = self.tork.govern(doc)
                        governed_list.append(result.output)
                        if result.receipt:
                            self._receipts.append(result.receipt.receipt_id)
                    else:
                        governed_list.append(doc)
                governed_docs.append(governed_list)
            results["documents"] = governed_docs

        # Govern result metadatas
        if self.govern_metadata and "metadatas" in results and results["metadatas"]:
            governed_metas = []
            for meta_list in results["metadatas"]:
                governed_list = []
                for meta in meta_list:
                    if meta:
                        governed_meta = {
                            k: self.tork.govern(v).output if isinstance(v, str) else v
                            for k, v in meta.items()
                        }
                        governed_list.append(governed_meta)
                    else:
                        governed_list.append(meta)
                governed_metas.append(governed_list)
            results["metadatas"] = governed_metas

        return results

    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include: Optional[List[str]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get documents with governance applied.
        """
        results = self._collection.get(
            ids=ids,
            where=where,
            limit=limit,
            offset=offset,
            include=include,
            where_document=where_document,
            **kwargs
        )

        # Govern documents
        if self.govern_on_query and "documents" in results and results["documents"]:
            results["documents"] = [
                self.tork.govern(doc).output if doc else doc
                for doc in results["documents"]
            ]

        return results

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Delete documents (passthrough)."""
        self._collection.delete(
            ids=ids,
            where=where,
            where_document=where_document,
            **kwargs
        )

    def count(self) -> int:
        """Get document count."""
        return self._collection.count()

    def peek(self, limit: int = 10) -> Dict[str, Any]:
        """Peek at documents with governance."""
        results = self._collection.peek(limit=limit)

        if self.govern_on_query and "documents" in results:
            results["documents"] = [
                self.tork.govern(doc).output if doc else doc
                for doc in results["documents"]
            ]

        return results

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


class TorkChromaClient:
    """
    Governed ChromaDB Client wrapper.

    Wraps ChromaDB client to return governed collections.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        govern_on_add: bool = True,
        govern_on_query: bool = True,
        govern_metadata: bool = True,
        # ChromaDB client options
        path: Optional[str] = None,
        settings: Any = None,
        tenant: str = "default_tenant",
        database: str = "default_database",
    ):
        self.tork = Tork(api_key=api_key)
        self.govern_on_add = govern_on_add
        self.govern_on_query = govern_on_query
        self.govern_metadata = govern_metadata
        self._client: Any = None
        self._client_kwargs = {
            "path": path,
            "settings": settings,
            "tenant": tenant,
            "database": database,
        }

    def _get_client(self) -> Any:
        """Get or create the ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
            except ImportError:
                raise ImportError("chromadb is required: pip install chromadb")

            # Filter out None values
            kwargs = {k: v for k, v in self._client_kwargs.items() if v is not None}

            if "path" in kwargs:
                self._client = chromadb.PersistentClient(**kwargs)
            else:
                self._client = chromadb.Client(**kwargs)

        return self._client

    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Any = None,
        **kwargs
    ) -> TorkChromaCollection:
        """Create a governed collection."""
        client = self._get_client()
        collection = client.create_collection(
            name=name,
            metadata=metadata,
            embedding_function=embedding_function,
            **kwargs
        )
        return TorkChromaCollection(
            collection,
            api_key=self.tork.api_key,
            govern_on_add=self.govern_on_add,
            govern_on_query=self.govern_on_query,
            govern_metadata=self.govern_metadata,
        )

    def get_collection(
        self,
        name: str,
        embedding_function: Any = None,
        **kwargs
    ) -> TorkChromaCollection:
        """Get a governed collection."""
        client = self._get_client()
        collection = client.get_collection(
            name=name,
            embedding_function=embedding_function,
            **kwargs
        )
        return TorkChromaCollection(
            collection,
            api_key=self.tork.api_key,
            govern_on_add=self.govern_on_add,
            govern_on_query=self.govern_on_query,
            govern_metadata=self.govern_metadata,
        )

    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Any = None,
        **kwargs
    ) -> TorkChromaCollection:
        """Get or create a governed collection."""
        client = self._get_client()
        collection = client.get_or_create_collection(
            name=name,
            metadata=metadata,
            embedding_function=embedding_function,
            **kwargs
        )
        return TorkChromaCollection(
            collection,
            api_key=self.tork.api_key,
            govern_on_add=self.govern_on_add,
            govern_on_query=self.govern_on_query,
            govern_metadata=self.govern_metadata,
        )

    def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        self._get_client().delete_collection(name=name)

    def list_collections(self) -> List[Any]:
        """List all collections."""
        return self._get_client().list_collections()

    def heartbeat(self) -> int:
        """Check if client is alive."""
        return self._get_client().heartbeat()

    def reset(self) -> bool:
        """Reset the client."""
        return self._get_client().reset()


def govern_add(
    collection: Any,
    documents: List[str],
    ids: List[str],
    api_key: Optional[str] = None,
    metadatas: Optional[List[Dict[str, Any]]] = None,
    embeddings: Optional[List[List[float]]] = None,
    **kwargs
) -> None:
    """
    Add documents to a ChromaDB collection with governance.

    Convenience function for one-off governed adds.

    Example:
        govern_add(
            collection,
            documents=["My SSN is 123-45-6789"],
            ids=["doc1"]
        )
    """
    tork = Tork(api_key=api_key)

    # Govern documents
    governed_docs = [tork.govern(doc).output for doc in documents]

    # Govern metadata
    governed_metas = None
    if metadatas:
        governed_metas = [
            {k: tork.govern(v).output if isinstance(v, str) else v for k, v in meta.items()}
            for meta in metadatas
        ]

    collection.add(
        documents=governed_docs,
        ids=ids,
        metadatas=governed_metas,
        embeddings=embeddings,
        **kwargs
    )


def govern_query(
    collection: Any,
    query_texts: List[str],
    api_key: Optional[str] = None,
    n_results: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    Query a ChromaDB collection with governance.

    Convenience function for one-off governed queries.

    Example:
        results = govern_query(
            collection,
            query_texts=["Find user data"]
        )
    """
    tork = Tork(api_key=api_key)

    # Govern query texts
    governed_queries = [tork.govern(qt).output for qt in query_texts]

    # Execute query
    results = collection.query(
        query_texts=governed_queries,
        n_results=n_results,
        **kwargs
    )

    # Govern result documents
    if "documents" in results and results["documents"]:
        governed_docs = []
        for doc_list in results["documents"]:
            governed_list = [
                tork.govern(doc).output if doc else doc
                for doc in doc_list
            ]
            governed_docs.append(governed_list)
        results["documents"] = governed_docs

    return results


def chromadb_governed(
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """
    Decorator to add Tork governance to ChromaDB-based functions.

    Example:
        @chromadb_governed()
        def my_search_function(query: str) -> List[str]:
            collection = client.get_collection("my_collection")
            results = collection.query(query_texts=[query])
            return results["documents"][0]
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string arguments
            if govern_input:
                args = tuple(
                    tork.govern(arg).output if isinstance(arg, str) else arg
                    for arg in args
                )
                kwargs = {
                    k: tork.govern(v).output if isinstance(v, str) else v
                    for k, v in kwargs.items()
                }

            result = func(*args, **kwargs)

            # Govern output
            if govern_output:
                if isinstance(result, str):
                    result = tork.govern(result).output
                elif isinstance(result, list):
                    result = [
                        tork.govern(r).output if isinstance(r, str) else r
                        for r in result
                    ]

            return result

        return wrapper
    return decorator

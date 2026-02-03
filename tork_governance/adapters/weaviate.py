"""
Tork Governance adapter for Weaviate vector database.

Provides governance for vector database operations including document
storage, retrieval, and search with automatic PII detection and redaction.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class WeaviateGovernanceResult:
    """Result of a governed Weaviate operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    blocked: bool = False
    original_count: int = 0
    governed_count: int = 0


class TorkWeaviateCollection:
    """Governed Weaviate collection wrapper."""

    def __init__(
        self,
        collection: Any,
        tork: Tork,
        govern_content: bool = True,
        govern_metadata: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """
        Initialize governed Weaviate collection.

        Args:
            collection: Weaviate collection object
            tork: Tork governance instance
            govern_content: Whether to govern document content
            govern_metadata: Whether to govern metadata fields
            text_fields: Specific fields to govern (None = all string fields)
        """
        self._collection = collection
        self._tork = tork
        self._govern_content = govern_content
        self._govern_metadata = govern_metadata
        self._text_fields = text_fields
        self._receipts: List[str] = []

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def collection(self) -> Any:
        """Get the underlying collection."""
        return self._collection

    def _govern_properties(self, properties: Dict[str, Any]) -> tuple:
        """Govern properties dict and return governed version with metadata."""
        governed = {}
        pii_detected = False
        pii_types = []
        receipts = []

        for key, value in properties.items():
            if isinstance(value, str):
                if self._text_fields is None or key in self._text_fields:
                    result = self._tork.govern(value)
                    governed[key] = result.output
                    if result.pii.has_pii:
                        pii_detected = True
                        pii_types.extend(result.pii.types)
                    receipts.append(result.receipt.receipt_id)
                    self._receipts.append(result.receipt.receipt_id)
                else:
                    governed[key] = value
            else:
                governed[key] = value

        return governed, pii_detected, list(set(pii_types)), receipts

    def _govern_metadata_dict(self, metadata: Optional[Dict[str, Any]]) -> tuple:
        """Govern metadata dictionary."""
        if not metadata or not self._govern_metadata:
            return metadata, False, [], []

        governed = {}
        pii_detected = False
        pii_types = []
        receipts = []

        for key, value in metadata.items():
            if isinstance(value, str):
                result = self._tork.govern(value)
                governed[key] = result.output
                if result.pii.has_pii:
                    pii_detected = True
                    pii_types.extend(result.pii.types)
                receipts.append(result.receipt.receipt_id)
                self._receipts.append(result.receipt.receipt_id)
            else:
                governed[key] = value

        return governed, pii_detected, list(set(pii_types)), receipts

    def insert(self, properties: Dict[str, Any], **kwargs) -> WeaviateGovernanceResult:
        """
        Insert a document with governance.

        Args:
            properties: Document properties
            **kwargs: Additional arguments for Weaviate insert

        Returns:
            WeaviateGovernanceResult with operation details
        """
        governed_props, pii_detected, pii_types, receipts = self._govern_properties(properties)

        try:
            result = self._collection.data.insert(governed_props, **kwargs)
            return WeaviateGovernanceResult(
                success=True,
                operation="insert",
                governed_data=result,
                receipts=receipts,
                pii_detected=pii_detected,
                pii_types=pii_types,
                original_count=1,
                governed_count=1,
            )
        except Exception as e:
            return WeaviateGovernanceResult(
                success=False,
                operation="insert",
                governed_data=str(e),
                receipts=receipts,
                pii_detected=pii_detected,
                pii_types=pii_types,
            )

    def insert_many(self, objects: List[Dict[str, Any]], **kwargs) -> WeaviateGovernanceResult:
        """
        Insert multiple documents with governance.

        Args:
            objects: List of document properties
            **kwargs: Additional arguments for Weaviate insert_many

        Returns:
            WeaviateGovernanceResult with operation details
        """
        governed_objects = []
        all_pii_types = []
        all_receipts = []
        any_pii_detected = False

        for obj in objects:
            properties = obj.get("properties", obj)
            governed_props, pii_detected, pii_types, receipts = self._govern_properties(properties)

            if pii_detected:
                any_pii_detected = True
                all_pii_types.extend(pii_types)
            all_receipts.extend(receipts)

            if "properties" in obj:
                governed_objects.append({**obj, "properties": governed_props})
            else:
                governed_objects.append(governed_props)

        try:
            result = self._collection.data.insert_many(governed_objects, **kwargs)
            return WeaviateGovernanceResult(
                success=True,
                operation="insert_many",
                governed_data=result,
                receipts=all_receipts,
                pii_detected=any_pii_detected,
                pii_types=list(set(all_pii_types)),
                original_count=len(objects),
                governed_count=len(governed_objects),
            )
        except Exception as e:
            return WeaviateGovernanceResult(
                success=False,
                operation="insert_many",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii_detected,
                pii_types=list(set(all_pii_types)),
                original_count=len(objects),
            )

    def query(self, query_text: str, **kwargs) -> WeaviateGovernanceResult:
        """
        Query the collection with governed query text.

        Args:
            query_text: Query string to search
            **kwargs: Additional query arguments

        Returns:
            WeaviateGovernanceResult with governed results
        """
        # Govern the query text
        query_result = self._tork.govern(query_text)
        governed_query = query_result.output
        self._receipts.append(query_result.receipt.receipt_id)

        try:
            results = self._collection.query.near_text(
                query=governed_query,
                **kwargs
            )

            return WeaviateGovernanceResult(
                success=True,
                operation="query",
                governed_data=results,
                receipts=[query_result.receipt.receipt_id],
                pii_detected=query_result.pii.has_pii,
                pii_types=query_result.pii.types,
                original_count=1,
                governed_count=1,
            )
        except Exception as e:
            return WeaviateGovernanceResult(
                success=False,
                operation="query",
                governed_data=str(e),
                receipts=[query_result.receipt.receipt_id],
                pii_detected=query_result.pii.has_pii,
                pii_types=query_result.pii.types,
            )

    def delete(self, uuid: str, **kwargs) -> WeaviateGovernanceResult:
        """Delete a document by UUID."""
        try:
            result = self._collection.data.delete_by_id(uuid, **kwargs)
            return WeaviateGovernanceResult(
                success=True,
                operation="delete",
                governed_data=result,
                original_count=1,
                governed_count=1,
            )
        except Exception as e:
            return WeaviateGovernanceResult(
                success=False,
                operation="delete",
                governed_data=str(e),
            )


class TorkWeaviateClient:
    """Governed Weaviate client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_content: bool = True,
        govern_metadata: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """
        Initialize governed Weaviate client.

        Args:
            client: Weaviate client instance (optional, can connect later)
            tork: Tork governance instance (created if not provided)
            config: Tork configuration
            govern_content: Whether to govern document content
            govern_metadata: Whether to govern metadata fields
            text_fields: Specific fields to govern (None = all string fields)
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_content = govern_content
        self._govern_metadata = govern_metadata
        self._text_fields = text_fields
        self._receipts: List[str] = []
        self._collections: Dict[str, TorkWeaviateCollection] = {}

    @property
    def client(self) -> Any:
        """Get the underlying Weaviate client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the Weaviate client."""
        self._client = value

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        all_receipts = self._receipts.copy()
        for collection in self._collections.values():
            all_receipts.extend(collection.receipts)
        return all_receipts

    def collection(self, name: str) -> TorkWeaviateCollection:
        """
        Get a governed collection by name.

        Args:
            name: Collection name

        Returns:
            TorkWeaviateCollection wrapper
        """
        if name not in self._collections:
            weaviate_collection = self._client.collections.get(name)
            self._collections[name] = TorkWeaviateCollection(
                collection=weaviate_collection,
                tork=self._tork,
                govern_content=self._govern_content,
                govern_metadata=self._govern_metadata,
                text_fields=self._text_fields,
            )
        return self._collections[name]

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


def govern_add(
    collection: Any,
    documents: Union[Dict[str, Any], List[Dict[str, Any]]],
    tork: Optional[Tork] = None,
    text_fields: Optional[List[str]] = None,
    **kwargs
) -> WeaviateGovernanceResult:
    """
    Govern documents and add to Weaviate collection.

    Args:
        collection: Weaviate collection
        documents: Document(s) to add
        tork: Tork instance (created if not provided)
        text_fields: Fields to govern
        **kwargs: Additional arguments

    Returns:
        WeaviateGovernanceResult
    """
    tork_instance = tork or Tork()
    governed_collection = TorkWeaviateCollection(
        collection=collection,
        tork=tork_instance,
        text_fields=text_fields,
    )

    if isinstance(documents, list):
        return governed_collection.insert_many(documents, **kwargs)
    else:
        return governed_collection.insert(documents, **kwargs)


def govern_query(
    collection: Any,
    query: str,
    tork: Optional[Tork] = None,
    **kwargs
) -> WeaviateGovernanceResult:
    """
    Govern query and search Weaviate collection.

    Args:
        collection: Weaviate collection
        query: Search query
        tork: Tork instance (created if not provided)
        **kwargs: Additional query arguments

    Returns:
        WeaviateGovernanceResult
    """
    tork_instance = tork or Tork()
    governed_collection = TorkWeaviateCollection(
        collection=collection,
        tork=tork_instance,
    )
    return governed_collection.query(query, **kwargs)


def govern_batch(
    client: Any,
    collection_name: str,
    documents: List[Dict[str, Any]],
    tork: Optional[Tork] = None,
    batch_size: int = 100,
    text_fields: Optional[List[str]] = None,
) -> WeaviateGovernanceResult:
    """
    Govern and batch insert documents to Weaviate.

    Args:
        client: Weaviate client
        collection_name: Target collection name
        documents: Documents to insert
        tork: Tork instance
        batch_size: Batch size for insertion
        text_fields: Fields to govern

    Returns:
        WeaviateGovernanceResult
    """
    tork_instance = tork or Tork()
    governed_client = TorkWeaviateClient(
        client=client,
        tork=tork_instance,
        text_fields=text_fields,
    )

    collection = governed_client.collection(collection_name)
    all_receipts = []
    all_pii_types = []
    any_pii_detected = False
    total_governed = 0

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = collection.insert_many(batch)

        all_receipts.extend(result.receipts)
        if result.pii_detected:
            any_pii_detected = True
            all_pii_types.extend(result.pii_types)
        total_governed += result.governed_count

    return WeaviateGovernanceResult(
        success=True,
        operation="batch_insert",
        governed_data={"total_inserted": total_governed},
        receipts=all_receipts,
        pii_detected=any_pii_detected,
        pii_types=list(set(all_pii_types)),
        original_count=len(documents),
        governed_count=total_governed,
    )


class AsyncTorkWeaviateClient:
    """Async governed Weaviate client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_content: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """Initialize async governed Weaviate client."""
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_content = govern_content
        self._text_fields = text_fields
        self._receipts: List[str] = []

    @property
    def client(self) -> Any:
        """Get the underlying async client."""
        return self._client

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    async def govern_add(
        self,
        collection_name: str,
        documents: Union[Dict[str, Any], List[Dict[str, Any]]],
        **kwargs
    ) -> WeaviateGovernanceResult:
        """Async govern and add documents."""
        # Governance is sync, only the Weaviate operations are async
        tork_collection = TorkWeaviateCollection(
            collection=self._client.collections.get(collection_name),
            tork=self._tork,
            text_fields=self._text_fields,
        )

        if isinstance(documents, list):
            return tork_collection.insert_many(documents, **kwargs)
        else:
            return tork_collection.insert(documents, **kwargs)

    async def govern_query(
        self,
        collection_name: str,
        query: str,
        **kwargs
    ) -> WeaviateGovernanceResult:
        """Async govern and query collection."""
        tork_collection = TorkWeaviateCollection(
            collection=self._client.collections.get(collection_name),
            tork=self._tork,
        )
        return tork_collection.query(query, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

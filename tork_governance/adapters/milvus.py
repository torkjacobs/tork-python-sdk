"""
Tork Governance adapter for Milvus vector database.

Provides governance for Milvus operations including data insertion,
vector search, and scalar queries with automatic PII detection.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class MilvusGovernanceResult:
    """Result of a governed Milvus operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    blocked: bool = False
    original_count: int = 0
    governed_count: int = 0


class TorkMilvusCollection:
    """Governed Milvus collection wrapper."""

    def __init__(
        self,
        collection: Any,
        tork: Tork,
        govern_fields: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """
        Initialize governed Milvus collection.

        Args:
            collection: Milvus collection object
            tork: Tork governance instance
            govern_fields: Whether to govern field data
            text_fields: Specific fields to govern (None = all string fields)
        """
        self._collection = collection
        self._tork = tork
        self._govern_fields = govern_fields
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

    def _govern_data(self, data: Union[Dict[str, List], List[Dict]]) -> tuple:
        """Govern insert data and return governed version with metadata."""
        governed_data = None
        pii_detected = False
        pii_types = []
        receipts = []

        if isinstance(data, dict):
            # Column-oriented format: {"field1": [val1, val2], "field2": [val1, val2]}
            governed_data = {}
            for field_name, values in data.items():
                if self._text_fields is None or field_name in self._text_fields:
                    governed_values = []
                    for value in values:
                        if isinstance(value, str):
                            result = self._tork.govern(value)
                            governed_values.append(result.output)
                            if result.pii.has_pii:
                                pii_detected = True
                                pii_types.extend(result.pii.types)
                            receipts.append(result.receipt.receipt_id)
                            self._receipts.append(result.receipt.receipt_id)
                        else:
                            governed_values.append(value)
                    governed_data[field_name] = governed_values
                else:
                    governed_data[field_name] = values

        elif isinstance(data, list):
            # Row-oriented format: [{"field1": val1, "field2": val2}, ...]
            governed_data = []
            for row in data:
                governed_row = {}
                for field_name, value in row.items():
                    if isinstance(value, str):
                        if self._text_fields is None or field_name in self._text_fields:
                            result = self._tork.govern(value)
                            governed_row[field_name] = result.output
                            if result.pii.has_pii:
                                pii_detected = True
                                pii_types.extend(result.pii.types)
                            receipts.append(result.receipt.receipt_id)
                            self._receipts.append(result.receipt.receipt_id)
                        else:
                            governed_row[field_name] = value
                    else:
                        governed_row[field_name] = value
                governed_data.append(governed_row)

        return governed_data, pii_detected, list(set(pii_types)), receipts

    def insert(
        self,
        data: Union[Dict[str, List], List[Dict]],
        **kwargs
    ) -> MilvusGovernanceResult:
        """
        Insert data with governance.

        Args:
            data: Data to insert (column or row format)
            **kwargs: Additional insert arguments

        Returns:
            MilvusGovernanceResult
        """
        if not self._govern_fields:
            try:
                result = self._collection.insert(data, **kwargs)
                return MilvusGovernanceResult(
                    success=True,
                    operation="insert",
                    governed_data=result,
                )
            except Exception as e:
                return MilvusGovernanceResult(
                    success=False,
                    operation="insert",
                    governed_data=str(e),
                )

        governed_data, pii_detected, pii_types, receipts = self._govern_data(data)

        # Count records
        if isinstance(data, dict):
            original_count = len(next(iter(data.values()))) if data else 0
        else:
            original_count = len(data)

        try:
            result = self._collection.insert(governed_data, **kwargs)
            return MilvusGovernanceResult(
                success=True,
                operation="insert",
                governed_data=result,
                receipts=receipts,
                pii_detected=pii_detected,
                pii_types=pii_types,
                original_count=original_count,
                governed_count=original_count,
            )
        except Exception as e:
            return MilvusGovernanceResult(
                success=False,
                operation="insert",
                governed_data=str(e),
                receipts=receipts,
                pii_detected=pii_detected,
                pii_types=pii_types,
                original_count=original_count,
            )

    def search(
        self,
        data: List[List[float]],
        anns_field: str,
        param: Dict[str, Any],
        limit: int,
        expr: Optional[str] = None,
        output_fields: Optional[List[str]] = None,
        **kwargs
    ) -> MilvusGovernanceResult:
        """
        Vector search with governance.

        Args:
            data: Query vectors
            anns_field: Field to search
            param: Search parameters
            limit: Result limit
            expr: Filter expression
            output_fields: Fields to return
            **kwargs: Additional search arguments

        Returns:
            MilvusGovernanceResult
        """
        # Govern filter expression if it contains string literals
        governed_expr = expr
        expr_receipts = []
        expr_pii_detected = False
        expr_pii_types = []

        if expr and isinstance(expr, str):
            # Check for string values in expression
            result = self._tork.govern(expr)
            governed_expr = result.output
            expr_receipts.append(result.receipt.receipt_id)
            self._receipts.append(result.receipt.receipt_id)
            expr_pii_detected = result.pii.has_pii
            expr_pii_types = result.pii.types

        try:
            results = self._collection.search(
                data=data,
                anns_field=anns_field,
                param=param,
                limit=limit,
                expr=governed_expr,
                output_fields=output_fields,
                **kwargs
            )
            return MilvusGovernanceResult(
                success=True,
                operation="search",
                governed_data=results,
                receipts=expr_receipts,
                pii_detected=expr_pii_detected,
                pii_types=expr_pii_types,
            )
        except Exception as e:
            return MilvusGovernanceResult(
                success=False,
                operation="search",
                governed_data=str(e),
                receipts=expr_receipts,
                pii_detected=expr_pii_detected,
                pii_types=expr_pii_types,
            )

    def query(
        self,
        expr: str,
        output_fields: Optional[List[str]] = None,
        **kwargs
    ) -> MilvusGovernanceResult:
        """
        Scalar query with governance.

        Args:
            expr: Query expression
            output_fields: Fields to return
            **kwargs: Additional query arguments

        Returns:
            MilvusGovernanceResult
        """
        # Govern the expression
        result = self._tork.govern(expr)
        governed_expr = result.output
        self._receipts.append(result.receipt.receipt_id)

        try:
            results = self._collection.query(
                expr=governed_expr,
                output_fields=output_fields,
                **kwargs
            )
            return MilvusGovernanceResult(
                success=True,
                operation="query",
                governed_data=results,
                receipts=[result.receipt.receipt_id],
                pii_detected=result.pii.has_pii,
                pii_types=result.pii.types,
            )
        except Exception as e:
            return MilvusGovernanceResult(
                success=False,
                operation="query",
                governed_data=str(e),
                receipts=[result.receipt.receipt_id],
                pii_detected=result.pii.has_pii,
                pii_types=result.pii.types,
            )

    def delete(self, expr: str, **kwargs) -> MilvusGovernanceResult:
        """Delete entities matching expression."""
        try:
            result = self._collection.delete(expr, **kwargs)
            return MilvusGovernanceResult(
                success=True,
                operation="delete",
                governed_data=result,
            )
        except Exception as e:
            return MilvusGovernanceResult(
                success=False,
                operation="delete",
                governed_data=str(e),
            )


class TorkMilvusClient:
    """Governed Milvus client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_fields: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """
        Initialize governed Milvus client.

        Args:
            client: Milvus connection or client
            tork: Tork governance instance
            config: Tork configuration
            govern_fields: Whether to govern field data
            text_fields: Specific fields to govern
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_fields = govern_fields
        self._text_fields = text_fields
        self._receipts: List[str] = []
        self._collections: Dict[str, TorkMilvusCollection] = {}

    @property
    def client(self) -> Any:
        """Get the underlying Milvus client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the Milvus client."""
        self._client = value

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        all_receipts = self._receipts.copy()
        for collection in self._collections.values():
            all_receipts.extend(collection.receipts)
        return all_receipts

    def collection(self, name: str, **kwargs) -> TorkMilvusCollection:
        """
        Get a governed collection by name.

        Args:
            name: Collection name
            **kwargs: Additional arguments for collection

        Returns:
            TorkMilvusCollection wrapper
        """
        if name not in self._collections:
            # Import pymilvus Collection if available
            try:
                from pymilvus import Collection
                milvus_collection = Collection(name, **kwargs)
            except ImportError:
                # Fallback: assume client has collection method
                milvus_collection = self._client.get_collection(name)

            self._collections[name] = TorkMilvusCollection(
                collection=milvus_collection,
                tork=self._tork,
                govern_fields=self._govern_fields,
                text_fields=self._text_fields,
            )
        return self._collections[name]

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


def govern_insert(
    collection: Any,
    data: Union[Dict[str, List], List[Dict]],
    tork: Optional[Tork] = None,
    text_fields: Optional[List[str]] = None,
    **kwargs
) -> MilvusGovernanceResult:
    """
    Govern data and insert to Milvus collection.

    Args:
        collection: Milvus collection
        data: Data to insert
        tork: Tork instance
        text_fields: Fields to govern
        **kwargs: Additional arguments

    Returns:
        MilvusGovernanceResult
    """
    tork_instance = tork or Tork()
    governed_collection = TorkMilvusCollection(
        collection=collection,
        tork=tork_instance,
        text_fields=text_fields,
    )
    return governed_collection.insert(data, **kwargs)


def govern_search(
    collection: Any,
    vectors: List[List[float]],
    anns_field: str,
    param: Dict[str, Any],
    limit: int,
    tork: Optional[Tork] = None,
    expr: Optional[str] = None,
    **kwargs
) -> MilvusGovernanceResult:
    """
    Govern search expression and execute vector search.

    Args:
        collection: Milvus collection
        vectors: Query vectors
        anns_field: Field to search
        param: Search parameters
        limit: Result limit
        tork: Tork instance
        expr: Filter expression
        **kwargs: Additional arguments

    Returns:
        MilvusGovernanceResult
    """
    tork_instance = tork or Tork()
    governed_collection = TorkMilvusCollection(
        collection=collection,
        tork=tork_instance,
    )
    return governed_collection.search(
        data=vectors,
        anns_field=anns_field,
        param=param,
        limit=limit,
        expr=expr,
        **kwargs
    )


def govern_query(
    collection: Any,
    expr: str,
    tork: Optional[Tork] = None,
    output_fields: Optional[List[str]] = None,
    **kwargs
) -> MilvusGovernanceResult:
    """
    Govern query expression and execute scalar query.

    Args:
        collection: Milvus collection
        expr: Query expression
        tork: Tork instance
        output_fields: Fields to return
        **kwargs: Additional arguments

    Returns:
        MilvusGovernanceResult
    """
    tork_instance = tork or Tork()
    governed_collection = TorkMilvusCollection(
        collection=collection,
        tork=tork_instance,
    )
    return governed_collection.query(expr, output_fields, **kwargs)


class AsyncTorkMilvusClient:
    """Async governed Milvus client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_fields: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """Initialize async governed Milvus client."""
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_fields = govern_fields
        self._text_fields = text_fields
        self._receipts: List[str] = []

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    async def insert(
        self,
        collection_name: str,
        data: Union[Dict[str, List], List[Dict]],
        **kwargs
    ) -> MilvusGovernanceResult:
        """Async insert with governance."""
        # Governance is sync, Milvus operation would be async
        try:
            from pymilvus import Collection
            collection = Collection(collection_name)
        except ImportError:
            collection = self._client.get_collection(collection_name)

        governed_collection = TorkMilvusCollection(
            collection=collection,
            tork=self._tork,
            govern_fields=self._govern_fields,
            text_fields=self._text_fields,
        )
        return governed_collection.insert(data, **kwargs)

    async def search(
        self,
        collection_name: str,
        vectors: List[List[float]],
        anns_field: str,
        param: Dict[str, Any],
        limit: int,
        expr: Optional[str] = None,
        **kwargs
    ) -> MilvusGovernanceResult:
        """Async search with governance."""
        try:
            from pymilvus import Collection
            collection = Collection(collection_name)
        except ImportError:
            collection = self._client.get_collection(collection_name)

        governed_collection = TorkMilvusCollection(
            collection=collection,
            tork=self._tork,
        )
        return governed_collection.search(
            data=vectors,
            anns_field=anns_field,
            param=param,
            limit=limit,
            expr=expr,
            **kwargs
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

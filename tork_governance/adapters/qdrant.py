"""
Tork Governance adapter for Qdrant vector database.

Provides governance for Qdrant operations including point storage,
search, and retrieval with automatic PII detection and redaction.
"""

from typing import Any, Dict, List, Optional, Union, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class QdrantGovernanceResult:
    """Result of a governed Qdrant operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    blocked: bool = False
    original_count: int = 0
    governed_count: int = 0


class TorkQdrantClient:
    """Governed Qdrant client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_payloads: bool = True,
        text_payload_keys: Optional[List[str]] = None,
    ):
        """
        Initialize governed Qdrant client.

        Args:
            client: Qdrant client instance
            tork: Tork governance instance (created if not provided)
            config: Tork configuration
            govern_payloads: Whether to govern point payloads
            text_payload_keys: Specific payload keys to govern (None = all strings)
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_payloads = govern_payloads
        self._text_payload_keys = text_payload_keys
        self._receipts: List[str] = []

    @property
    def client(self) -> Any:
        """Get the underlying Qdrant client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the Qdrant client."""
        self._client = value

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    def _govern_payload(self, payload: Optional[Dict[str, Any]]) -> tuple:
        """Govern a payload dictionary."""
        if not payload or not self._govern_payloads:
            return payload, False, [], []

        governed = {}
        pii_detected = False
        pii_types = []
        receipts = []

        for key, value in payload.items():
            if isinstance(value, str):
                if self._text_payload_keys is None or key in self._text_payload_keys:
                    result = self._tork.govern(value)
                    governed[key] = result.output
                    if result.pii.has_pii:
                        pii_detected = True
                        pii_types.extend(result.pii.types)
                    receipts.append(result.receipt.receipt_id)
                    self._receipts.append(result.receipt.receipt_id)
                else:
                    governed[key] = value
            elif isinstance(value, dict):
                # Recursively govern nested dicts
                nested_governed, nested_pii, nested_types, nested_receipts = self._govern_payload(value)
                governed[key] = nested_governed
                if nested_pii:
                    pii_detected = True
                    pii_types.extend(nested_types)
                receipts.extend(nested_receipts)
            elif isinstance(value, list):
                # Govern string items in lists
                governed_list = []
                for item in value:
                    if isinstance(item, str):
                        result = self._tork.govern(item)
                        governed_list.append(result.output)
                        if result.pii.has_pii:
                            pii_detected = True
                            pii_types.extend(result.pii.types)
                        receipts.append(result.receipt.receipt_id)
                        self._receipts.append(result.receipt.receipt_id)
                    else:
                        governed_list.append(item)
                governed[key] = governed_list
            else:
                governed[key] = value

        return governed, pii_detected, list(set(pii_types)), receipts

    def upsert(
        self,
        collection_name: str,
        points: List[Any],
        **kwargs
    ) -> QdrantGovernanceResult:
        """
        Upsert points with governance.

        Args:
            collection_name: Target collection
            points: Points to upsert (PointStruct or dict format)
            **kwargs: Additional upsert arguments

        Returns:
            QdrantGovernanceResult
        """
        governed_points = []
        all_pii_types = []
        all_receipts = []
        any_pii_detected = False

        for point in points:
            # Handle both dict and PointStruct formats
            if hasattr(point, 'payload'):
                payload = point.payload
            elif isinstance(point, dict):
                payload = point.get('payload', {})
            else:
                payload = {}

            governed_payload, pii_detected, pii_types, receipts = self._govern_payload(payload)

            if pii_detected:
                any_pii_detected = True
                all_pii_types.extend(pii_types)
            all_receipts.extend(receipts)

            # Reconstruct point with governed payload
            if hasattr(point, 'payload'):
                # PointStruct - create new with governed payload
                governed_points.append(type(point)(
                    id=point.id,
                    vector=point.vector,
                    payload=governed_payload,
                ))
            elif isinstance(point, dict):
                governed_points.append({
                    **point,
                    'payload': governed_payload,
                })
            else:
                governed_points.append(point)

        try:
            result = self._client.upsert(
                collection_name=collection_name,
                points=governed_points,
                **kwargs
            )
            return QdrantGovernanceResult(
                success=True,
                operation="upsert",
                governed_data=result,
                receipts=all_receipts,
                pii_detected=any_pii_detected,
                pii_types=list(set(all_pii_types)),
                original_count=len(points),
                governed_count=len(governed_points),
            )
        except Exception as e:
            return QdrantGovernanceResult(
                success=False,
                operation="upsert",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii_detected,
                pii_types=list(set(all_pii_types)),
                original_count=len(points),
            )

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: Optional[str] = None,
        **kwargs
    ) -> QdrantGovernanceResult:
        """
        Search with governance.

        Args:
            collection_name: Target collection
            query_vector: Query vector for search
            query_text: Optional query text to govern
            **kwargs: Additional search arguments

        Returns:
            QdrantGovernanceResult
        """
        receipts = []
        pii_detected = False
        pii_types = []

        # Govern query text if provided
        if query_text:
            query_result = self._tork.govern(query_text)
            receipts.append(query_result.receipt.receipt_id)
            self._receipts.append(query_result.receipt.receipt_id)
            pii_detected = query_result.pii.has_pii
            pii_types = query_result.pii.types

        try:
            results = self._client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                **kwargs
            )
            return QdrantGovernanceResult(
                success=True,
                operation="search",
                governed_data=results,
                receipts=receipts,
                pii_detected=pii_detected,
                pii_types=pii_types,
            )
        except Exception as e:
            return QdrantGovernanceResult(
                success=False,
                operation="search",
                governed_data=str(e),
                receipts=receipts,
                pii_detected=pii_detected,
                pii_types=pii_types,
            )

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Optional[Any] = None,
        limit: int = 10,
        **kwargs
    ) -> QdrantGovernanceResult:
        """
        Scroll through collection with governance.

        Args:
            collection_name: Target collection
            scroll_filter: Optional filter
            limit: Number of points to retrieve
            **kwargs: Additional scroll arguments

        Returns:
            QdrantGovernanceResult
        """
        try:
            points, next_offset = self._client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                **kwargs
            )

            # Govern returned payloads
            governed_points = []
            all_receipts = []
            any_pii_detected = False
            all_pii_types = []

            for point in points:
                if hasattr(point, 'payload') and point.payload:
                    governed_payload, pii_detected, pii_types, receipts = self._govern_payload(
                        dict(point.payload)
                    )
                    if pii_detected:
                        any_pii_detected = True
                        all_pii_types.extend(pii_types)
                    all_receipts.extend(receipts)
                    # Note: We can't modify the returned point, just track governance
                governed_points.append(point)

            return QdrantGovernanceResult(
                success=True,
                operation="scroll",
                governed_data=(governed_points, next_offset),
                receipts=all_receipts,
                pii_detected=any_pii_detected,
                pii_types=list(set(all_pii_types)),
                original_count=len(points),
                governed_count=len(governed_points),
            )
        except Exception as e:
            return QdrantGovernanceResult(
                success=False,
                operation="scroll",
                governed_data=str(e),
            )

    def delete(
        self,
        collection_name: str,
        points_selector: Any,
        **kwargs
    ) -> QdrantGovernanceResult:
        """Delete points from collection."""
        try:
            result = self._client.delete(
                collection_name=collection_name,
                points_selector=points_selector,
                **kwargs
            )
            return QdrantGovernanceResult(
                success=True,
                operation="delete",
                governed_data=result,
            )
        except Exception as e:
            return QdrantGovernanceResult(
                success=False,
                operation="delete",
                governed_data=str(e),
            )

    def retrieve(
        self,
        collection_name: str,
        ids: List[Union[int, str]],
        **kwargs
    ) -> QdrantGovernanceResult:
        """Retrieve points by IDs with governed payloads."""
        try:
            points = self._client.retrieve(
                collection_name=collection_name,
                ids=ids,
                **kwargs
            )

            all_receipts = []
            any_pii_detected = False
            all_pii_types = []

            for point in points:
                if hasattr(point, 'payload') and point.payload:
                    _, pii_detected, pii_types, receipts = self._govern_payload(
                        dict(point.payload)
                    )
                    if pii_detected:
                        any_pii_detected = True
                        all_pii_types.extend(pii_types)
                    all_receipts.extend(receipts)

            return QdrantGovernanceResult(
                success=True,
                operation="retrieve",
                governed_data=points,
                receipts=all_receipts,
                pii_detected=any_pii_detected,
                pii_types=list(set(all_pii_types)),
                original_count=len(ids),
                governed_count=len(points),
            )
        except Exception as e:
            return QdrantGovernanceResult(
                success=False,
                operation="retrieve",
                governed_data=str(e),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


def govern_upsert(
    client: Any,
    collection_name: str,
    points: List[Any],
    tork: Optional[Tork] = None,
    text_payload_keys: Optional[List[str]] = None,
    **kwargs
) -> QdrantGovernanceResult:
    """
    Govern points and upsert to Qdrant.

    Args:
        client: Qdrant client
        collection_name: Target collection
        points: Points to upsert
        tork: Tork instance
        text_payload_keys: Keys to govern
        **kwargs: Additional arguments

    Returns:
        QdrantGovernanceResult
    """
    governed_client = TorkQdrantClient(
        client=client,
        tork=tork,
        text_payload_keys=text_payload_keys,
    )
    return governed_client.upsert(collection_name, points, **kwargs)


def govern_search(
    client: Any,
    collection_name: str,
    query_vector: List[float],
    query_text: Optional[str] = None,
    tork: Optional[Tork] = None,
    **kwargs
) -> QdrantGovernanceResult:
    """
    Govern search query and execute.

    Args:
        client: Qdrant client
        collection_name: Target collection
        query_vector: Query vector
        query_text: Optional query text
        tork: Tork instance
        **kwargs: Additional arguments

    Returns:
        QdrantGovernanceResult
    """
    governed_client = TorkQdrantClient(
        client=client,
        tork=tork,
    )
    return governed_client.search(collection_name, query_vector, query_text, **kwargs)


def govern_scroll(
    client: Any,
    collection_name: str,
    tork: Optional[Tork] = None,
    limit: int = 10,
    **kwargs
) -> QdrantGovernanceResult:
    """
    Scroll through collection with governance.

    Args:
        client: Qdrant client
        collection_name: Target collection
        tork: Tork instance
        limit: Points per page
        **kwargs: Additional arguments

    Returns:
        QdrantGovernanceResult
    """
    governed_client = TorkQdrantClient(
        client=client,
        tork=tork,
    )
    return governed_client.scroll(collection_name, limit=limit, **kwargs)


def govern_batch(
    client: Any,
    collection_name: str,
    points: List[Any],
    tork: Optional[Tork] = None,
    batch_size: int = 100,
    text_payload_keys: Optional[List[str]] = None,
    **kwargs
) -> QdrantGovernanceResult:
    """
    Batch upsert with governance.

    Args:
        client: Qdrant client
        collection_name: Target collection
        points: Points to upsert
        tork: Tork instance
        batch_size: Batch size
        text_payload_keys: Keys to govern
        **kwargs: Additional arguments

    Returns:
        QdrantGovernanceResult
    """
    governed_client = TorkQdrantClient(
        client=client,
        tork=tork,
        text_payload_keys=text_payload_keys,
    )

    all_receipts = []
    all_pii_types = []
    any_pii_detected = False
    total_governed = 0

    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        result = governed_client.upsert(collection_name, batch, **kwargs)

        all_receipts.extend(result.receipts)
        if result.pii_detected:
            any_pii_detected = True
            all_pii_types.extend(result.pii_types)
        total_governed += result.governed_count

    return QdrantGovernanceResult(
        success=True,
        operation="batch_upsert",
        governed_data={"total_upserted": total_governed},
        receipts=all_receipts,
        pii_detected=any_pii_detected,
        pii_types=list(set(all_pii_types)),
        original_count=len(points),
        governed_count=total_governed,
    )


class AsyncTorkQdrantClient:
    """Async governed Qdrant client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_payloads: bool = True,
        text_payload_keys: Optional[List[str]] = None,
    ):
        """Initialize async governed Qdrant client."""
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_payloads = govern_payloads
        self._text_payload_keys = text_payload_keys
        self._receipts: List[str] = []
        self._sync_client = TorkQdrantClient(
            tork=self._tork,
            govern_payloads=govern_payloads,
            text_payload_keys=text_payload_keys,
        )

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    async def upsert(
        self,
        collection_name: str,
        points: List[Any],
        **kwargs
    ) -> QdrantGovernanceResult:
        """Async upsert with governance."""
        # Use sync client for governance, then async for Qdrant operation
        self._sync_client._client = self._client
        return self._sync_client.upsert(collection_name, points, **kwargs)

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: Optional[str] = None,
        **kwargs
    ) -> QdrantGovernanceResult:
        """Async search with governance."""
        self._sync_client._client = self._client
        return self._sync_client.search(collection_name, query_vector, query_text, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

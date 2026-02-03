"""
Tork Governance adapter for Arize ML observability.

Provides governance for Arize logging with automatic PII detection
and redaction in features, predictions, and tags.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class ArizeGovernanceResult:
    """Result of a governed Arize operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    redacted_fields: List[str] = field(default_factory=list)
    model_id: Optional[str] = None
    prediction_id: Optional[str] = None


class TorkArizeClient:
    """Governed Arize client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_features: bool = True,
        govern_predictions: bool = True,
        govern_tags: bool = True,
        govern_embeddings: bool = True,
        model_id: Optional[str] = None,
        model_version: Optional[str] = None,
    ):
        """
        Initialize governed Arize client.

        Args:
            client: Arize client instance
            tork: Tork governance instance
            config: Tork configuration
            govern_features: Whether to govern feature data
            govern_predictions: Whether to govern predictions
            govern_tags: Whether to govern tags
            govern_embeddings: Whether to govern embedding metadata
            model_id: Model ID for logging
            model_version: Model version
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_features = govern_features
        self._govern_predictions = govern_predictions
        self._govern_tags = govern_tags
        self._govern_embeddings = govern_embeddings
        self._model_id = model_id
        self._model_version = model_version
        self._receipts: List[str] = []

    @property
    def client(self) -> Any:
        """Get the underlying Arize client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the Arize client."""
        self._client = value

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    def _govern_value(self, value: Any) -> tuple:
        """Govern a value and return governed version with metadata."""
        if isinstance(value, str):
            result = self._tork.govern(value)
            self._receipts.append(result.receipt.receipt_id)
            return result.output, result.pii.has_pii, result.pii.types, [result.receipt.receipt_id]
        elif isinstance(value, dict):
            return self._govern_dict(value)
        elif isinstance(value, list):
            governed_list = []
            any_pii = False
            all_types = []
            all_receipts = []
            for item in value:
                gov_item, pii, types, receipts = self._govern_value(item)
                governed_list.append(gov_item)
                if pii:
                    any_pii = True
                    all_types.extend(types)
                all_receipts.extend(receipts)
            return governed_list, any_pii, list(set(all_types)), all_receipts
        return value, False, [], []

    def _govern_dict(self, data: Dict[str, Any]) -> tuple:
        """Govern all values in a dictionary."""
        governed = {}
        any_pii = False
        all_types = []
        all_receipts = []
        redacted_fields = []

        for key, value in data.items():
            gov_value, pii, types, receipts = self._govern_value(value)
            governed[key] = gov_value
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.append(key)
            all_receipts.extend(receipts)

        return governed, any_pii, list(set(all_types)), all_receipts, redacted_fields

    def log_prediction(
        self,
        prediction_id: str,
        features: Optional[Dict[str, Any]] = None,
        prediction_label: Optional[Any] = None,
        actual_label: Optional[Any] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ArizeGovernanceResult:
        """
        Log a prediction with governance.

        Args:
            prediction_id: Unique prediction ID
            features: Feature dictionary
            prediction_label: Predicted value
            actual_label: Actual/ground truth value
            tags: Tags dictionary
            **kwargs: Additional logging arguments

        Returns:
            ArizeGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []

        governed_features = features
        governed_prediction = prediction_label
        governed_actual = actual_label
        governed_tags = tags

        # Govern features
        if features and self._govern_features:
            governed_features, pii, types, receipts, fields = self._govern_dict(features)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend([f'features.{f}' for f in fields])

        # Govern prediction label if string
        if prediction_label and self._govern_predictions and isinstance(prediction_label, str):
            result = self._tork.govern(prediction_label)
            governed_prediction = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                all_redacted_fields.append('prediction_label')

        # Govern actual label if string
        if actual_label and self._govern_predictions and isinstance(actual_label, str):
            result = self._tork.govern(actual_label)
            governed_actual = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                all_redacted_fields.append('actual_label')

        # Govern tags
        if tags and self._govern_tags:
            governed_tags, pii, types, receipts, fields = self._govern_dict(tags)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend([f'tags.{f}' for f in fields])

        try:
            if self._client:
                result = self._client.log(
                    prediction_id=prediction_id,
                    features=governed_features,
                    prediction_label=governed_prediction,
                    actual_label=governed_actual,
                    tags=governed_tags,
                    model_id=self._model_id,
                    model_version=self._model_version,
                    **kwargs
                )
            else:
                result = {
                    'prediction_id': prediction_id,
                    'features': governed_features,
                    'prediction_label': governed_prediction,
                    'actual_label': governed_actual,
                    'tags': governed_tags,
                }

            return ArizeGovernanceResult(
                success=True,
                operation="log_prediction",
                governed_data=result,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                model_id=self._model_id,
                prediction_id=prediction_id,
            )
        except Exception as e:
            return ArizeGovernanceResult(
                success=False,
                operation="log_prediction",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                prediction_id=prediction_id,
            )

    def log_embedding(
        self,
        prediction_id: str,
        embedding_features: Dict[str, Any],
        embedding_vector: List[float],
        embedding_text: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ArizeGovernanceResult:
        """
        Log an embedding with governance.

        Args:
            prediction_id: Unique prediction ID
            embedding_features: Embedding feature metadata
            embedding_vector: The embedding vector (not governed)
            embedding_text: Original text for the embedding
            tags: Tags dictionary
            **kwargs: Additional logging arguments

        Returns:
            ArizeGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []

        governed_features = embedding_features
        governed_text = embedding_text
        governed_tags = tags

        # Govern embedding features
        if self._govern_embeddings:
            governed_features, pii, types, receipts, fields = self._govern_dict(embedding_features)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend([f'embedding_features.{f}' for f in fields])

        # Govern embedding text
        if embedding_text and self._govern_embeddings:
            result = self._tork.govern(embedding_text)
            governed_text = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                all_redacted_fields.append('embedding_text')

        # Govern tags
        if tags and self._govern_tags:
            governed_tags, pii, types, receipts, fields = self._govern_dict(tags)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend([f'tags.{f}' for f in fields])

        try:
            if self._client:
                result = self._client.log(
                    prediction_id=prediction_id,
                    embedding_features=governed_features,
                    embedding_vector=embedding_vector,  # Vectors not governed
                    tags=governed_tags,
                    model_id=self._model_id,
                    model_version=self._model_version,
                    **kwargs
                )
            else:
                result = {
                    'prediction_id': prediction_id,
                    'embedding_features': governed_features,
                    'embedding_text': governed_text,
                    'tags': governed_tags,
                }

            return ArizeGovernanceResult(
                success=True,
                operation="log_embedding",
                governed_data=result,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                model_id=self._model_id,
                prediction_id=prediction_id,
            )
        except Exception as e:
            return ArizeGovernanceResult(
                success=False,
                operation="log_embedding",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                prediction_id=prediction_id,
            )

    def log_batch(
        self,
        predictions: List[Dict[str, Any]],
        **kwargs
    ) -> ArizeGovernanceResult:
        """
        Log a batch of predictions with governance.

        Args:
            predictions: List of prediction dictionaries
            **kwargs: Additional logging arguments

        Returns:
            ArizeGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []
        governed_predictions = []

        for pred in predictions:
            result = self.log_prediction(
                prediction_id=pred.get('prediction_id', str(datetime.now().timestamp())),
                features=pred.get('features'),
                prediction_label=pred.get('prediction_label'),
                actual_label=pred.get('actual_label'),
                tags=pred.get('tags'),
            )
            all_receipts.extend(result.receipts)
            if result.pii_detected:
                any_pii = True
                all_types.extend(result.pii_types)
                all_redacted_fields.extend(result.redacted_fields)
            governed_predictions.append(result.governed_data)

        return ArizeGovernanceResult(
            success=True,
            operation="log_batch",
            governed_data=governed_predictions,
            receipts=all_receipts,
            pii_detected=any_pii,
            pii_types=list(set(all_types)),
            redacted_fields=list(set(all_redacted_fields)),
            model_id=self._model_id,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


def govern_log_prediction(
    client: Any,
    prediction_id: str,
    features: Optional[Dict[str, Any]] = None,
    prediction_label: Optional[Any] = None,
    tork: Optional[Tork] = None,
    **kwargs
) -> ArizeGovernanceResult:
    """
    Govern and log a prediction to Arize.

    Args:
        client: Arize client
        prediction_id: Prediction ID
        features: Feature data
        prediction_label: Prediction value
        tork: Tork instance
        **kwargs: Additional arguments

    Returns:
        ArizeGovernanceResult
    """
    governed_client = TorkArizeClient(client=client, tork=tork)
    return governed_client.log_prediction(
        prediction_id=prediction_id,
        features=features,
        prediction_label=prediction_label,
        **kwargs
    )


def govern_log_embedding(
    client: Any,
    prediction_id: str,
    embedding_features: Dict[str, Any],
    embedding_vector: List[float],
    tork: Optional[Tork] = None,
    **kwargs
) -> ArizeGovernanceResult:
    """
    Govern and log an embedding to Arize.

    Args:
        client: Arize client
        prediction_id: Prediction ID
        embedding_features: Embedding metadata
        embedding_vector: Embedding vector
        tork: Tork instance
        **kwargs: Additional arguments

    Returns:
        ArizeGovernanceResult
    """
    governed_client = TorkArizeClient(client=client, tork=tork)
    return governed_client.log_embedding(
        prediction_id=prediction_id,
        embedding_features=embedding_features,
        embedding_vector=embedding_vector,
        **kwargs
    )


def arize_governed(
    tork: Optional[Tork] = None,
    model_id: Optional[str] = None,
    govern_features: bool = True,
    govern_predictions: bool = True,
):
    """
    Create a governed Arize client.

    Args:
        tork: Tork instance
        model_id: Model ID
        govern_features: Whether to govern features
        govern_predictions: Whether to govern predictions

    Returns:
        TorkArizeClient
    """
    return TorkArizeClient(
        tork=tork,
        model_id=model_id,
        govern_features=govern_features,
        govern_predictions=govern_predictions,
    )

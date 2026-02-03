"""
Tork Governance adapter for Helicone LLM observability.

Provides governance for Helicone logging with automatic PII detection
and redaction in prompts, completions, and metadata.
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import functools

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class HeliconeGovernanceResult:
    """Result of a governed Helicone operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    redacted_fields: List[str] = field(default_factory=list)
    request_id: Optional[str] = None


class TorkHeliconeClient:
    """Governed Helicone client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_prompts: bool = True,
        govern_completions: bool = True,
        govern_metadata: bool = True,
        api_key: Optional[str] = None,
    ):
        """
        Initialize governed Helicone client.

        Args:
            client: Helicone client or OpenAI client with Helicone proxy
            tork: Tork governance instance
            config: Tork configuration
            govern_prompts: Whether to govern prompt content
            govern_completions: Whether to govern completion content
            govern_metadata: Whether to govern metadata
            api_key: Helicone API key (optional)
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_prompts = govern_prompts
        self._govern_completions = govern_completions
        self._govern_metadata = govern_metadata
        self._api_key = api_key
        self._receipts: List[str] = []

    @property
    def client(self) -> Any:
        """Get the underlying client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the client."""
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

    def _govern_messages(self, messages: List[Dict[str, Any]]) -> tuple:
        """Govern chat messages."""
        governed_messages = []
        any_pii = False
        all_types = []
        all_receipts = []
        redacted_fields = []

        for message in messages:
            governed_msg = message.copy()
            if 'content' in message and isinstance(message['content'], str):
                result = self._tork.govern(message['content'])
                governed_msg['content'] = result.output
                self._receipts.append(result.receipt.receipt_id)
                all_receipts.append(result.receipt.receipt_id)
                if result.pii.has_pii:
                    any_pii = True
                    all_types.extend(result.pii.types)
                    redacted_fields.append('content')
            governed_messages.append(governed_msg)

        return governed_messages, any_pii, list(set(all_types)), all_receipts, redacted_fields

    def log_request(
        self,
        request_data: Dict[str, Any],
        **kwargs
    ) -> HeliconeGovernanceResult:
        """
        Log a request with governance.

        Args:
            request_data: Request data to log
            **kwargs: Additional logging arguments

        Returns:
            HeliconeGovernanceResult
        """
        governed_data = request_data.copy()
        all_receipts = []
        any_pii = False
        all_types = []
        redacted_fields = []

        if self._govern_prompts:
            # Govern prompt/messages
            if 'prompt' in request_data:
                result = self._tork.govern(request_data['prompt'])
                governed_data['prompt'] = result.output
                all_receipts.append(result.receipt.receipt_id)
                if result.pii.has_pii:
                    any_pii = True
                    all_types.extend(result.pii.types)
                    redacted_fields.append('prompt')

            if 'messages' in request_data:
                gov_msgs, pii, types, receipts, fields = self._govern_messages(request_data['messages'])
                governed_data['messages'] = gov_msgs
                all_receipts.extend(receipts)
                if pii:
                    any_pii = True
                    all_types.extend(types)
                    redacted_fields.extend(fields)

        if self._govern_metadata and 'metadata' in request_data:
            gov_meta, pii, types, receipts, fields = self._govern_dict(request_data['metadata'])
            governed_data['metadata'] = gov_meta
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.extend([f'metadata.{f}' for f in fields])

        # Add governance metadata
        governed_data['_tork_governance'] = {
            'enabled': True,
            'receipts': all_receipts,
            'pii_detected': any_pii,
        }

        try:
            if self._client and hasattr(self._client, 'log_request'):
                result = self._client.log_request(governed_data, **kwargs)
            else:
                result = governed_data

            return HeliconeGovernanceResult(
                success=True,
                operation="log_request",
                governed_data=result,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
            )
        except Exception as e:
            return HeliconeGovernanceResult(
                success=False,
                operation="log_request",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
            )

    def log_response(
        self,
        response_data: Dict[str, Any],
        request_id: Optional[str] = None,
        **kwargs
    ) -> HeliconeGovernanceResult:
        """
        Log a response with governance.

        Args:
            response_data: Response data to log
            request_id: Associated request ID
            **kwargs: Additional logging arguments

        Returns:
            HeliconeGovernanceResult
        """
        governed_data = response_data.copy()
        all_receipts = []
        any_pii = False
        all_types = []
        redacted_fields = []

        if self._govern_completions:
            # Govern completion content
            if 'choices' in response_data:
                governed_choices = []
                for choice in response_data['choices']:
                    gov_choice = choice.copy()
                    if 'text' in choice:
                        result = self._tork.govern(choice['text'])
                        gov_choice['text'] = result.output
                        all_receipts.append(result.receipt.receipt_id)
                        if result.pii.has_pii:
                            any_pii = True
                            all_types.extend(result.pii.types)
                            redacted_fields.append('choices.text')
                    if 'message' in choice and 'content' in choice['message']:
                        result = self._tork.govern(choice['message']['content'])
                        gov_choice['message'] = {**choice['message'], 'content': result.output}
                        all_receipts.append(result.receipt.receipt_id)
                        if result.pii.has_pii:
                            any_pii = True
                            all_types.extend(result.pii.types)
                            redacted_fields.append('choices.message.content')
                    governed_choices.append(gov_choice)
                governed_data['choices'] = governed_choices

        # Add governance metadata
        governed_data['_tork_governance'] = {
            'enabled': True,
            'receipts': all_receipts,
            'pii_detected': any_pii,
        }

        try:
            if self._client and hasattr(self._client, 'log_response'):
                result = self._client.log_response(governed_data, request_id=request_id, **kwargs)
            else:
                result = governed_data

            return HeliconeGovernanceResult(
                success=True,
                operation="log_response",
                governed_data=result,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                request_id=request_id,
            )
        except Exception as e:
            return HeliconeGovernanceResult(
                success=False,
                operation="log_response",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                request_id=request_id,
            )

    def create_governed_openai_client(self, openai_client: Any) -> Any:
        """
        Wrap an OpenAI client to add governance to Helicone logging.

        Args:
            openai_client: OpenAI client configured with Helicone proxy

        Returns:
            Wrapped OpenAI client with governance
        """
        governed_client = openai_client
        original_create = openai_client.chat.completions.create

        @functools.wraps(original_create)
        def governed_create(*args, **kwargs):
            # Govern messages before sending
            if 'messages' in kwargs and self._govern_prompts:
                gov_msgs, _, _, _, _ = self._govern_messages(kwargs['messages'])
                kwargs['messages'] = gov_msgs
            return original_create(*args, **kwargs)

        governed_client.chat.completions.create = governed_create
        return governed_client

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


def govern_log_request(
    request_data: Dict[str, Any],
    tork: Optional[Tork] = None,
    client: Any = None,
    **kwargs
) -> HeliconeGovernanceResult:
    """
    Govern and log a request to Helicone.

    Args:
        request_data: Request data to log
        tork: Tork instance
        client: Helicone client
        **kwargs: Additional arguments

    Returns:
        HeliconeGovernanceResult
    """
    governed_client = TorkHeliconeClient(client=client, tork=tork)
    return governed_client.log_request(request_data, **kwargs)


def govern_log_response(
    response_data: Dict[str, Any],
    tork: Optional[Tork] = None,
    client: Any = None,
    request_id: Optional[str] = None,
    **kwargs
) -> HeliconeGovernanceResult:
    """
    Govern and log a response to Helicone.

    Args:
        response_data: Response data to log
        tork: Tork instance
        client: Helicone client
        request_id: Associated request ID
        **kwargs: Additional arguments

    Returns:
        HeliconeGovernanceResult
    """
    governed_client = TorkHeliconeClient(client=client, tork=tork)
    return governed_client.log_response(response_data, request_id=request_id, **kwargs)


def helicone_governed(
    tork: Optional[Tork] = None,
    govern_prompts: bool = True,
    govern_completions: bool = True,
):
    """
    Decorator to add Helicone governance to a function.

    Args:
        tork: Tork instance
        govern_prompts: Whether to govern prompts
        govern_completions: Whether to govern completions

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = TorkHeliconeClient(
                tork=tork,
                govern_prompts=govern_prompts,
                govern_completions=govern_completions,
            )
            # Add governance client to kwargs
            kwargs['_tork_helicone'] = client
            return func(*args, **kwargs)
        return wrapper
    return decorator

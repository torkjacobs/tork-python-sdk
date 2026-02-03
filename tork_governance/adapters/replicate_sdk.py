"""
Tork Governance adapter for Replicate SDK.

Provides governance for Replicate model predictions
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.replicate_sdk import TorkReplicateClient

    client = TorkReplicateClient(api_token="...", tork=tork)
    output = client.run("meta/llama-2-70b-chat", input={"prompt": "Hello"})
"""

from typing import Any, Dict, List, Optional, Union, Iterator
from functools import wraps


class TorkReplicateClient:
    """Governed Replicate client wrapper."""

    def __init__(
        self,
        api_token: str = None,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.api_token = api_token
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the Replicate client."""
        if self._client is None:
            try:
                import replicate
                if self.api_token:
                    replicate.api_token = self.api_token
                self._client = replicate
            except ImportError:
                raise ImportError(
                    "replicate is required. Install with: pip install replicate"
                )
        return self._client

    def _govern_input_dict(self, input_dict: Dict[str, Any]) -> tuple:
        """Govern text fields in input dictionary."""
        receipts = []
        governed = {}

        text_fields = ['prompt', 'input', 'text', 'message', 'query', 'system_prompt']

        for key, value in input_dict.items():
            if key in text_fields and isinstance(value, str) and self.govern_input:
                result = self.tork.govern(value)
                receipts.append(result.receipt)
                governed[key] = result.output if result.action in ('redact', 'REDACT') else value
            else:
                governed[key] = value

        return governed, receipts

    def run(
        self,
        model: str,
        input: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Run governed prediction."""
        client = self._get_client()

        # Govern input
        governed_input, receipts = self._govern_input_dict(input)

        # Run prediction
        output = client.run(model, input=governed_input, **kwargs)

        # Handle different output types
        if isinstance(output, str):
            # Govern string output
            if self.govern_output:
                result = self.tork.govern(output)
                output = result.output if result.action in ('redact', 'REDACT') else output
        elif isinstance(output, list):
            # Join list output (common for text generation)
            text = "".join(output) if all(isinstance(o, str) for o in output) else output
            if self.govern_output and isinstance(text, str):
                result = self.tork.govern(text)
                text = result.output if result.action in ('redact', 'REDACT') else text
            output = text

        return {
            "output": output,
            "_tork_receipts": receipts
        }

    def stream(
        self,
        model: str,
        input: Dict[str, Any],
        **kwargs
    ) -> Iterator[Any]:
        """Stream governed prediction."""
        client = self._get_client()

        # Govern input
        governed_input, _ = self._govern_input_dict(input)

        # Stream prediction
        for event in client.stream(model, input=governed_input, **kwargs):
            yield event

    def predictions_create(
        self,
        model: str = None,
        version: str = None,
        input: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create governed prediction."""
        client = self._get_client()

        # Govern input
        governed_input, receipts = self._govern_input_dict(input or {})

        prediction = client.predictions.create(
            model=model,
            version=version,
            input=governed_input,
            **kwargs
        )

        return {
            "id": prediction.id,
            "model": prediction.model,
            "version": prediction.version,
            "status": prediction.status,
            "_tork_receipts": receipts
        }

    def predictions_get(self, prediction_id: str) -> Dict[str, Any]:
        """Get prediction with governed output."""
        client = self._get_client()

        prediction = client.predictions.get(prediction_id)
        output = prediction.output

        # Govern output if text
        if self.govern_output and isinstance(output, str):
            result = self.tork.govern(output)
            output = result.output if result.action in ('redact', 'REDACT') else output
        elif self.govern_output and isinstance(output, list):
            text = "".join(output) if all(isinstance(o, str) for o in output) else output
            if isinstance(text, str):
                result = self.tork.govern(text)
                output = result.output if result.action in ('redact', 'REDACT') else text

        return {
            "id": prediction.id,
            "model": prediction.model,
            "version": prediction.version,
            "status": prediction.status,
            "output": output
        }


class AsyncTorkReplicateClient:
    """Async governed Replicate client wrapper."""

    def __init__(
        self,
        api_token: str = None,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.api_token = api_token
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the async Replicate client."""
        if self._client is None:
            try:
                import replicate
                if self.api_token:
                    replicate.api_token = self.api_token
                self._client = replicate
            except ImportError:
                raise ImportError(
                    "replicate is required. Install with: pip install replicate"
                )
        return self._client

    def _govern_input_dict(self, input_dict: Dict[str, Any]) -> tuple:
        """Govern text fields in input dictionary."""
        receipts = []
        governed = {}

        text_fields = ['prompt', 'input', 'text', 'message', 'query', 'system_prompt']

        for key, value in input_dict.items():
            if key in text_fields and isinstance(value, str) and self.govern_input:
                result = self.tork.govern(value)
                receipts.append(result.receipt)
                governed[key] = result.output if result.action in ('redact', 'REDACT') else value
            else:
                governed[key] = value

        return governed, receipts

    async def run(
        self,
        model: str,
        input: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Run governed async prediction."""
        client = self._get_client()

        governed_input, receipts = self._govern_input_dict(input)

        output = await client.async_run(model, input=governed_input, **kwargs)

        if isinstance(output, str) and self.govern_output:
            result = self.tork.govern(output)
            output = result.output if result.action in ('redact', 'REDACT') else output
        elif isinstance(output, list):
            text = "".join(output) if all(isinstance(o, str) for o in output) else output
            if self.govern_output and isinstance(text, str):
                result = self.tork.govern(text)
                output = result.output if result.action in ('redact', 'REDACT') else text

        return {
            "output": output,
            "_tork_receipts": receipts
        }

    async def stream(
        self,
        model: str,
        input: Dict[str, Any],
        **kwargs
    ):
        """Stream governed async prediction."""
        client = self._get_client()

        governed_input, _ = self._govern_input_dict(input)

        async for event in client.async_stream(model, input=governed_input, **kwargs):
            yield event


def replicate_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Replicate API calls."""
    text_fields = ['prompt', 'input', 'text', 'message', 'query', 'system_prompt']

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'input' in kwargs and govern_input:
                governed = {}
                for key, value in kwargs['input'].items():
                    if key in text_fields and isinstance(value, str):
                        result = tork.govern(value)
                        governed[key] = result.output if result.action in ('redact', 'REDACT') else value
                    else:
                        governed[key] = value
                kwargs['input'] = governed
            return func(*args, **kwargs)
        return wrapper
    return decorator

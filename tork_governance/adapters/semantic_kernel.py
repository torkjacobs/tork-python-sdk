"""
Microsoft Semantic Kernel adapter for Tork Governance.

Provides plugins and filters for Semantic Kernel applications.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkSKFilter:
    """
    Semantic Kernel filter for Tork governance.

    Example:
        >>> from tork_governance.adapters.semantic_kernel import TorkSKFilter
        >>> from semantic_kernel import Kernel
        >>>
        >>> kernel = Kernel()
        >>> tork_filter = TorkSKFilter()
        >>> # Add as function invocation filter
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    async def on_function_invocation(self, context: Any) -> Any:
        """
        Filter function invocations with governance.

        Args:
            context: Semantic Kernel function context

        Returns:
            Modified context with governed arguments
        """
        if hasattr(context, "arguments"):
            governed_args = {}
            for key, value in context.arguments.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_args[key] = result.output
                    self.receipts.append({
                        "type": "function_input",
                        "argument": key,
                        "receipt_id": result.receipt.receipt_id,
                        "action": result.action.value
                    })
                else:
                    governed_args[key] = value
            context.arguments = governed_args
        return context

    async def on_function_result(self, context: Any, result: Any) -> Any:
        """Filter function results with governance."""
        if isinstance(result, str):
            gov_result = self.tork.govern(result)
            self.receipts.append({
                "type": "function_output",
                "receipt_id": gov_result.receipt.receipt_id
            })
            return gov_result.output
        return result

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkSKPlugin:
    """
    Semantic Kernel plugin with Tork governance.

    Example:
        >>> from tork_governance.adapters.semantic_kernel import TorkSKPlugin
        >>>
        >>> plugin = TorkSKPlugin()
        >>>
        >>> @plugin.governed_function
        >>> async def my_function(input: str) -> str:
        >>>     return f"Processed: {input}"
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def governed_function(self, func: Callable) -> Callable:
        """Decorator to wrap SK functions with governance."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Govern input arguments
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_kwargs[key] = result.output
                    self.receipts.append({
                        "type": "plugin_input",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Call function
            output = await func(*args, **governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = self.tork.govern(output)
                self.receipts.append({
                    "type": "plugin_output",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            return output

        return wrapper

    def govern(self, text: str) -> str:
        """Direct governance method for use in SK prompts."""
        result = self.tork.govern(text)
        self.receipts.append({
            "type": "direct_govern",
            "receipt_id": result.receipt.receipt_id
        })
        return result.output

    def check_pii(self, text: str) -> bool:
        """Check if text contains PII."""
        result = self.tork.govern(text)
        return result.pii.has_pii

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkSKPromptFilter:
    """Filter for governing prompts before rendering."""

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    async def on_prompt_render(self, prompt: str) -> str:
        """Govern rendered prompt."""
        result = self.tork.govern(prompt)
        self.receipts.append({
            "type": "prompt_render",
            "receipt_id": result.receipt.receipt_id
        })
        return result.output

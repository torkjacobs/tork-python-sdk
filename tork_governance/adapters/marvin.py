"""
Marvin adapter for Tork Governance.

Provides AI function wrappers and classifier governance for Marvin AI functions.
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction

T = TypeVar("T")


class TorkMarvinAI:
    """
    Wrapper for Marvin AI with governance.

    Example:
        >>> from tork_governance.adapters.marvin import TorkMarvinAI
        >>> import marvin
        >>>
        >>> ai = TorkMarvinAI()
        >>>
        >>> result = ai.classify("Contact: test@email.com", labels=["pii", "safe"])
        >>> extracted = ai.extract("Email: user@domain.com", target=str)
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def classify(self, text: str, labels: List[str], **kwargs) -> str:
        """Classify text with governance."""
        try:
            import marvin
        except ImportError:
            raise ImportError("marvin package required: pip install marvin")

        # Govern input
        input_result = self.tork.govern(text)
        self.receipts.append({
            "type": "classify_input",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        # Classify
        result = marvin.classify(input_result.output, labels=labels, **kwargs)
        return result

    def extract(self, text: str, target: Type[T], **kwargs) -> List[T]:
        """Extract structured data with governance."""
        try:
            import marvin
        except ImportError:
            raise ImportError("marvin package required: pip install marvin")

        # Govern input
        input_result = self.tork.govern(text)
        self.receipts.append({
            "type": "extract_input",
            "receipt_id": input_result.receipt.receipt_id
        })

        # Extract
        results = marvin.extract(input_result.output, target=target, **kwargs)

        # Govern extracted values
        governed_results = []
        for item in results:
            if isinstance(item, str):
                result = self.tork.govern(item)
                governed_results.append(result.output)
                self.receipts.append({
                    "type": "extract_output",
                    "receipt_id": result.receipt.receipt_id
                })
            elif hasattr(item, '__dict__'):
                for field, value in vars(item).items():
                    if isinstance(value, str):
                        result = self.tork.govern(value)
                        setattr(item, field, result.output)
                governed_results.append(item)
            else:
                governed_results.append(item)

        return governed_results

    def cast(self, text: str, target: Type[T], **kwargs) -> T:
        """Cast text to type with governance."""
        try:
            import marvin
        except ImportError:
            raise ImportError("marvin package required: pip install marvin")

        input_result = self.tork.govern(text)
        self.receipts.append({
            "type": "cast_input",
            "receipt_id": input_result.receipt.receipt_id
        })

        result = marvin.cast(input_result.output, target=target, **kwargs)

        if isinstance(result, str):
            output_result = self.tork.govern(result)
            return output_result.output

        return result

    def generate(self, target: Type[T], instructions: str = "", **kwargs) -> T:
        """Generate data with governance."""
        try:
            import marvin
        except ImportError:
            raise ImportError("marvin package required: pip install marvin")

        if instructions:
            input_result = self.tork.govern(instructions)
            instructions = input_result.output
            self.receipts.append({
                "type": "generate_instructions",
                "receipt_id": input_result.receipt.receipt_id
            })

        result = marvin.generate(target=target, instructions=instructions, **kwargs)

        # Govern generated content
        if isinstance(result, str):
            output_result = self.tork.govern(result)
            return output_result.output
        elif hasattr(result, '__dict__'):
            for field, value in vars(result).items():
                if isinstance(value, str):
                    gov_result = self.tork.govern(value)
                    setattr(result, field, gov_result.output)

        return result

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_fn(tork: Optional[Tork] = None):
    """
    Decorator for governed Marvin AI functions.

    Example:
        >>> @governed_fn()
        >>> @marvin.fn
        >>> def summarize(text: str) -> str:
        >>>     '''Summarize the text'''
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string args
            governed_args = []
            for arg in args:
                if isinstance(arg, str):
                    result = _tork.govern(arg)
                    governed_args.append(result.output)
                    receipts.append({
                        "type": "fn_input_arg",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_args.append(arg)

            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    governed_kwargs[key] = result.output
                    receipts.append({
                        "type": "fn_input_kwarg",
                        "key": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute
            output = func(*governed_args, **governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = _tork.govern(output)
                receipts.append({
                    "type": "fn_output",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            return output

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


def governed_classifier(tork: Optional[Tork] = None):
    """
    Decorator for governed Marvin classifiers.

    Example:
        >>> @governed_classifier()
        >>> def classify_sentiment(text: str) -> Literal["positive", "negative", "neutral"]:
        >>>     return marvin.classify(text, labels=["positive", "negative", "neutral"])
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(text: str, *args, **kwargs):
            # Govern input
            result = _tork.govern(text)
            receipts.append({
                "type": "classifier_input",
                "receipt_id": result.receipt.receipt_id
            })

            # Classify
            return func(result.output, *args, **kwargs)

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


class TorkMarvinImage:
    """Wrapper for Marvin image functions with governance."""

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def caption(self, image: Any, instructions: str = "") -> str:
        """Caption image with governed instructions."""
        try:
            import marvin
        except ImportError:
            raise ImportError("marvin package required: pip install marvin")

        if instructions:
            result = self.tork.govern(instructions)
            instructions = result.output
            self.receipts.append({
                "type": "caption_instructions",
                "receipt_id": result.receipt.receipt_id
            })

        caption = marvin.image.caption(image, instructions=instructions)

        output_result = self.tork.govern(caption)
        self.receipts.append({
            "type": "caption_output",
            "receipt_id": output_result.receipt.receipt_id
        })
        return output_result.output

    def get_receipts(self) -> List[Dict]:
        return self.receipts

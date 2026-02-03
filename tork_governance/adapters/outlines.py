"""
Outlines adapter for Tork Governance.

Provides generator wrappers and model governance for structured generation.
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction

T = TypeVar("T")


class TorkOutlinesGenerator:
    """
    Wrapper for Outlines generators with governance.

    Example:
        >>> from tork_governance.adapters.outlines import TorkOutlinesGenerator
        >>> import outlines
        >>>
        >>> model = outlines.models.transformers("gpt2")
        >>> generator = outlines.generate.text(model)
        >>> governed_gen = TorkOutlinesGenerator(generator)
        >>>
        >>> result = governed_gen("Email: test@example.com")
    """

    def __init__(self, generator: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.generator = generator
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self.govern(text)

    def __call__(self, prompt: str, **kwargs) -> Any:
        """Generate with governed input and output."""
        # Govern input
        input_result = self.tork.govern(prompt)
        self.receipts.append({
            "type": "generator_input",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        # Generate
        output = self.generator(input_result.output, **kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "generator_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output

        return output

    def stream(self, prompt: str, **kwargs):
        """Stream generation with governance."""
        input_result = self.tork.govern(prompt)

        for chunk in self.generator.stream(input_result.output, **kwargs):
            if isinstance(chunk, str):
                result = self.tork.govern(chunk)
                yield result.output
            else:
                yield chunk

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkOutlinesModel:
    """
    Wrapper for Outlines models with governance.

    Example:
        >>> from tork_governance.adapters.outlines import TorkOutlinesModel
        >>> import outlines
        >>>
        >>> model = outlines.models.transformers("gpt2")
        >>> governed_model = TorkOutlinesModel(model)
    """

    def __init__(self, model: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.model = model
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate with governance."""
        input_result = self.tork.govern(prompt)
        self.receipts.append({
            "type": "model_input",
            "receipt_id": input_result.receipt.receipt_id
        })

        output = self.model.generate(input_result.output, **kwargs)

        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "model_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output

        return output

    def generate_json(self, prompt: str, schema: Type[T], **kwargs) -> T:
        """Generate JSON with governance."""
        input_result = self.tork.govern(prompt)

        output = self.model.generate_json(input_result.output, schema, **kwargs)

        # Govern string fields in structured output
        if hasattr(output, '__dict__'):
            for field, value in vars(output).items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    setattr(output, field, result.output)
                    self.receipts.append({
                        "type": "json_field",
                        "field": field,
                        "receipt_id": result.receipt.receipt_id
                    })

        return output

    def generate_choice(self, prompt: str, choices: List[str], **kwargs) -> str:
        """Generate choice with governance."""
        input_result = self.tork.govern(prompt)
        return self.model.generate_choice(input_result.output, choices, **kwargs)

    def generate_regex(self, prompt: str, pattern: str, **kwargs) -> str:
        """Generate regex-constrained output with governance."""
        input_result = self.tork.govern(prompt)
        output = self.model.generate_regex(input_result.output, pattern, **kwargs)

        output_result = self.tork.govern(output)
        self.receipts.append({
            "type": "regex_output",
            "receipt_id": output_result.receipt.receipt_id
        })
        return output_result.output

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_generate(tork: Optional[Tork] = None):
    """
    Decorator for governed Outlines generation.

    Example:
        >>> @governed_generate()
        >>> def generate_text(prompt: str) -> str:
        >>>     return generator(prompt)
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(prompt: str, *args, **kwargs):
            # Govern input
            input_result = _tork.govern(prompt)
            receipts.append({
                "type": "decorated_input",
                "receipt_id": input_result.receipt.receipt_id
            })

            # Generate
            output = func(input_result.output, *args, **kwargs)

            # Govern output
            if isinstance(output, str):
                output_result = _tork.govern(output)
                receipts.append({
                    "type": "decorated_output",
                    "receipt_id": output_result.receipt.receipt_id
                })
                return output_result.output

            return output

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


class TorkOutlinesPrompt:
    """Wrapper for Outlines prompts with governance."""

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def template(self, template_str: str) -> Callable:
        """Create governed prompt template."""
        def render(**kwargs):
            # Govern template variables
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_kwargs[key] = result.output
                    self.receipts.append({
                        "type": "template_variable",
                        "variable": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            return template_str.format(**governed_kwargs)

        return render

    def get_receipts(self) -> List[Dict]:
        return self.receipts

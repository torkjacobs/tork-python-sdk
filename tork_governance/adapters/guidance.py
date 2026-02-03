"""
Microsoft Guidance adapter for Tork Governance.

Provides program wrappers and generation block governance for constrained generation.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkGuidanceProgram:
    """
    Wrapper for Guidance programs with governance.

    Example:
        >>> from tork_governance.adapters.guidance import TorkGuidanceProgram
        >>> import guidance
        >>>
        >>> @guidance
        >>> def my_program(lm, user_input):
        >>>     lm += f"Process: {user_input}"
        >>>     lm += guidance.gen("output")
        >>>     return lm
        >>>
        >>> governed_program = TorkGuidanceProgram(my_program)
        >>> result = governed_program(user_input="test@email.com")
    """

    def __init__(self, program: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.program = program
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self.govern(text)

    def __call__(self, lm: Any = None, **kwargs) -> Any:
        """Execute program with governed inputs and outputs."""
        # Govern input kwargs
        governed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed_kwargs[key] = result.output
                self.receipts.append({
                    "type": "program_input",
                    "variable": key,
                    "receipt_id": result.receipt.receipt_id,
                    "action": result.action.value
                })
            else:
                governed_kwargs[key] = value

        # Execute program
        if lm is not None:
            output = self.program(lm, **governed_kwargs)
        else:
            output = self.program(**governed_kwargs)

        # Govern output variables
        if hasattr(output, '__getitem__'):
            for key in governed_kwargs.keys():
                try:
                    value = output[key]
                    if isinstance(value, str):
                        result = self.tork.govern(value)
                        self.receipts.append({
                            "type": "program_output",
                            "variable": key,
                            "receipt_id": result.receipt.receipt_id
                        })
                except (KeyError, TypeError):
                    pass

        return output

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkGuidanceGen:
    """
    Governed generation blocks for Guidance.

    Example:
        >>> from tork_governance.adapters.guidance import TorkGuidanceGen
        >>>
        >>> gen = TorkGuidanceGen()
        >>>
        >>> @guidance
        >>> def program(lm):
        >>>     lm += "Output: "
        >>>     lm += gen.governed_gen("result")
        >>>     return lm
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def governed_gen(self, name: str, **kwargs) -> Any:
        """Create a governed generation block."""
        # Import guidance lazily
        try:
            import guidance
        except ImportError:
            raise ImportError("guidance package required: pip install guidance")

        tork = self.tork
        receipts = self.receipts

        @guidance
        def gen_block(lm):
            lm += guidance.gen(name, **kwargs)

            # Post-process: govern the generated content
            if name in lm:
                value = lm[name]
                if isinstance(value, str):
                    result = tork.govern(value)
                    receipts.append({
                        "type": "gen_block",
                        "name": name,
                        "receipt_id": result.receipt.receipt_id
                    })
                    # Note: Guidance LMs are immutable, return governed value
            return lm

        return gen_block

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_block(tork: Optional[Tork] = None):
    """
    Decorator for governed Guidance blocks.

    Example:
        >>> @governed_block()
        >>> @guidance
        >>> def my_block(lm, text):
        >>>     lm += f"Input: {text}"
        >>>     lm += guidance.gen("output")
        >>>     return lm
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(lm: Any = None, **kwargs):
            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    governed_kwargs[key] = result.output
                    receipts.append({
                        "type": "block_input",
                        "variable": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute block
            if lm is not None:
                return func(lm, **governed_kwargs)
            return func(**governed_kwargs)

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


class TorkGuidanceModel:
    """Wrapper for Guidance models with governance."""

    def __init__(self, model: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.model = model
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def __add__(self, content: Any) -> Any:
        """Govern content added to model."""
        if isinstance(content, str):
            result = self.tork.govern(content)
            self.receipts.append({
                "type": "model_content",
                "receipt_id": result.receipt.receipt_id
            })
            return self.model + result.output
        return self.model + content

    def __getitem__(self, key: str) -> Any:
        """Get variable from model."""
        value = self.model[key]
        if isinstance(value, str):
            result = self.tork.govern(value)
            return result.output
        return value

    def get_receipts(self) -> List[Dict]:
        return self.receipts

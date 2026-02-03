"""
Stanford DSPy adapter for Tork Governance.

Provides module wrappers and signature governance for DSPy programmatic prompting.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkDSPyModule:
    """
    Wrapper for DSPy modules with governance.

    Example:
        >>> from tork_governance.adapters.dspy import TorkDSPyModule
        >>> import dspy
        >>>
        >>> class MyModule(dspy.Module):
        >>>     def forward(self, question):
        >>>         return self.predict(question=question)
        >>>
        >>> module = MyModule()
        >>> governed_module = TorkDSPyModule(module)
        >>> result = governed_module.forward(question="User data for john@example.com")
    """

    def __init__(self, module: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.module = module
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self.govern(text)

    def forward(self, **kwargs) -> Any:
        """Execute module with governed inputs and outputs."""
        # Govern inputs
        governed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed_kwargs[key] = result.output
                self.receipts.append({
                    "type": "module_input",
                    "field": key,
                    "receipt_id": result.receipt.receipt_id,
                    "action": result.action.value
                })
            else:
                governed_kwargs[key] = value

        # Execute module
        output = self.module.forward(**governed_kwargs)

        # Govern output fields
        if hasattr(output, '__dict__'):
            for field, value in vars(output).items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    setattr(output, field, result.output)
                    self.receipts.append({
                        "type": "module_output",
                        "field": field,
                        "receipt_id": result.receipt.receipt_id
                    })

        return output

    def __call__(self, **kwargs) -> Any:
        """Allow module-style calling."""
        return self.forward(**kwargs)

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkDSPySignature:
    """
    Governed DSPy signature wrapper.

    Example:
        >>> from tork_governance.adapters.dspy import TorkDSPySignature
        >>>
        >>> sig = TorkDSPySignature("question -> answer")
        >>> governed_input = sig.govern_input(question="email: test@example.com")
    """

    def __init__(self, signature: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.signature = signature
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_input(self, **kwargs) -> Dict[str, Any]:
        """Govern signature input fields."""
        governed = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": "signature_input",
                    "field": key,
                    "receipt_id": result.receipt.receipt_id
                })
            else:
                governed[key] = value
        return governed

    def govern_output(self, output: Any) -> Any:
        """Govern signature output fields."""
        if hasattr(output, '__dict__'):
            for field, value in vars(output).items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    setattr(output, field, result.output)
        return output

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_predict(tork: Optional[Tork] = None):
    """
    Decorator for DSPy predict methods.

    Example:
        >>> @governed_predict()
        >>> def my_predictor(question: str) -> str:
        >>>     return dspy.Predict("question -> answer")(question=question)
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    governed_kwargs[key] = result.output
                    receipts.append({
                        "type": "predict_input",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute
            output = func(*args, **governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = _tork.govern(output)
                receipts.append({
                    "type": "predict_output",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            return output

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


class TorkDSPyOptimizer:
    """Wrapper for DSPy optimizers with governance."""

    def __init__(self, optimizer: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.optimizer = optimizer
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def compile(self, module: Any, trainset: List[Any]) -> Any:
        """Compile with governed training data."""
        governed_trainset = []
        for example in trainset:
            governed_example = {}
            for key, value in vars(example).items() if hasattr(example, '__dict__') else example.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_example[key] = result.output
                else:
                    governed_example[key] = value
            governed_trainset.append(governed_example)

        return self.optimizer.compile(module, trainset=governed_trainset)

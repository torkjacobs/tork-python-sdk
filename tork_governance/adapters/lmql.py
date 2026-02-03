"""
LMQL adapter for Tork Governance.

Provides query wrappers and runtime governance for LMQL query language.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkLMQLQuery:
    """
    Wrapper for LMQL queries with governance.

    Example:
        >>> from tork_governance.adapters.lmql import TorkLMQLQuery
        >>> import lmql
        >>>
        >>> @lmql.query
        >>> def my_query(user_input):
        >>>     '''lmql
        >>>     "Process: {user_input}"
        >>>     "[RESPONSE]"
        >>>     '''
        >>>
        >>> governed_query = TorkLMQLQuery(my_query)
        >>> result = governed_query(user_input="test@email.com")
    """

    def __init__(self, query: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.query = query
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_query(self, text: str) -> str:
        """Govern query text - standalone method."""
        return self.govern(text)

    def __call__(self, **kwargs) -> Any:
        """Execute query with governed inputs and outputs."""
        # Govern input kwargs
        governed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed_kwargs[key] = result.output
                self.receipts.append({
                    "type": "query_input",
                    "variable": key,
                    "receipt_id": result.receipt.receipt_id,
                    "action": result.action.value
                })
            else:
                governed_kwargs[key] = value

        # Execute query
        output = self.query(**governed_kwargs)

        # Govern output
        governed_output = self._govern_output(output)
        return governed_output

    async def __acall__(self, **kwargs) -> Any:
        """Async query execution."""
        governed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed_kwargs[key] = result.output

        output = await self.query(**governed_kwargs)
        return self._govern_output(output)

    def _govern_output(self, output: Any) -> Any:
        """Govern query output."""
        if isinstance(output, str):
            result = self.tork.govern(output)
            self.receipts.append({
                "type": "query_output",
                "receipt_id": result.receipt.receipt_id
            })
            return result.output
        elif isinstance(output, dict):
            governed = {}
            for key, value in output.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed[key] = result.output
                    self.receipts.append({
                        "type": "query_output",
                        "variable": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed[key] = value
            return governed
        elif hasattr(output, '__dict__'):
            for field, value in vars(output).items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    setattr(output, field, result.output)
            return output
        return output

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkLMQLRuntime:
    """
    LMQL runtime with governance.

    Example:
        >>> from tork_governance.adapters.lmql import TorkLMQLRuntime
        >>>
        >>> runtime = TorkLMQLRuntime()
        >>> result = runtime.run(query_string, variables={"input": "test@email.com"})
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def run(self, query: str, variables: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """Run LMQL query with governance."""
        try:
            import lmql
        except ImportError:
            raise ImportError("lmql package required: pip install lmql")

        # Govern variables
        governed_variables = {}
        if variables:
            for key, value in variables.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_variables[key] = result.output
                    self.receipts.append({
                        "type": "runtime_variable",
                        "variable": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_variables[key] = value

        # Execute
        output = lmql.run(query, **governed_variables, **kwargs)

        # Govern output
        if isinstance(output, str):
            result = self.tork.govern(output)
            self.receipts.append({
                "type": "runtime_output",
                "receipt_id": result.receipt.receipt_id
            })
            return result.output

        return output

    async def arun(self, query: str, variables: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """Async run LMQL query."""
        try:
            import lmql
        except ImportError:
            raise ImportError("lmql package required: pip install lmql")

        governed_variables = {}
        if variables:
            for key, value in variables.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_variables[key] = result.output

        output = await lmql.run(query, **governed_variables, **kwargs)

        if isinstance(output, str):
            result = self.tork.govern(output)
            return result.output

        return output

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_query(tork: Optional[Tork] = None):
    """
    Decorator for governed LMQL queries.

    Example:
        >>> @governed_query()
        >>> @lmql.query
        >>> def my_query(text):
        >>>     '''lmql
        >>>     "Input: {text}"
        >>>     "[OUTPUT]"
        >>>     '''
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(**kwargs):
            # Govern inputs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    governed_kwargs[key] = result.output
                    receipts.append({
                        "type": "decorated_query_input",
                        "variable": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute
            output = func(**governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = _tork.govern(output)
                receipts.append({
                    "type": "decorated_query_output",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            return output

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator

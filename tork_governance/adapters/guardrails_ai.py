"""
Guardrails AI adapter for Tork Governance.

Integrates Tork governance with Guardrails AI validators and guards.
This allows using Tork PII detection alongside Guardrails validation.

Example:
    from guardrails import Guard
    from tork_governance.adapters.guardrails_ai import TorkValidator, TorkGuard

    # Use as a validator
    guard = Guard().use(TorkValidator())
    result = guard.validate("My SSN is 123-45-6789")

    # Use as a wrapped guard
    tork_guard = TorkGuard(guard)
    result = tork_guard.validate("My email is test@example.com")
"""

from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkValidator:
    """
    Guardrails AI validator that uses Tork for PII detection.

    Can be used with Guard().use() to add PII governance to any guard.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        on_fail: str = "fix",  # "fix", "reask", "exception", "noop"
        redact: bool = True,
    ):
        self.tork = Tork(api_key=api_key)
        self.on_fail = on_fail
        self.redact = redact

    def validate(self, value: Any, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate input using Tork governance."""
        if not isinstance(value, str):
            value = str(value)

        result = self.tork.govern(value)

        if result.action == GovernanceAction.ALLOW:
            return {
                "outcome": "pass",
                "value": value,
                "metadata": {
                    "tork_receipt_id": result.receipt.receipt_id if result.receipt else None,
                    "pii_found": [],
                }
            }

        if self.on_fail == "fix" and self.redact:
            return {
                "outcome": "pass",
                "value": result.output,
                "metadata": {
                    "tork_receipt_id": result.receipt.receipt_id if result.receipt else None,
                    "pii_found": [m.type.value for m in result.pii.matches],
                    "original_redacted": True,
                }
            }
        elif self.on_fail == "exception":
            raise ValueError(f"PII detected: {[m.type.value for m in result.pii.matches]}")
        elif self.on_fail == "reask":
            return {
                "outcome": "fail",
                "error_message": f"Please remove PII from input: {[m.type.value for m in result.pii.matches]}",
                "fix_value": result.output if self.redact else None,
            }
        else:  # noop
            return {
                "outcome": "pass",
                "value": value,
                "metadata": {"pii_detected": True}
            }

    def __call__(self, value: Any, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Allow using validator as callable."""
        return self.validate(value, metadata)


class TorkGuard:
    """
    Wrapper around Guardrails Guard that adds Tork governance.

    Governs both input and output of the guard.
    """

    def __init__(
        self,
        guard: Any = None,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.guard = guard
        self.tork = Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._last_input_result: Optional[GovernanceResult] = None
        self._last_output_result: Optional[GovernanceResult] = None

    def validate(self, llm_output: str, **kwargs) -> Any:
        """Validate with governance applied."""
        # Govern input
        if self.govern_input:
            self._last_input_result = self.tork.govern(llm_output)
            llm_output = self._last_input_result.output

        # Run guard validation
        if self.guard:
            result = self.guard.validate(llm_output, **kwargs)
        else:
            result = llm_output

        # Govern output
        if self.govern_output and isinstance(result, str):
            self._last_output_result = self.tork.govern(result)
            result = self._last_output_result.output

        return result

    def __call__(self, llm_output: str, **kwargs) -> Any:
        """Allow using guard as callable."""
        return self.validate(llm_output, **kwargs)

    @property
    def last_receipt_id(self) -> Optional[str]:
        """Get the last receipt ID from governance."""
        if self._last_output_result and self._last_output_result.receipt:
            return self._last_output_result.receipt.receipt_id
        if self._last_input_result and self._last_input_result.receipt:
            return self._last_input_result.receipt.receipt_id
        return None


class TorkRail:
    """
    Custom Rail specification that includes Tork governance.

    Can be used in RAIL XML specifications.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.tork = Tork(api_key=api_key)

    def to_rail_spec(self) -> str:
        """Generate RAIL XML for Tork validator."""
        return '''
<rail version="0.1">
<output>
    <string name="response"
            validators="tork-pii-governance"
            on-fail-tork-pii-governance="fix"/>
</output>
</rail>
'''

    def register_validator(self, guard: Any) -> Any:
        """Register Tork validator with a guard."""
        guard.use(TorkValidator(api_key=self.tork.api_key))
        return guard


def with_tork_governance(
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """
    Decorator to add Tork governance to Guardrails guard functions.

    Example:
        @with_tork_governance()
        def my_guard_function(text: str) -> str:
            guard = Guard()
            return guard.validate(text)
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string arguments
            if govern_input:
                args = tuple(
                    tork.govern(arg).output if isinstance(arg, str) else arg
                    for arg in args
                )
                kwargs = {
                    k: tork.govern(v).output if isinstance(v, str) else v
                    for k, v in kwargs.items()
                }

            result = func(*args, **kwargs)

            # Govern output
            if govern_output and isinstance(result, str):
                result = tork.govern(result).output

            return result

        return wrapper
    return decorator

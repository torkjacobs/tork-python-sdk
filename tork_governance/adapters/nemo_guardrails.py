"""
Tork Governance adapter for NVIDIA NeMo Guardrails.

Integrates Tork's PII detection and policy enforcement with
NeMo Guardrails for comprehensive AI safety.

Usage:
    from tork_governance.adapters.nemo_guardrails import (
        TorkNeMoRails,
        tork_input_rail,
        tork_output_rail
    )

    # Add Tork as a rail in your NeMo config
    rails = TorkNeMoRails(config, tork=tork)
    response = await rails.generate(messages=[...])
"""

from typing import Any, Dict, List, Optional, Callable
from functools import wraps


class TorkNeMoRails:
    """
    Governed NeMo Guardrails wrapper.
    Adds Tork governance as input/output rails.
    """

    def __init__(
        self,
        config: Any = None,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        block_on_pii: bool = False
    ):
        self.config = config
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.block_on_pii = block_on_pii
        self._rails = None

    def _get_rails(self):
        """Lazy initialize NeMo Guardrails."""
        if self._rails is None:
            try:
                from nemoguardrails import RailsConfig, LLMRails
                if self.config is None:
                    self.config = RailsConfig.from_path("config")
                self._rails = LLMRails(self.config)
            except ImportError:
                raise ImportError(
                    "nemoguardrails is required. Install with: "
                    "pip install nemoguardrails"
                )
        return self._rails

    async def generate(
        self,
        messages: List[Dict[str, str]] = None,
        prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate with Tork governance applied."""
        rails = self._get_rails()

        # Govern input messages
        governed_messages = messages
        receipts = []

        if self.govern_input and messages:
            governed_messages = []
            for msg in messages:
                if msg.get("role") == "user" and msg.get("content"):
                    result = self.tork.govern(msg["content"])
                    receipts.append(result.receipt)

                    if self.block_on_pii and result.action == "block":
                        return {
                            "role": "assistant",
                            "content": "I cannot process this request due to sensitive information.",
                            "_tork_blocked": True,
                            "_tork_receipts": receipts
                        }

                    governed_messages.append({
                        **msg,
                        "content": result.output if result.action in ('redact', 'REDACT') else msg["content"]
                    })
                else:
                    governed_messages.append(msg)

        # Govern prompt if provided
        governed_prompt = prompt
        if self.govern_input and prompt:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            governed_prompt = result.output if result.action in ('redact', 'REDACT') else prompt

        # Generate response
        if governed_messages:
            response = await rails.generate_async(messages=governed_messages, **kwargs)
        else:
            response = await rails.generate_async(prompt=governed_prompt, **kwargs)

        # Govern output
        if self.govern_output:
            content = response.get("content", "")
            if content:
                result = self.tork.govern(content)
                response["content"] = result.output if result.action in ('redact', 'REDACT') else content
                response["_tork_output_governed"] = result.action in ('redact', 'REDACT')

        response["_tork_receipts"] = receipts
        return response

    def generate_sync(
        self,
        messages: List[Dict[str, str]] = None,
        prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous generate with governance."""
        import asyncio
        return asyncio.run(self.generate(messages, prompt, **kwargs))


def tork_input_rail(tork: Any, block_on_pii: bool = False):
    """
    Create a Tork input rail function for NeMo Guardrails.

    Usage in colang:
        define flow tork_pii_check
            $result = execute tork_input_rail(user_message=$user_message)
    """
    async def rail_fn(user_message: str) -> Dict[str, Any]:
        result = tork.govern(user_message)

        if block_on_pii and result.action == "block":
            return {
                "allowed": False,
                "message": "Message blocked due to sensitive information.",
                "receipt": result.receipt
            }

        return {
            "allowed": True,
            "content": result.output if result.action in ('redact', 'REDACT') else user_message,
            "redacted": result.action in ('redact', 'REDACT'),
            "receipt": result.receipt
        }

    return rail_fn


def tork_output_rail(tork: Any):
    """
    Create a Tork output rail function for NeMo Guardrails.

    Usage in colang:
        define flow tork_output_check
            $result = execute tork_output_rail(bot_message=$bot_message)
    """
    async def rail_fn(bot_message: str) -> Dict[str, Any]:
        result = tork.govern(bot_message)

        return {
            "content": result.output if result.action in ('redact', 'REDACT') else bot_message,
            "redacted": result.action in ('redact', 'REDACT'),
            "receipt": result.receipt
        }

    return rail_fn


class TorkNeMoAction:
    """
    Tork action for NeMo Guardrails action server.
    Register this as an action in your NeMo config.
    """

    def __init__(self, tork: Any):
        self.tork = tork

    async def govern_input(self, text: str) -> Dict[str, Any]:
        """Action to govern input text."""
        result = self.tork.govern(text)
        return {
            "governed_text": result.output if result.action in ('redact', 'REDACT') else text,
            "action": result.action,
            "receipt": result.receipt
        }

    async def govern_output(self, text: str) -> Dict[str, Any]:
        """Action to govern output text."""
        result = self.tork.govern(text)
        return {
            "governed_text": result.output if result.action in ('redact', 'REDACT') else text,
            "action": result.action,
            "receipt": result.receipt
        }

    async def check_pii(self, text: str) -> Dict[str, Any]:
        """Action to check for PII without modifying."""
        result = self.tork.govern(text)
        return {
            "has_pii": result.action in ('redact', 'REDACT', 'block'),
            "pii_types": result.metadata.get("pii_types", []) if hasattr(result, 'metadata') else [],
            "receipt": result.receipt
        }


def create_tork_rails_config(
    tork: Any,
    base_config: Optional[Dict] = None,
    govern_input: bool = True,
    govern_output: bool = True
) -> Dict:
    """
    Create a NeMo Guardrails config with Tork rails included.

    Returns a config dict that can be used with RailsConfig.
    """
    config = base_config or {}

    # Add Tork actions
    if "actions" not in config:
        config["actions"] = []

    tork_action = TorkNeMoAction(tork)
    config["actions"].extend([
        {"name": "tork_govern_input", "fn": tork_action.govern_input},
        {"name": "tork_govern_output", "fn": tork_action.govern_output},
        {"name": "tork_check_pii", "fn": tork_action.check_pii},
    ])

    return config


def register_tork_actions(rails: Any, tork: Any) -> None:
    """
    Register Tork governance actions with an existing LLMRails instance.

    Usage:
        from nemoguardrails import LLMRails
        rails = LLMRails(config)
        register_tork_actions(rails, tork)
    """
    action = TorkNeMoAction(tork)

    rails.register_action(action.govern_input, "tork_govern_input")
    rails.register_action(action.govern_output, "tork_govern_output")
    rails.register_action(action.check_pii, "tork_check_pii")


# Colang template for Tork integration
TORK_COLANG_TEMPLATE = '''
# Tork Governance Rails

define user express sensitive info
    "my ssn is"
    "my social security"
    "my credit card"
    "my password is"

define flow tork input governance
    user ...
    $result = execute tork_govern_input(text=$user_message)
    if $result.action == "block"
        bot inform cannot process sensitive info
        stop

define flow tork output governance
    bot ...
    $result = execute tork_govern_output(text=$bot_message)

define bot inform cannot process sensitive info
    "I cannot process requests containing sensitive personal information. Please remove any SSNs, credit cards, or passwords and try again."
'''

"""
LangChain Integration for Tork Governance

Provides callback handlers and chain wrappers for LangChain pipelines.
"""

from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


class TorkCallbackHandler:
    """
    LangChain callback handler that applies Tork governance to LLM calls.

    Example:
        >>> from tork_governance.adapters.langchain import TorkCallbackHandler
        >>> from langchain_openai import ChatOpenAI
        >>>
        >>> handler = TorkCallbackHandler()
        >>> llm = ChatOpenAI(callbacks=[handler])
        >>> response = llm.invoke("Tell me about AI safety")
        >>> print(handler.receipts)  # Access compliance receipts
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        block_on_pii: bool = False
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.block_on_pii = block_on_pii
        self.receipts: List[Dict] = []

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts processing. Validates input prompts."""
        for i, prompt in enumerate(prompts):
            result = self.tork.govern(prompt)
            self.receipts.append({
                'type': 'input',
                'receipt': result.receipt,
                'action': result.action.value
            })

            if self.block_on_pii and result.action == GovernanceAction.DENY:
                raise ValueError(
                    f"Input blocked by Tork governance policy. "
                    f"Receipt: {result.receipt.receipt_id}"
                )

            # Modify prompt in place if redaction occurred
            if result.action == GovernanceAction.REDACT and result.pii.has_pii:
                prompts[i] = result.output

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes. Validates output."""
        try:
            for generation in response.generations:
                for gen in generation:
                    result = self.tork.govern(gen.text)
                    self.receipts.append({
                        'type': 'output',
                        'receipt': result.receipt,
                        'action': result.action.value
                    })

                    # Modify output in place if redaction occurred
                    if result.action == GovernanceAction.REDACT and result.pii.has_pii:
                        gen.text = result.output
        except AttributeError:
            pass  # Response format not as expected, skip

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain starts. Can validate chain inputs."""
        pass

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when chain ends. Can validate chain outputs."""
        pass

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Called when a tool is invoked. Validates tool inputs."""
        result = self.tork.govern(input_str)
        self.receipts.append({
            'type': 'tool_input',
            'receipt': result.receipt,
            'action': result.action.value
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes. Validates tool outputs."""
        result = self.tork.govern(output)
        self.receipts.append({
            'type': 'tool_output',
            'receipt': result.receipt,
            'action': result.action.value
        })

    def clear_receipts(self) -> None:
        """Clear accumulated receipts."""
        self.receipts = []


class TorkGovernedChain:
    """
    Wrapper for LangChain chains that applies governance to inputs/outputs.

    Example:
        >>> from tork_governance.adapters.langchain import TorkGovernedChain
        >>> from langchain_openai import ChatOpenAI
        >>> from langchain.prompts import ChatPromptTemplate
        >>>
        >>> prompt = ChatPromptTemplate.from_template("Answer: {question}")
        >>> chain = prompt | ChatOpenAI()
        >>> governed = TorkGovernedChain(chain)
        >>> result = governed.invoke({"question": "What is AI?"})
    """

    def __init__(
        self,
        chain: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0"
    ):
        self.chain = chain
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.last_result: Optional[GovernanceResult] = None

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        result = self.tork.govern(text)
        self.last_result = result
        return result.output

    def govern_output(self, text: str) -> str:
        """Govern output text - standalone method."""
        result = self.tork.govern(text)
        self.last_result = result
        return result.output

    def govern(self, text: str) -> str:
        """Govern text - alias for govern_input."""
        return self.govern_input(text)

    def invoke(self, inputs: Union[Dict, str], **kwargs) -> Any:
        """Invoke the chain with governance."""
        # Govern input
        if isinstance(inputs, str):
            input_result = self.tork.govern(inputs)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked: {input_result.receipt.receipt_id}")
            governed_input = input_result.output
        else:
            # Govern each string value in the dict
            governed_input = {}
            for key, value in inputs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Input blocked: {result.receipt.receipt_id}")
                    governed_input[key] = result.output
                else:
                    governed_input[key] = value

        # Invoke chain
        output = self.chain.invoke(governed_input, **kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.last_result = output_result
            return output_result.output
        elif hasattr(output, 'content'):
            output_result = self.tork.govern(output.content)
            self.last_result = output_result
            output.content = output_result.output
            return output
        else:
            return output

    async def ainvoke(self, inputs: Union[Dict, str], **kwargs) -> Any:
        """Async invoke the chain with governance."""
        # For async, we use the sync governance (CPU-bound, fast)
        return self.invoke(inputs, **kwargs)


def create_governed_chain(
    chain: Any,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0"
) -> TorkGovernedChain:
    """
    Factory function to create a governed chain wrapper.

    Args:
        chain: The LangChain chain/runnable to wrap
        api_key: Optional Tork API key
        policy_version: Policy version string

    Returns:
        TorkGovernedChain wrapper
    """
    return TorkGovernedChain(
        chain=chain,
        api_key=api_key,
        policy_version=policy_version
    )

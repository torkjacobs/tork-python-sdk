"""
vLLM adapter for Tork Governance.

Provides governance integration for vLLM, a high-throughput LLM serving engine.
Supports batch generation, streaming, and async operations.

Example:
    from vllm import LLM
    from tork_governance.adapters.vllm import TorkVLLMEngine, govern_generate

    # Use governed engine
    engine = TorkVLLMEngine(model="meta-llama/Llama-2-7b-hf")
    outputs = engine.generate(["My SSN is 123-45-6789"])

    # Use convenience function
    outputs = govern_generate(llm, ["My email is test@example.com"])
"""

from typing import Any, Callable, Dict, Generator, List, Optional, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkSamplingParams:
    """
    Wrapper for vLLM SamplingParams with governance metadata.

    Extends sampling parameters with governance-specific options.
    """

    def __init__(
        self,
        temperature: float = 1.0,
        top_p: float = 1.0,
        top_k: int = -1,
        max_tokens: int = 16,
        stop: Optional[List[str]] = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        best_of: int = 1,
        use_beam_search: bool = False,
        # Governance options
        govern_output: bool = True,
        redact_pii: bool = True,
    ):
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.stop = stop
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.best_of = best_of
        self.use_beam_search = use_beam_search
        self.govern_output = govern_output
        self.redact_pii = redact_pii

    def to_vllm_params(self) -> Any:
        """Convert to vLLM SamplingParams."""
        try:
            from vllm import SamplingParams
        except ImportError:
            raise ImportError("vllm is required: pip install vllm")

        return SamplingParams(
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            max_tokens=self.max_tokens,
            stop=self.stop,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            best_of=self.best_of,
            use_beam_search=self.use_beam_search,
        )


class TorkVLLMEngine:
    """
    Governed vLLM engine wrapper.

    Wraps vLLM's LLM class with automatic governance applied to
    prompts and generated outputs.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
        **vllm_kwargs
    ):
        self.model = model
        self.tork = Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.vllm_kwargs = vllm_kwargs
        self._llm: Any = None
        self._receipts: List[str] = []

    def _get_llm(self) -> Any:
        """Get or create the vLLM instance."""
        if self._llm is None:
            try:
                from vllm import LLM
            except ImportError:
                raise ImportError("vllm is required: pip install vllm")

            self._llm = LLM(model=self.model, **self.vllm_kwargs)
        return self._llm

    def generate(
        self,
        prompts: Union[str, List[str]],
        sampling_params: Optional[Union[TorkSamplingParams, Any]] = None,
        **kwargs
    ) -> List[Any]:
        """
        Generate text with governance applied.

        Args:
            prompts: Single prompt or list of prompts
            sampling_params: Sampling parameters (TorkSamplingParams or vLLM SamplingParams)
            **kwargs: Additional arguments passed to vLLM

        Returns:
            List of RequestOutput objects with governed text
        """
        llm = self._get_llm()

        # Normalize prompts to list
        if isinstance(prompts, str):
            prompts = [prompts]

        # Govern input prompts
        if self.govern_input:
            governed_prompts = []
            for prompt in prompts:
                result = self.tork.govern(prompt)
                governed_prompts.append(result.output)
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
            prompts = governed_prompts

        # Handle sampling params
        vllm_params = None
        govern_output = self.govern_output

        if isinstance(sampling_params, TorkSamplingParams):
            vllm_params = sampling_params.to_vllm_params()
            govern_output = sampling_params.govern_output
        elif sampling_params is not None:
            vllm_params = sampling_params

        # Generate
        if vllm_params:
            outputs = llm.generate(prompts, vllm_params, **kwargs)
        else:
            outputs = llm.generate(prompts, **kwargs)

        # Govern outputs
        if govern_output:
            outputs = self._govern_outputs(outputs)

        return outputs

    def _govern_outputs(self, outputs: List[Any]) -> List[Any]:
        """Govern the generated outputs."""
        for output in outputs:
            for completion in output.outputs:
                if hasattr(completion, 'text') and completion.text:
                    result = self.tork.govern(completion.text)
                    completion.text = result.output
                    if result.receipt:
                        self._receipts.append(result.receipt.receipt_id)
        return outputs

    def batch_generate(
        self,
        prompt_batches: List[List[str]],
        sampling_params: Optional[TorkSamplingParams] = None,
        **kwargs
    ) -> List[List[Any]]:
        """
        Generate text for multiple batches with governance.

        Args:
            prompt_batches: List of prompt batches
            sampling_params: Sampling parameters
            **kwargs: Additional arguments

        Returns:
            List of output batches
        """
        results = []
        for batch in prompt_batches:
            batch_outputs = self.generate(batch, sampling_params, **kwargs)
            results.append(batch_outputs)
        return results

    def encode(self, prompts: Union[str, List[str]]) -> Any:
        """Encode prompts (passthrough to vLLM)."""
        return self._get_llm().encode(prompts)

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


class AsyncTorkVLLMEngine:
    """
    Async governed vLLM engine wrapper.

    Provides async methods for vLLM generation with governance.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
        **vllm_kwargs
    ):
        self.model = model
        self.tork = Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.vllm_kwargs = vllm_kwargs
        self._engine: Any = None
        self._receipts: List[str] = []

    async def _get_engine(self) -> Any:
        """Get or create the async vLLM engine."""
        if self._engine is None:
            try:
                from vllm import AsyncLLMEngine
                from vllm.engine.arg_utils import AsyncEngineArgs
            except ImportError:
                raise ImportError("vllm is required: pip install vllm")

            engine_args = AsyncEngineArgs(model=self.model, **self.vllm_kwargs)
            self._engine = AsyncLLMEngine.from_engine_args(engine_args)
        return self._engine

    async def generate(
        self,
        prompt: str,
        sampling_params: Optional[TorkSamplingParams] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Async generate with governance.

        Args:
            prompt: The prompt text
            sampling_params: Sampling parameters
            request_id: Optional request ID
            **kwargs: Additional arguments

        Returns:
            Generated output with governance applied
        """
        engine = await self._get_engine()

        # Govern input
        if self.govern_input:
            result = self.tork.govern(prompt)
            prompt = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

        # Handle sampling params
        vllm_params = None
        govern_output = self.govern_output

        if isinstance(sampling_params, TorkSamplingParams):
            vllm_params = sampling_params.to_vllm_params()
            govern_output = sampling_params.govern_output
        elif sampling_params is not None:
            vllm_params = sampling_params

        # Generate
        import uuid
        request_id = request_id or str(uuid.uuid4())

        final_output = None
        async for output in engine.generate(prompt, vllm_params, request_id):
            final_output = output

        # Govern output
        if govern_output and final_output:
            for completion in final_output.outputs:
                if hasattr(completion, 'text') and completion.text:
                    result = self.tork.govern(completion.text)
                    completion.text = result.output
                    if result.receipt:
                        self._receipts.append(result.receipt.receipt_id)

        return final_output

    async def stream_generate(
        self,
        prompt: str,
        sampling_params: Optional[TorkSamplingParams] = None,
        request_id: Optional[str] = None,
    ) -> Generator[Any, None, None]:
        """
        Stream generation with governance on final output.

        Yields intermediate results and governs the final output.
        """
        engine = await self._get_engine()

        # Govern input
        if self.govern_input:
            result = self.tork.govern(prompt)
            prompt = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

        vllm_params = None
        if isinstance(sampling_params, TorkSamplingParams):
            vllm_params = sampling_params.to_vllm_params()
        elif sampling_params is not None:
            vllm_params = sampling_params

        import uuid
        request_id = request_id or str(uuid.uuid4())

        full_text = ""
        async for output in engine.generate(prompt, vllm_params, request_id):
            if output.outputs:
                full_text = output.outputs[0].text
            yield output

        # Govern accumulated output
        if self.govern_output and full_text:
            result = self.tork.govern(full_text)
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


def govern_generate(
    llm: Any,
    prompts: Union[str, List[str]],
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
    sampling_params: Any = None,
    **kwargs
) -> List[Any]:
    """
    Governed vLLM generate call.

    Convenience function that wraps an existing vLLM LLM instance
    with governance.

    Example:
        from vllm import LLM
        llm = LLM(model="meta-llama/Llama-2-7b-hf")
        outputs = govern_generate(llm, ["My SSN is 123-45-6789"])
    """
    tork = Tork(api_key=api_key)

    # Normalize prompts
    if isinstance(prompts, str):
        prompts = [prompts]

    # Govern inputs
    if govern_input:
        prompts = [tork.govern(p).output for p in prompts]

    # Generate
    outputs = llm.generate(prompts, sampling_params, **kwargs)

    # Govern outputs
    if govern_output:
        for output in outputs:
            for completion in output.outputs:
                if hasattr(completion, 'text') and completion.text:
                    completion.text = tork.govern(completion.text).output

    return outputs


def vllm_governed(
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """
    Decorator to add Tork governance to vLLM-based functions.

    Example:
        @vllm_governed()
        def my_generate_function(prompts: List[str]) -> List[str]:
            llm = LLM(model="meta-llama/Llama-2-7b-hf")
            outputs = llm.generate(prompts)
            return [o.outputs[0].text for o in outputs]
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string and list arguments
            if govern_input:
                new_args = []
                for arg in args:
                    if isinstance(arg, str):
                        new_args.append(tork.govern(arg).output)
                    elif isinstance(arg, list) and arg and isinstance(arg[0], str):
                        new_args.append([tork.govern(p).output for p in arg])
                    else:
                        new_args.append(arg)
                args = tuple(new_args)

                if "prompts" in kwargs:
                    if isinstance(kwargs["prompts"], str):
                        kwargs["prompts"] = tork.govern(kwargs["prompts"]).output
                    elif isinstance(kwargs["prompts"], list):
                        kwargs["prompts"] = [tork.govern(p).output for p in kwargs["prompts"]]

            result = func(*args, **kwargs)

            # Govern output
            if govern_output:
                if isinstance(result, str):
                    result = tork.govern(result).output
                elif isinstance(result, list) and result and isinstance(result[0], str):
                    result = [tork.govern(r).output for r in result]

            return result

        return wrapper
    return decorator

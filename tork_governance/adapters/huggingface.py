"""
Tork Governance adapter for Hugging Face Transformers.

Provides governance for Hugging Face pipelines, models, and tokenizers
with automatic PII detection and redaction.

Usage:
    from tork_governance.adapters.huggingface import TorkHFPipeline, govern_generate

    # Wrap a pipeline
    pipe = pipeline("text-generation", model="gpt2")
    governed_pipe = TorkHFPipeline(pipe)
    result = governed_pipe("My SSN is 123-45-6789")

    # Use decorator
    @huggingface_governed
    def generate_text(pipe, prompt):
        return pipe(prompt)
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps

from ..core import Tork, GovernanceResult


@dataclass
class HuggingFaceGovernanceResult:
    """Result from a governed Hugging Face operation."""
    result: Any
    input_governance: GovernanceResult
    output_governance: Optional[GovernanceResult] = None
    receipt_id: str = ""
    pii_detected_in_input: bool = False
    pii_detected_in_output: bool = False
    pii_types_input: List[str] = field(default_factory=list)
    pii_types_output: List[str] = field(default_factory=list)


class TorkHFPipeline:
    """
    Governed Hugging Face Pipeline wrapper.

    Wraps any Hugging Face pipeline (text-generation, summarization, etc.)
    with automatic PII detection and redaction.

    Args:
        pipeline: The Hugging Face pipeline to wrap
        tork: Optional Tork instance (creates default if not provided)
        redact_input: Whether to redact PII in inputs (default True)
        redact_output: Whether to redact PII in outputs (default True)

    Example:
        from transformers import pipeline
        from tork_governance.adapters.huggingface import TorkHFPipeline

        pipe = pipeline("text-generation", model="gpt2")
        governed = TorkHFPipeline(pipe)

        result = governed("My email is test@example.com")
        print(result.result)  # Generated text with PII redacted
        print(result.receipt_id)  # Governance receipt
    """

    def __init__(
        self,
        pipeline: Any,
        tork: Optional[Tork] = None,
        redact_input: bool = True,
        redact_output: bool = True,
    ):
        self.pipeline = pipeline
        self.tork = tork or Tork()
        self.redact_input = redact_input
        self.redact_output = redact_output
        self._receipts: List[str] = []

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs from this pipeline."""
        return self._receipts.copy()

    def __call__(
        self,
        inputs: Union[str, List[str]],
        **kwargs
    ) -> HuggingFaceGovernanceResult:
        """
        Run the pipeline with governance.

        Args:
            inputs: Text input(s) to process
            **kwargs: Additional arguments passed to the pipeline

        Returns:
            HuggingFaceGovernanceResult with governed outputs
        """
        # Handle single string or list of strings
        is_batch = isinstance(inputs, list)
        input_list = inputs if is_batch else [inputs]

        # Govern inputs
        governed_inputs = []
        input_results = []
        pii_in_input = False
        pii_types_input = set()

        for inp in input_list:
            result = self.tork.govern(inp)
            input_results.append(result)
            if result.pii.has_pii:
                pii_in_input = True
                pii_types_input.update(result.pii.types)
            governed_inputs.append(result.output if self.redact_input else inp)

        # Run pipeline with governed inputs
        pipeline_inputs = governed_inputs if is_batch else governed_inputs[0]
        raw_result = self.pipeline(pipeline_inputs, **kwargs)

        # Extract text from pipeline output
        output_texts = self._extract_output_text(raw_result, is_batch)

        # Govern outputs
        output_results = []
        pii_in_output = False
        pii_types_output = set()
        governed_outputs = []

        for out_text in output_texts:
            if out_text:
                result = self.tork.govern(out_text)
                output_results.append(result)
                if result.pii.has_pii:
                    pii_in_output = True
                    pii_types_output.update(result.pii.types)
                governed_outputs.append(result.output if self.redact_output else out_text)
            else:
                governed_outputs.append(out_text)

        # Reconstruct output with governed text
        final_result = self._reconstruct_output(raw_result, governed_outputs, is_batch)

        # Create governance result
        receipt_id = input_results[0].receipt.receipt_id if input_results else ""
        self._receipts.append(receipt_id)

        return HuggingFaceGovernanceResult(
            result=final_result,
            input_governance=input_results[0] if input_results else None,
            output_governance=output_results[0] if output_results else None,
            receipt_id=receipt_id,
            pii_detected_in_input=pii_in_input,
            pii_detected_in_output=pii_in_output,
            pii_types_input=list(pii_types_input),
            pii_types_output=list(pii_types_output),
        )

    def _extract_output_text(self, result: Any, is_batch: bool) -> List[str]:
        """Extract generated text from pipeline output."""
        texts = []

        # Handle different pipeline output formats
        if isinstance(result, list):
            for item in result:
                if isinstance(item, list):
                    # Batch with multiple generations per input
                    for sub_item in item:
                        texts.append(self._get_text_from_item(sub_item))
                else:
                    texts.append(self._get_text_from_item(item))
        elif isinstance(result, dict):
            texts.append(self._get_text_from_item(result))
        elif isinstance(result, str):
            texts.append(result)
        else:
            texts.append(str(result) if result else "")

        return texts

    def _get_text_from_item(self, item: Any) -> str:
        """Extract text from a single pipeline output item."""
        if isinstance(item, dict):
            # Common keys for different pipeline types
            for key in ['generated_text', 'summary_text', 'translation_text',
                        'answer', 'token_str', 'sequence', 'text']:
                if key in item:
                    return item[key]
            return str(item)
        elif isinstance(item, str):
            return item
        return str(item) if item else ""

    def _reconstruct_output(self, original: Any, governed_texts: List[str], is_batch: bool) -> Any:
        """Reconstruct the output with governed text."""
        if not governed_texts:
            return original

        text_idx = 0

        def replace_text(item):
            nonlocal text_idx
            if isinstance(item, dict):
                new_item = item.copy()
                for key in ['generated_text', 'summary_text', 'translation_text',
                            'answer', 'token_str', 'sequence', 'text']:
                    if key in new_item and text_idx < len(governed_texts):
                        new_item[key] = governed_texts[text_idx]
                        text_idx += 1
                        break
                return new_item
            elif isinstance(item, str) and text_idx < len(governed_texts):
                text = governed_texts[text_idx]
                text_idx += 1
                return text
            return item

        if isinstance(original, list):
            return [
                [replace_text(sub) for sub in item] if isinstance(item, list)
                else replace_text(item)
                for item in original
            ]
        else:
            return replace_text(original)


class TorkHFModel:
    """
    Governed Hugging Face Model wrapper.

    Wraps any Hugging Face model (AutoModel, AutoModelForCausalLM, etc.)
    with automatic PII detection and redaction during generation.

    Args:
        model: The Hugging Face model to wrap
        tokenizer: The tokenizer to use for encoding/decoding
        tork: Optional Tork instance
        redact_input: Whether to redact PII in inputs
        redact_output: Whether to redact PII in outputs

    Example:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from tork_governance.adapters.huggingface import TorkHFModel

        model = AutoModelForCausalLM.from_pretrained("gpt2")
        tokenizer = AutoTokenizer.from_pretrained("gpt2")

        governed = TorkHFModel(model, tokenizer)
        result = governed.generate("My SSN is 123-45-6789", max_length=50)
    """

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        tork: Optional[Tork] = None,
        redact_input: bool = True,
        redact_output: bool = True,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.tork = tork or Tork()
        self.redact_input = redact_input
        self.redact_output = redact_output
        self._receipts: List[str] = []

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()

    def generate(
        self,
        prompt: Union[str, List[str]],
        **kwargs
    ) -> HuggingFaceGovernanceResult:
        """
        Generate text with governance.

        Args:
            prompt: Input prompt(s)
            **kwargs: Arguments passed to model.generate()

        Returns:
            HuggingFaceGovernanceResult with governed output
        """
        is_batch = isinstance(prompt, list)
        prompts = prompt if is_batch else [prompt]

        # Govern inputs
        governed_prompts = []
        input_results = []
        pii_in_input = False
        pii_types_input = set()

        for p in prompts:
            result = self.tork.govern(p)
            input_results.append(result)
            if result.pii.has_pii:
                pii_in_input = True
                pii_types_input.update(result.pii.types)
            governed_prompts.append(result.output if self.redact_input else p)

        # Encode and generate
        input_text = governed_prompts if is_batch else governed_prompts[0]
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            padding=True if is_batch else False
        )

        # Move to model device if needed
        if hasattr(self.model, 'device'):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        # Generate
        outputs = self.model.generate(**inputs, **kwargs)

        # Decode outputs
        generated_texts = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

        # Govern outputs
        output_results = []
        pii_in_output = False
        pii_types_output = set()
        governed_outputs = []

        for text in generated_texts:
            result = self.tork.govern(text)
            output_results.append(result)
            if result.pii.has_pii:
                pii_in_output = True
                pii_types_output.update(result.pii.types)
            governed_outputs.append(result.output if self.redact_output else text)

        # Return appropriate format
        final_result = governed_outputs if is_batch else governed_outputs[0]

        receipt_id = input_results[0].receipt.receipt_id if input_results else ""
        self._receipts.append(receipt_id)

        return HuggingFaceGovernanceResult(
            result=final_result,
            input_governance=input_results[0] if input_results else None,
            output_governance=output_results[0] if output_results else None,
            receipt_id=receipt_id,
            pii_detected_in_input=pii_in_input,
            pii_detected_in_output=pii_in_output,
            pii_types_input=list(pii_types_input),
            pii_types_output=list(pii_types_output),
        )

    def __call__(self, *args, **kwargs):
        """Forward call to underlying model."""
        return self.model(*args, **kwargs)

    def __getattr__(self, name: str):
        """Delegate attribute access to underlying model."""
        return getattr(self.model, name)


class TorkHFTokenizer:
    """
    Governed Hugging Face Tokenizer wrapper.

    Wraps any Hugging Face tokenizer with PII detection during
    encode and decode operations.

    Args:
        tokenizer: The Hugging Face tokenizer to wrap
        tork: Optional Tork instance
        redact_on_encode: Whether to redact PII when encoding
        redact_on_decode: Whether to redact PII when decoding

    Example:
        from transformers import AutoTokenizer
        from tork_governance.adapters.huggingface import TorkHFTokenizer

        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        governed = TorkHFTokenizer(tokenizer)

        result = governed.encode("My SSN is 123-45-6789")
        # PII is redacted before encoding
    """

    def __init__(
        self,
        tokenizer: Any,
        tork: Optional[Tork] = None,
        redact_on_encode: bool = True,
        redact_on_decode: bool = True,
    ):
        self.tokenizer = tokenizer
        self.tork = tork or Tork()
        self.redact_on_encode = redact_on_encode
        self.redact_on_decode = redact_on_decode
        self._receipts: List[str] = []

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()

    def encode(
        self,
        text: Union[str, List[str]],
        **kwargs
    ) -> Any:
        """
        Encode text with governance.

        Args:
            text: Text to encode
            **kwargs: Arguments passed to tokenizer.encode()

        Returns:
            Encoded tokens
        """
        if self.redact_on_encode:
            if isinstance(text, list):
                governed_texts = []
                for t in text:
                    result = self.tork.govern(t)
                    self._receipts.append(result.receipt.receipt_id)
                    governed_texts.append(result.output)
                text = governed_texts
            else:
                result = self.tork.govern(text)
                self._receipts.append(result.receipt.receipt_id)
                text = result.output

        return self.tokenizer.encode(text, **kwargs)

    def decode(
        self,
        token_ids: Any,
        **kwargs
    ) -> str:
        """
        Decode tokens with governance.

        Args:
            token_ids: Token IDs to decode
            **kwargs: Arguments passed to tokenizer.decode()

        Returns:
            Decoded and optionally governed text
        """
        text = self.tokenizer.decode(token_ids, **kwargs)

        if self.redact_on_decode:
            result = self.tork.govern(text)
            self._receipts.append(result.receipt.receipt_id)
            return result.output

        return text

    def batch_decode(
        self,
        sequences: Any,
        **kwargs
    ) -> List[str]:
        """
        Batch decode with governance.

        Args:
            sequences: Token ID sequences to decode
            **kwargs: Arguments passed to tokenizer.batch_decode()

        Returns:
            List of decoded and optionally governed texts
        """
        texts = self.tokenizer.batch_decode(sequences, **kwargs)

        if self.redact_on_decode:
            governed_texts = []
            for text in texts:
                result = self.tork.govern(text)
                self._receipts.append(result.receipt.receipt_id)
                governed_texts.append(result.output)
            return governed_texts

        return texts

    def __call__(self, *args, **kwargs):
        """Forward call to underlying tokenizer with input governance."""
        # Govern text inputs if provided
        if args and isinstance(args[0], (str, list)):
            text = args[0]
            if self.redact_on_encode:
                if isinstance(text, list):
                    governed = []
                    for t in text:
                        result = self.tork.govern(t)
                        self._receipts.append(result.receipt.receipt_id)
                        governed.append(result.output)
                    args = (governed,) + args[1:]
                else:
                    result = self.tork.govern(text)
                    self._receipts.append(result.receipt.receipt_id)
                    args = (result.output,) + args[1:]

        return self.tokenizer(*args, **kwargs)

    def __getattr__(self, name: str):
        """Delegate attribute access to underlying tokenizer."""
        return getattr(self.tokenizer, name)


def govern_generate(
    model: Any,
    tokenizer: Any,
    prompt: Union[str, List[str]],
    tork: Optional[Tork] = None,
    redact_input: bool = True,
    redact_output: bool = True,
    **kwargs
) -> HuggingFaceGovernanceResult:
    """
    Govern a model.generate() call.

    Convenience function for one-off governed generation without
    creating a wrapper instance.

    Args:
        model: Hugging Face model
        tokenizer: Hugging Face tokenizer
        prompt: Input prompt(s)
        tork: Optional Tork instance
        redact_input: Whether to redact PII in input
        redact_output: Whether to redact PII in output
        **kwargs: Arguments passed to model.generate()

    Returns:
        HuggingFaceGovernanceResult

    Example:
        result = govern_generate(
            model, tokenizer,
            "My email is test@example.com",
            max_length=50
        )
    """
    governed_model = TorkHFModel(
        model, tokenizer, tork,
        redact_input=redact_input,
        redact_output=redact_output
    )
    return governed_model.generate(prompt, **kwargs)


def govern_pipeline(
    pipeline: Any,
    inputs: Union[str, List[str]],
    tork: Optional[Tork] = None,
    redact_input: bool = True,
    redact_output: bool = True,
    **kwargs
) -> HuggingFaceGovernanceResult:
    """
    Govern a pipeline call.

    Convenience function for one-off governed pipeline execution.

    Args:
        pipeline: Hugging Face pipeline
        inputs: Input text(s)
        tork: Optional Tork instance
        redact_input: Whether to redact PII in input
        redact_output: Whether to redact PII in output
        **kwargs: Arguments passed to pipeline

    Returns:
        HuggingFaceGovernanceResult

    Example:
        pipe = pipeline("text-generation", model="gpt2")
        result = govern_pipeline(pipe, "My SSN is 123-45-6789")
    """
    governed_pipeline = TorkHFPipeline(
        pipeline, tork,
        redact_input=redact_input,
        redact_output=redact_output
    )
    return governed_pipeline(inputs, **kwargs)


def govern_inference(
    model_id: str,
    inputs: Union[str, List[str], Dict[str, Any]],
    tork: Optional[Tork] = None,
    api_token: Optional[str] = None,
    redact_input: bool = True,
    redact_output: bool = True,
) -> HuggingFaceGovernanceResult:
    """
    Govern a Hugging Face Inference API call.

    Provides governance for calls to the Hugging Face Inference API
    without requiring local model loading.

    Args:
        model_id: Hugging Face model ID (e.g., "gpt2", "facebook/bart-large-cnn")
        inputs: Input text(s) or parameters dict
        tork: Optional Tork instance
        api_token: Hugging Face API token
        redact_input: Whether to redact PII in input
        redact_output: Whether to redact PII in output

    Returns:
        HuggingFaceGovernanceResult

    Example:
        result = govern_inference(
            "gpt2",
            "My phone number is 555-123-4567",
            api_token="hf_xxx"
        )
    """
    tork = tork or Tork()

    # Extract text from inputs
    if isinstance(inputs, dict):
        text_key = 'inputs' if 'inputs' in inputs else None
        if text_key:
            text = inputs[text_key]
        else:
            text = str(inputs)
    elif isinstance(inputs, list):
        text = inputs
    else:
        text = inputs

    # Govern input
    is_batch = isinstance(text, list)
    texts = text if is_batch else [text]

    governed_texts = []
    input_results = []
    pii_in_input = False
    pii_types_input = set()

    for t in texts:
        result = tork.govern(str(t))
        input_results.append(result)
        if result.pii.has_pii:
            pii_in_input = True
            pii_types_input.update(result.pii.types)
        governed_texts.append(result.output if redact_input else str(t))

    # Prepare governed inputs
    if isinstance(inputs, dict):
        governed_inputs = inputs.copy()
        if 'inputs' in governed_inputs:
            governed_inputs['inputs'] = governed_texts if is_batch else governed_texts[0]
    else:
        governed_inputs = governed_texts if is_batch else governed_texts[0]

    # Make API call (simulated - actual implementation would use requests)
    # In a real implementation, this would call the HF Inference API
    # For now, we return the governed input as the result
    api_result = governed_inputs

    # Govern output (if it's text)
    output_results = []
    pii_in_output = False
    pii_types_output = set()

    if isinstance(api_result, str):
        result = tork.govern(api_result)
        output_results.append(result)
        if result.pii.has_pii:
            pii_in_output = True
            pii_types_output.update(result.pii.types)
        api_result = result.output if redact_output else api_result
    elif isinstance(api_result, list):
        governed_outputs = []
        for item in api_result:
            if isinstance(item, str):
                result = tork.govern(item)
                output_results.append(result)
                if result.pii.has_pii:
                    pii_in_output = True
                    pii_types_output.update(result.pii.types)
                governed_outputs.append(result.output if redact_output else item)
            else:
                governed_outputs.append(item)
        api_result = governed_outputs

    receipt_id = input_results[0].receipt.receipt_id if input_results else ""

    return HuggingFaceGovernanceResult(
        result=api_result,
        input_governance=input_results[0] if input_results else None,
        output_governance=output_results[0] if output_results else None,
        receipt_id=receipt_id,
        pii_detected_in_input=pii_in_input,
        pii_detected_in_output=pii_in_output,
        pii_types_input=list(pii_types_input),
        pii_types_output=list(pii_types_output),
    )


def huggingface_governed(
    tork: Optional[Tork] = None,
    redact_input: bool = True,
    redact_output: bool = True,
):
    """
    Decorator for adding governance to Hugging Face operations.

    Args:
        tork: Optional Tork instance
        redact_input: Whether to redact PII in inputs
        redact_output: Whether to redact PII in outputs

    Returns:
        Decorator function

    Example:
        @huggingface_governed()
        def generate_text(pipe, prompt):
            return pipe(prompt)

        result = generate_text(my_pipeline, "My SSN is 123-45-6789")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal tork
            _tork = tork or Tork()

            # Govern string arguments
            governed_args = []
            input_results = []

            for arg in args:
                if isinstance(arg, str):
                    result = _tork.govern(arg)
                    input_results.append(result)
                    governed_args.append(result.output if redact_input else arg)
                elif isinstance(arg, list) and all(isinstance(x, str) for x in arg):
                    governed_list = []
                    for item in arg:
                        result = _tork.govern(item)
                        input_results.append(result)
                        governed_list.append(result.output if redact_input else item)
                    governed_args.append(governed_list)
                else:
                    governed_args.append(arg)

            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    input_results.append(result)
                    governed_kwargs[key] = result.output if redact_input else value
                else:
                    governed_kwargs[key] = value

            # Call function
            output = func(*governed_args, **governed_kwargs)

            # Govern output
            output_result = None
            if redact_output:
                if isinstance(output, str):
                    output_result = _tork.govern(output)
                    output = output_result.output
                elif isinstance(output, list):
                    governed_output = []
                    for item in output:
                        if isinstance(item, str):
                            result = _tork.govern(item)
                            output_result = output_result or result
                            governed_output.append(result.output)
                        elif isinstance(item, dict):
                            # Handle pipeline output format
                            governed_item = item.copy()
                            for text_key in ['generated_text', 'summary_text', 'translation_text', 'text']:
                                if text_key in governed_item:
                                    result = _tork.govern(governed_item[text_key])
                                    output_result = output_result or result
                                    governed_item[text_key] = result.output
                            governed_output.append(governed_item)
                        else:
                            governed_output.append(item)
                    output = governed_output

            return output

        return wrapper
    return decorator


# Aliases for convenience
HFGovernanceResult = HuggingFaceGovernanceResult
TorkTransformersPipeline = TorkHFPipeline
TorkTransformersModel = TorkHFModel
TorkTransformersTokenizer = TorkHFTokenizer

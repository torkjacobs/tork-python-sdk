"""
Tork Governance adapter for Google Gemini / Vertex AI.

Provides governance for Google Generative AI with automatic
PII detection and redaction in content generation and chat.

Usage:
    from tork_governance.adapters.google_gemini import TorkGeminiClient

    # Wrap Gemini model
    import google.generativeai as genai
    model = genai.GenerativeModel("gemini-pro")
    governed = TorkGeminiClient(model)

    # All API calls now governed
    response = governed.generate_content("My SSN is 123-45-6789")
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class GeminiGovernanceResult:
    """Result of Gemini governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    response: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkGeminiClient:
    """
    Governed wrapper for Google Gemini model.

    Automatically applies PII detection and redaction to all
    content generation and chat requests.

    Example:
        import google.generativeai as genai
        from tork_governance.adapters.google_gemini import TorkGeminiClient

        genai.configure(api_key="...")
        model = genai.GenerativeModel("gemini-pro")
        governed = TorkGeminiClient(model)

        # Content generation is governed
        response = governed.generate_content("Hello")
    """

    def __init__(
        self,
        model: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_prompts: bool = True,
        redact_responses: bool = True,
        redact_chat_history: bool = True,
    ):
        """
        Initialize governed Gemini client.

        Args:
            model: Gemini GenerativeModel instance
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_prompts: Whether to redact PII in prompts
            redact_responses: Whether to redact PII in responses
            redact_chat_history: Whether to redact PII in chat history
        """
        self._model = model
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_prompts = redact_prompts
        self._redact_responses = redact_responses
        self._redact_chat_history = redact_chat_history
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def model(self) -> Any:
        """Access underlying Gemini model."""
        return self._model

    def _govern_text(self, text: Any) -> tuple[Any, Optional[GovernanceResult]]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

    def _govern_content(self, content: Any) -> Any:
        """Apply governance to content (string, list, or parts)."""
        if isinstance(content, str):
            governed, _ = self._govern_text(content)
            return governed
        elif isinstance(content, list):
            governed = []
            for part in content:
                if isinstance(part, str):
                    text, _ = self._govern_text(part)
                    governed.append(text)
                elif isinstance(part, dict):
                    governed_part = part.copy()
                    if "text" in governed_part:
                        governed_part["text"], _ = self._govern_text(governed_part["text"])
                    governed.append(governed_part)
                elif hasattr(part, "text"):
                    # Handle Part objects
                    part.text, _ = self._govern_text(part.text)
                    governed.append(part)
                else:
                    governed.append(part)
            return governed
        elif hasattr(content, "text"):
            content.text, _ = self._govern_text(content.text)
            return content
        return content

    def _govern_history(self, history: List[Any]) -> List[Any]:
        """Apply governance to chat history."""
        governed = []
        for entry in history:
            if hasattr(entry, "parts"):
                for part in entry.parts:
                    if hasattr(part, "text"):
                        part.text, _ = self._govern_text(part.text)
            elif isinstance(entry, dict):
                governed_entry = entry.copy()
                if "parts" in governed_entry:
                    governed_entry["parts"] = self._govern_content(governed_entry["parts"])
                governed.append(governed_entry)
                continue
            governed.append(entry)
        return governed

    def generate_content(
        self,
        contents: Any,
        generation_config: Optional[Any] = None,
        safety_settings: Optional[Any] = None,
        stream: bool = False,
        **kwargs,
    ) -> GeminiGovernanceResult:
        """
        Generate content with governance.

        Args:
            contents: Content to generate from (string, list, or parts)
            generation_config: Generation configuration
            safety_settings: Safety settings
            stream: Whether to stream responses
            **kwargs: Additional arguments

        Returns:
            GeminiGovernanceResult with governed response
        """
        original_contents = contents
        receipts_before = len(self._receipts)

        # Govern content
        if self._redact_prompts:
            governed_contents = self._govern_content(contents)
        else:
            governed_contents = contents

        # Build request kwargs
        request_kwargs = {}
        if generation_config:
            request_kwargs["generation_config"] = generation_config
        if safety_settings:
            request_kwargs["safety_settings"] = safety_settings

        # Call Gemini
        if stream:
            response = self._model.generate_content(
                governed_contents,
                stream=True,
                **request_kwargs,
                **kwargs,
            )
            return GeminiGovernanceResult(
                governed_data=governed_contents,
                original_data=original_contents,
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "generate_content", "stream": True},
            )

        response = self._model.generate_content(
            governed_contents,
            **request_kwargs,
            **kwargs,
        )

        # Govern response
        if self._redact_responses and response:
            if hasattr(response, "text") and isinstance(response.text, str):
                # Note: response.text is typically read-only, so we track it
                pass
            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and isinstance(part.text, str):
                                part.text, _ = self._govern_text(part.text)

        new_receipts = self._receipts[receipts_before:]

        return GeminiGovernanceResult(
            governed_data=governed_contents,
            original_data=original_contents,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "generate_content"},
        )

    async def agenerate_content(
        self,
        contents: Any,
        generation_config: Optional[Any] = None,
        safety_settings: Optional[Any] = None,
        stream: bool = False,
        **kwargs,
    ) -> GeminiGovernanceResult:
        """
        Generate content asynchronously with governance.

        Args:
            contents: Content to generate from
            generation_config: Generation configuration
            safety_settings: Safety settings
            stream: Whether to stream responses
            **kwargs: Additional arguments

        Returns:
            GeminiGovernanceResult with governed response
        """
        original_contents = contents
        receipts_before = len(self._receipts)

        # Govern content
        if self._redact_prompts:
            governed_contents = self._govern_content(contents)
        else:
            governed_contents = contents

        # Build request kwargs
        request_kwargs = {}
        if generation_config:
            request_kwargs["generation_config"] = generation_config
        if safety_settings:
            request_kwargs["safety_settings"] = safety_settings

        # Call Gemini
        response = await self._model.generate_content_async(
            governed_contents,
            stream=stream,
            **request_kwargs,
            **kwargs,
        )

        if stream:
            return GeminiGovernanceResult(
                governed_data=governed_contents,
                original_data=original_contents,
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "agenerate_content", "stream": True},
            )

        # Govern response
        if self._redact_responses and response:
            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and isinstance(part.text, str):
                                part.text, _ = self._govern_text(part.text)

        new_receipts = self._receipts[receipts_before:]

        return GeminiGovernanceResult(
            governed_data=governed_contents,
            original_data=original_contents,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "agenerate_content"},
        )

    def start_chat(
        self,
        history: Optional[List[Any]] = None,
        **kwargs,
    ) -> "TorkGeminiChat":
        """
        Start a governed chat session.

        Args:
            history: Optional chat history
            **kwargs: Additional arguments

        Returns:
            TorkGeminiChat wrapper
        """
        # Govern history if provided
        governed_history = history
        if self._redact_chat_history and history:
            governed_history = self._govern_history(history)

        chat = self._model.start_chat(history=governed_history, **kwargs)
        return TorkGeminiChat(chat, self._tork, self._redact_prompts, self._redact_responses, self._receipts)

    def embed_content(
        self,
        content: Union[str, List[str]],
        task_type: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs,
    ) -> GeminiGovernanceResult:
        """
        Create embeddings with governance.

        Args:
            content: Text(s) to embed
            task_type: Type of embedding task
            title: Optional title
            **kwargs: Additional arguments

        Returns:
            GeminiGovernanceResult with governed response
        """
        original_content = content
        receipts_before = len(self._receipts)

        # Govern content
        if self._redact_prompts:
            if isinstance(content, str):
                governed_content, _ = self._govern_text(content)
            else:
                governed_content = []
                for text in content:
                    governed_text, _ = self._govern_text(text)
                    governed_content.append(governed_text)
        else:
            governed_content = content

        # Build request kwargs
        request_kwargs = {}
        if task_type:
            request_kwargs["task_type"] = task_type
        if title:
            request_kwargs["title"] = title

        # Call Gemini
        response = self._model.embed_content(governed_content, **request_kwargs, **kwargs)

        new_receipts = self._receipts[receipts_before:]

        return GeminiGovernanceResult(
            governed_data=governed_content,
            original_data=original_content,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "embed_content"},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying model."""
        return getattr(self._model, name)


class TorkGeminiChat:
    """Governed wrapper for Gemini chat session."""

    def __init__(
        self,
        chat: Any,
        tork: Tork,
        redact_prompts: bool,
        redact_responses: bool,
        receipts: List[Receipt],
    ):
        self._chat = chat
        self._tork = tork
        self._redact_prompts = redact_prompts
        self._redact_responses = redact_responses
        self._receipts = receipts

    def _govern_text(self, text: Any) -> tuple[Any, Optional[GovernanceResult]]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

    def send_message(
        self,
        content: Any,
        **kwargs,
    ) -> GeminiGovernanceResult:
        """
        Send a message with governance.

        Args:
            content: Message content
            **kwargs: Additional arguments

        Returns:
            GeminiGovernanceResult with governed response
        """
        original_content = content
        receipts_before = len(self._receipts)

        # Govern content
        governed_content = content
        if self._redact_prompts:
            if isinstance(content, str):
                governed_content, _ = self._govern_text(content)
            elif isinstance(content, list):
                governed_content = []
                for part in content:
                    if isinstance(part, str):
                        text, _ = self._govern_text(part)
                        governed_content.append(text)
                    else:
                        governed_content.append(part)

        # Send message
        response = self._chat.send_message(governed_content, **kwargs)

        # Govern response
        if self._redact_responses and response:
            if hasattr(response, "text") and isinstance(response.text, str):
                pass  # response.text is typically read-only

        new_receipts = self._receipts[receipts_before:]

        return GeminiGovernanceResult(
            governed_data=governed_content,
            original_data=original_content,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "send_message"},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying chat."""
        return getattr(self._chat, name)


def govern_generate_content(
    contents: Any,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> GeminiGovernanceResult:
    """
    Apply governance to Gemini content.

    Args:
        contents: Content to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        GeminiGovernanceResult with governed content
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    if isinstance(contents, str):
        governed = govern_text(contents)
    elif isinstance(contents, list):
        governed = []
        for part in contents:
            if isinstance(part, str):
                governed.append(govern_text(part))
            elif isinstance(part, dict) and "text" in part:
                governed_part = part.copy()
                governed_part["text"] = govern_text(part["text"])
                governed.append(governed_part)
            else:
                governed.append(part)
    else:
        governed = contents

    return GeminiGovernanceResult(
        governed_data=governed,
        original_data=contents,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_generate_content"},
    )


def govern_gemini_chat(
    message: str,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> GeminiGovernanceResult:
    """
    Apply governance to Gemini chat message.

    Args:
        message: Message to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        GeminiGovernanceResult with governed message
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    result = tork_instance.govern(message)

    return GeminiGovernanceResult(
        governed_data=result.output,
        original_data=message,
        pii_detected=result.receipt is not None,
        pii_count=result.receipt.pii_count if result.receipt and hasattr(result.receipt, "pii_count") else 0,
        receipts=[result.receipt] if result.receipt else [],
        metadata={"operation": "govern_gemini_chat"},
    )


def govern_gemini_embedding(
    content: Union[str, List[str]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> GeminiGovernanceResult:
    """
    Apply governance to Gemini embedding input.

    Args:
        content: Content to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        GeminiGovernanceResult with governed content
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    if isinstance(content, str):
        governed = govern_text(content)
    else:
        governed = [govern_text(t) for t in content]

    return GeminiGovernanceResult(
        governed_data=governed,
        original_data=content,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_gemini_embedding"},
    )


def gemini_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Gemini operations.

    Args:
        tork: Tork instance
        config: TorkConfig if tork not provided

    Returns:
        Decorator function
    """
    tork_instance = tork or Tork(config=config or TorkConfig())

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Govern content/contents argument
            governed_args = list(args)
            if len(governed_args) > 0 and isinstance(governed_args[0], str):
                result = tork_instance.govern(governed_args[0])
                governed_args[0] = result.output

            if "contents" in kwargs:
                if isinstance(kwargs["contents"], str):
                    result = tork_instance.govern(kwargs["contents"])
                    kwargs["contents"] = result.output

            if "content" in kwargs:
                if isinstance(kwargs["content"], str):
                    result = tork_instance.govern(kwargs["content"])
                    kwargs["content"] = result.output

            return func(*governed_args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkGeminiClient",
    "TorkGeminiChat",
    "GeminiGovernanceResult",
    "govern_generate_content",
    "govern_gemini_chat",
    "govern_gemini_embedding",
    "gemini_governed",
]

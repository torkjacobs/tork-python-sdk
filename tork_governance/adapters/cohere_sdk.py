"""
Tork Governance adapter for Cohere SDK.

Provides governance for Cohere API with automatic
PII detection and redaction in chat, generate, embed, and rerank.

Usage:
    from tork_governance.adapters.cohere_sdk import TorkCohereClient

    # Wrap Cohere client
    import cohere
    client = TorkCohereClient(cohere.Client("..."))

    # All API calls now governed
    response = client.chat(
        message="My SSN is 123-45-6789"
    )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class CohereGovernanceResult:
    """Result of Cohere governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    response: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkCohereClient:
    """
    Governed wrapper for Cohere client.

    Automatically applies PII detection and redaction to all
    chat, generate, embed, and rerank requests.

    Example:
        import cohere
        from tork_governance.adapters.cohere_sdk import TorkCohereClient

        co = cohere.Client("...")
        governed = TorkCohereClient(co)

        # Chat is governed
        response = governed.chat(message="Hello")
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_messages: bool = True,
        redact_prompts: bool = True,
        redact_documents: bool = True,
        redact_responses: bool = True,
    ):
        """
        Initialize governed Cohere client.

        Args:
            client: Cohere client instance
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_messages: Whether to redact PII in messages
            redact_prompts: Whether to redact PII in prompts
            redact_documents: Whether to redact PII in documents
            redact_responses: Whether to redact PII in responses
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_messages = redact_messages
        self._redact_prompts = redact_prompts
        self._redact_documents = redact_documents
        self._redact_responses = redact_responses
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Cohere client."""
        return self._client

    def _govern_text(self, text: Any) -> tuple[Any, Optional[GovernanceResult]]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

    def _govern_chat_history(self, chat_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply governance to chat history."""
        governed = []
        for msg in chat_history:
            governed_msg = msg.copy()
            if "message" in governed_msg:
                governed_msg["message"], _ = self._govern_text(governed_msg["message"])
            if "text" in governed_msg:
                governed_msg["text"], _ = self._govern_text(governed_msg["text"])
            governed.append(governed_msg)
        return governed

    def _govern_documents(self, documents: List[Union[str, Dict[str, Any]]]) -> List[Union[str, Dict[str, Any]]]:
        """Apply governance to documents."""
        governed = []
        for doc in documents:
            if isinstance(doc, str):
                text, _ = self._govern_text(doc)
                governed.append(text)
            elif isinstance(doc, dict):
                governed_doc = doc.copy()
                if "text" in governed_doc:
                    governed_doc["text"], _ = self._govern_text(governed_doc["text"])
                if "title" in governed_doc:
                    governed_doc["title"], _ = self._govern_text(governed_doc["title"])
                if "snippet" in governed_doc:
                    governed_doc["snippet"], _ = self._govern_text(governed_doc["snippet"])
                governed.append(governed_doc)
            else:
                governed.append(doc)
        return governed

    def chat(
        self,
        message: str,
        model: Optional[str] = None,
        preamble: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> CohereGovernanceResult:
        """
        Chat with governance.

        Args:
            message: User message
            model: Model to use
            preamble: System preamble
            chat_history: Previous messages
            documents: Documents for RAG
            stream: Whether to stream responses
            **kwargs: Additional arguments for Cohere

        Returns:
            CohereGovernanceResult with governed response
        """
        original_message = message
        original_preamble = preamble
        original_history = chat_history
        original_documents = documents
        receipts_before = len(self._receipts)

        # Govern message
        governed_message = message
        if self._redact_messages:
            governed_message, _ = self._govern_text(message)

        # Govern preamble
        governed_preamble = preamble
        if self._redact_prompts and preamble:
            governed_preamble, _ = self._govern_text(preamble)

        # Govern chat history
        governed_history = chat_history
        if self._redact_messages and chat_history:
            governed_history = self._govern_chat_history(chat_history)

        # Govern documents
        governed_documents = documents
        if self._redact_documents and documents:
            governed_documents = self._govern_documents(documents)

        # Build request
        request_kwargs = {"message": governed_message, **kwargs}
        if model:
            request_kwargs["model"] = model
        if governed_preamble:
            request_kwargs["preamble"] = governed_preamble
        if governed_history:
            request_kwargs["chat_history"] = governed_history
        if governed_documents:
            request_kwargs["documents"] = governed_documents

        # Call Cohere
        if stream:
            response = self._client.chat_stream(**request_kwargs)
        else:
            response = self._client.chat(**request_kwargs)

        # Handle streaming
        if stream:
            return CohereGovernanceResult(
                governed_data={"message": governed_message, "preamble": governed_preamble},
                original_data={"message": original_message, "preamble": original_preamble},
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "chat", "model": model, "stream": True},
            )

        # Govern response
        if self._redact_responses and response:
            if hasattr(response, "text") and isinstance(response.text, str):
                response.text, _ = self._govern_text(response.text)

        new_receipts = self._receipts[receipts_before:]

        return CohereGovernanceResult(
            governed_data={
                "message": governed_message,
                "preamble": governed_preamble,
                "chat_history": governed_history,
                "documents": governed_documents,
            },
            original_data={
                "message": original_message,
                "preamble": original_preamble,
                "chat_history": original_history,
                "documents": original_documents,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "chat", "model": model},
        )

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        num_generations: int = 1,
        stream: bool = False,
        **kwargs,
    ) -> CohereGovernanceResult:
        """
        Generate text with governance.

        Args:
            prompt: Prompt text
            model: Model to use
            num_generations: Number of generations
            stream: Whether to stream responses
            **kwargs: Additional arguments for Cohere

        Returns:
            CohereGovernanceResult with governed response
        """
        original_prompt = prompt
        receipts_before = len(self._receipts)

        # Govern prompt
        governed_prompt = prompt
        if self._redact_prompts:
            governed_prompt, _ = self._govern_text(prompt)

        # Build request
        request_kwargs = {
            "prompt": governed_prompt,
            "num_generations": num_generations,
            **kwargs,
        }
        if model:
            request_kwargs["model"] = model

        # Call Cohere
        if stream:
            response = self._client.generate_stream(**request_kwargs)
        else:
            response = self._client.generate(**request_kwargs)

        # Handle streaming
        if stream:
            return CohereGovernanceResult(
                governed_data=governed_prompt,
                original_data=original_prompt,
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "generate", "model": model, "stream": True},
            )

        # Govern response
        if self._redact_responses and response:
            if hasattr(response, "generations"):
                for gen in response.generations:
                    if hasattr(gen, "text") and isinstance(gen.text, str):
                        gen.text, _ = self._govern_text(gen.text)

        new_receipts = self._receipts[receipts_before:]

        return CohereGovernanceResult(
            governed_data=governed_prompt,
            original_data=original_prompt,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "generate", "model": model},
        )

    def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        input_type: Optional[str] = None,
        embedding_types: Optional[List[str]] = None,
        **kwargs,
    ) -> CohereGovernanceResult:
        """
        Create embeddings with governance.

        Args:
            texts: Texts to embed
            model: Model to use
            input_type: Type of input
            embedding_types: Types of embeddings
            **kwargs: Additional arguments for Cohere

        Returns:
            CohereGovernanceResult with governed response
        """
        original_texts = texts
        receipts_before = len(self._receipts)

        # Govern texts
        governed_texts = texts
        if self._redact_prompts:
            governed_texts = []
            for text in texts:
                governed_text, _ = self._govern_text(text)
                governed_texts.append(governed_text)

        # Build request
        request_kwargs = {"texts": governed_texts, **kwargs}
        if model:
            request_kwargs["model"] = model
        if input_type:
            request_kwargs["input_type"] = input_type
        if embedding_types:
            request_kwargs["embedding_types"] = embedding_types

        # Call Cohere
        response = self._client.embed(**request_kwargs)

        new_receipts = self._receipts[receipts_before:]

        return CohereGovernanceResult(
            governed_data=governed_texts,
            original_data=original_texts,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "embed", "model": model},
        )

    def rerank(
        self,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        model: Optional[str] = None,
        top_n: Optional[int] = None,
        **kwargs,
    ) -> CohereGovernanceResult:
        """
        Rerank documents with governance.

        Args:
            query: Query text
            documents: Documents to rerank
            model: Model to use
            top_n: Number of top results
            **kwargs: Additional arguments for Cohere

        Returns:
            CohereGovernanceResult with governed response
        """
        original_query = query
        original_documents = documents
        receipts_before = len(self._receipts)

        # Govern query
        governed_query = query
        if self._redact_prompts:
            governed_query, _ = self._govern_text(query)

        # Govern documents
        governed_documents = documents
        if self._redact_documents:
            governed_documents = self._govern_documents(documents)

        # Build request
        request_kwargs = {
            "query": governed_query,
            "documents": governed_documents,
            **kwargs,
        }
        if model:
            request_kwargs["model"] = model
        if top_n:
            request_kwargs["top_n"] = top_n

        # Call Cohere
        response = self._client.rerank(**request_kwargs)

        new_receipts = self._receipts[receipts_before:]

        return CohereGovernanceResult(
            governed_data={"query": governed_query, "documents": governed_documents},
            original_data={"query": original_query, "documents": original_documents},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "rerank", "model": model},
        )

    def classify(
        self,
        inputs: List[str],
        examples: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> CohereGovernanceResult:
        """
        Classify texts with governance.

        Args:
            inputs: Texts to classify
            examples: Classification examples
            model: Model to use
            **kwargs: Additional arguments for Cohere

        Returns:
            CohereGovernanceResult with governed response
        """
        original_inputs = inputs
        original_examples = examples
        receipts_before = len(self._receipts)

        # Govern inputs
        governed_inputs = inputs
        if self._redact_prompts:
            governed_inputs = []
            for text in inputs:
                governed_text, _ = self._govern_text(text)
                governed_inputs.append(governed_text)

        # Govern examples
        governed_examples = examples
        if self._redact_prompts and examples:
            governed_examples = []
            for ex in examples:
                governed_ex = ex.copy()
                if "text" in governed_ex:
                    governed_ex["text"], _ = self._govern_text(governed_ex["text"])
                governed_examples.append(governed_ex)

        # Build request
        request_kwargs = {"inputs": governed_inputs, **kwargs}
        if model:
            request_kwargs["model"] = model
        if governed_examples:
            request_kwargs["examples"] = governed_examples

        # Call Cohere
        response = self._client.classify(**request_kwargs)

        new_receipts = self._receipts[receipts_before:]

        return CohereGovernanceResult(
            governed_data={"inputs": governed_inputs, "examples": governed_examples},
            original_data={"inputs": original_inputs, "examples": original_examples},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "classify", "model": model},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_cohere_chat(
    message: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> CohereGovernanceResult:
    """
    Apply governance to Cohere chat.

    Args:
        message: Message to govern
        chat_history: Chat history to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        CohereGovernanceResult with governed data
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    governed_message = govern_text(message)
    governed_history = None
    if chat_history:
        governed_history = []
        for msg in chat_history:
            governed_msg = msg.copy()
            if "message" in governed_msg:
                governed_msg["message"] = govern_text(governed_msg["message"])
            governed_history.append(governed_msg)

    return CohereGovernanceResult(
        governed_data={"message": governed_message, "chat_history": governed_history},
        original_data={"message": message, "chat_history": chat_history},
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_cohere_chat"},
    )


def govern_cohere_generate(
    prompt: str,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> CohereGovernanceResult:
    """
    Apply governance to Cohere generate prompt.

    Args:
        prompt: Prompt to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        CohereGovernanceResult with governed prompt
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    result = tork_instance.govern(prompt)

    return CohereGovernanceResult(
        governed_data=result.output,
        original_data=prompt,
        pii_detected=result.receipt is not None,
        pii_count=result.receipt.pii_count if result.receipt and hasattr(result.receipt, "pii_count") else 0,
        receipts=[result.receipt] if result.receipt else [],
        metadata={"operation": "govern_cohere_generate"},
    )


def govern_cohere_embed(
    texts: List[str],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> CohereGovernanceResult:
    """
    Apply governance to Cohere embed texts.

    Args:
        texts: Texts to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        CohereGovernanceResult with governed texts
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    governed = [govern_text(t) for t in texts]

    return CohereGovernanceResult(
        governed_data=governed,
        original_data=texts,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_cohere_embed"},
    )


def govern_cohere_rerank(
    query: str,
    documents: List[Union[str, Dict[str, Any]]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> CohereGovernanceResult:
    """
    Apply governance to Cohere rerank.

    Args:
        query: Query to govern
        documents: Documents to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        CohereGovernanceResult with governed data
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    governed_query = govern_text(query)
    governed_documents = []
    for doc in documents:
        if isinstance(doc, str):
            governed_documents.append(govern_text(doc))
        elif isinstance(doc, dict):
            governed_doc = doc.copy()
            if "text" in governed_doc:
                governed_doc["text"] = govern_text(governed_doc["text"])
            governed_documents.append(governed_doc)
        else:
            governed_documents.append(doc)

    return CohereGovernanceResult(
        governed_data={"query": governed_query, "documents": governed_documents},
        original_data={"query": query, "documents": documents},
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_cohere_rerank"},
    )


def cohere_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Cohere operations.

    Args:
        tork: Tork instance
        config: TorkConfig if tork not provided

    Returns:
        Decorator function
    """
    tork_instance = tork or Tork(config=config or TorkConfig())

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Govern message
            if "message" in kwargs and isinstance(kwargs["message"], str):
                result = tork_instance.govern(kwargs["message"])
                kwargs["message"] = result.output

            # Govern prompt
            if "prompt" in kwargs and isinstance(kwargs["prompt"], str):
                result = tork_instance.govern(kwargs["prompt"])
                kwargs["prompt"] = result.output

            # Govern query
            if "query" in kwargs and isinstance(kwargs["query"], str):
                result = tork_instance.govern(kwargs["query"])
                kwargs["query"] = result.output

            # Govern texts
            if "texts" in kwargs and isinstance(kwargs["texts"], list):
                kwargs["texts"] = [
                    tork_instance.govern(t).output if isinstance(t, str) else t
                    for t in kwargs["texts"]
                ]

            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkCohereClient",
    "CohereGovernanceResult",
    "govern_cohere_chat",
    "govern_cohere_generate",
    "govern_cohere_embed",
    "govern_cohere_rerank",
    "cohere_governed",
]

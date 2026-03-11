"""
LangGraph Integration for Tork Governance

Provides middleware and wrappers for LangGraph graph-based agent orchestration.
LangGraph uses a state machine pattern where nodes are functions and edges are transitions.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


def _extract_text_from_state(state: Any) -> List[str]:
    """Recursively extract string content from a LangGraph state dict."""
    texts = []
    if isinstance(state, str):
        texts.append(state)
    elif isinstance(state, dict):
        # Handle messages list (LangGraph convention)
        if "messages" in state:
            for msg in state["messages"]:
                if isinstance(msg, str):
                    texts.append(msg)
                elif isinstance(msg, dict) and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        texts.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, str):
                                texts.append(block)
                            elif isinstance(block, dict) and "text" in block:
                                texts.append(block["text"])
                elif hasattr(msg, "content"):
                    content = msg.content
                    if isinstance(content, str):
                        texts.append(content)
        # Also check other string values at top level
        for key, value in state.items():
            if key == "messages":
                continue
            if isinstance(value, str):
                texts.append(value)
    elif isinstance(state, list):
        for item in state:
            texts.extend(_extract_text_from_state(item))
    return texts


def _govern_state(tork: Tork, state: Any, receipts: List[Dict], direction: str, agent_id: str) -> Any:
    """Govern all text content found in a LangGraph state dict."""
    if isinstance(state, str):
        result = tork.govern(state)
        receipts.append({
            'type': direction,
            'agent_id': agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Content blocked by governance: {result.receipt.receipt_id}")
        return result.output

    if isinstance(state, dict):
        governed = dict(state)
        if "messages" in governed:
            governed_messages = []
            for msg in governed["messages"]:
                if isinstance(msg, str):
                    result = tork.govern(msg)
                    receipts.append({
                        'type': direction,
                        'agent_id': agent_id,
                        'receipt_id': result.receipt.receipt_id,
                        'action': result.action.value,
                    })
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Message blocked by governance: {result.receipt.receipt_id}")
                    governed_messages.append(result.output)
                elif isinstance(msg, dict) and "content" in msg:
                    governed_msg = dict(msg)
                    content = msg["content"]
                    if isinstance(content, str):
                        result = tork.govern(content)
                        receipts.append({
                            'type': direction,
                            'agent_id': agent_id,
                            'receipt_id': result.receipt.receipt_id,
                            'action': result.action.value,
                        })
                        if result.action == GovernanceAction.DENY:
                            raise ValueError(f"Message blocked by governance: {result.receipt.receipt_id}")
                        governed_msg["content"] = result.output
                    governed_messages.append(governed_msg)
                else:
                    governed_messages.append(msg)
            governed["messages"] = governed_messages

        # Govern other string values
        for key, value in governed.items():
            if key == "messages":
                continue
            if isinstance(value, str):
                result = tork.govern(value)
                receipts.append({
                    'type': direction,
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"State field '{key}' blocked by governance: {result.receipt.receipt_id}")
                governed[key] = result.output
        return governed

    return state


class TorkLangGraphMiddleware:
    """
    Middleware for LangGraph that applies Tork governance to graph execution.

    Wraps a LangGraph CompiledGraph, intercepting node inputs/outputs
    through governance checks.

    Example:
        >>> from tork_governance.adapters.langgraph import TorkLangGraphMiddleware
        >>> from langgraph.graph import StateGraph
        >>>
        >>> middleware = TorkLangGraphMiddleware()
        >>> graph = StateGraph(...)
        >>> compiled = graph.compile()
        >>> governed = middleware.wrap_graph(compiled)
        >>> result = governed.invoke({"messages": [{"role": "user", "content": "Hello"}]})
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "langgraph-agent",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def wrap_graph(self, graph: Any) -> "GovernedGraph":
        """Wrap a compiled LangGraph with governance controls."""
        return GovernedGraph(graph, self)

    def process_input(self, state: Any) -> Any:
        """Process and validate input state."""
        return _govern_state(self.tork, state, self.receipts, "input", self.agent_id)

    def process_output(self, state: Any) -> Any:
        """Process and validate output state."""
        return _govern_state(self.tork, state, self.receipts, "output", self.agent_id)

    def govern(self, text: str) -> str:
        """Govern a single text string."""
        result = self.tork.govern(text)
        self.receipts.append({
            'type': 'govern',
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        return result.output


class GovernedGraph:
    """
    Wrapper for a compiled LangGraph that applies governance to invoke and stream.

    Example:
        >>> from tork_governance.adapters.langgraph import TorkLangGraphMiddleware
        >>> middleware = TorkLangGraphMiddleware()
        >>> governed = middleware.wrap_graph(compiled_graph)
        >>> result = governed.invoke({"messages": [{"role": "user", "content": "Hello"}]})
    """

    def __init__(self, graph: Any, middleware: TorkLangGraphMiddleware):
        self._graph = graph
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped graph."""
        return getattr(self._graph, name)

    def invoke(self, state: Any, **kwargs) -> Any:
        """Invoke the graph with governance applied to input and output."""
        if self._middleware.govern_input:
            state = self._middleware.process_input(state)

        result = self._graph.invoke(state, **kwargs)

        if self._middleware.govern_output:
            result = self._middleware.process_output(result)

        return result

    def stream(self, state: Any, **kwargs):
        """Stream the graph with governance applied to each chunk."""
        if self._middleware.govern_input:
            state = self._middleware.process_input(state)

        for chunk in self._graph.stream(state, **kwargs):
            if self._middleware.govern_output:
                chunk = self._middleware.process_output(chunk)
            yield chunk


class TorkGovernedNode:
    """
    Decorator for individual LangGraph graph nodes that governs input/output state.

    Example:
        >>> from tork_governance.adapters.langgraph import TorkGovernedNode
        >>> from tork_governance import Tork
        >>>
        >>> tork = Tork()
        >>> governed_node = TorkGovernedNode(tork=tork)
        >>>
        >>> @governed_node
        ... def my_node(state):
        ...     return {"messages": [{"role": "assistant", "content": "response"}]}
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "langgraph-node",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Any, *args, **kwargs) -> Any:
            if self.govern_input:
                state = _govern_state(self.tork, state, self.receipts, "node_input", self.agent_id)

            result = func(state, *args, **kwargs)

            if self.govern_output:
                result = _govern_state(self.tork, result, self.receipts, "node_output", self.agent_id)

            return result
        return wrapper


def govern_graph_invoke(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "langgraph-invoke",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for graph.invoke() that governs the initial input and final output.

    Example:
        >>> from tork_governance.adapters.langgraph import govern_graph_invoke
        >>>
        >>> @govern_graph_invoke()
        ... def run_graph(state):
        ...     return compiled_graph.invoke(state)
    """
    _tork = tork or Tork(api_key=api_key, policy_version=policy_version)
    _receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Any, *args, **kwargs) -> Any:
            if govern_input:
                state = _govern_state(_tork, state, _receipts, "invoke_input", agent_id)

            result = func(state, *args, **kwargs)

            if govern_output:
                result = _govern_state(_tork, result, _receipts, "invoke_output", agent_id)

            return result

        wrapper.receipts = _receipts
        return wrapper
    return decorator


def govern_graph_stream(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "langgraph-stream",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for graph.stream() that governs each streamed chunk.

    Example:
        >>> from tork_governance.adapters.langgraph import govern_graph_stream
        >>>
        >>> @govern_graph_stream()
        ... def stream_graph(state):
        ...     yield from compiled_graph.stream(state)
    """
    _tork = tork or Tork(api_key=api_key, policy_version=policy_version)
    _receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Any, *args, **kwargs):
            if govern_input:
                state = _govern_state(_tork, state, _receipts, "stream_input", agent_id)

            for chunk in func(state, *args, **kwargs):
                if govern_output:
                    chunk = _govern_state(_tork, chunk, _receipts, "stream_output", agent_id)
                yield chunk

        wrapper.receipts = _receipts
        return wrapper
    return decorator

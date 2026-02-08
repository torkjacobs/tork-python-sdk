"""
Tork Governance Framework Adapters

Provides integrations for popular Python frameworks:
- LangChain
- CrewAI
- AutoGen
- OpenAI Agents SDK
- FastAPI
- Django
- Flask
- MCP (Model Context Protocol)
- LlamaIndex
- Semantic Kernel
- Haystack
- Pydantic AI
- DSPy (Stanford)
- Instructor
- Guidance (Microsoft)
- LMQL
- Outlines
- Marvin
- SuperAGI
- MetaGPT
- BabyAGI
- AgentGPT
- Flowise
- Langflow
- Starlette
- Guardrails AI
- Dify
- LiteLLM
- NeMo Guardrails
- Ollama
- vLLM
- ChromaDB
- Pinecone
- Weaviate
- Qdrant
- Milvus
- LangSmith
- Helicone
- Weights & Biases (W&B)
- Arize
- Langfuse
- Phoenix (Arize Phoenix)
- Portkey
- PromptLayer
- Humanloop
- OpenAI SDK
- Anthropic SDK
- Google Gemini
- AWS Bedrock
- Azure OpenAI
- Cohere SDK
- Mistral SDK
- Groq SDK
- Together AI SDK
- Replicate SDK
- Hugging Face Transformers
- n8n AI
- Mirascope
- Magentic
- txtai
- ChatDev
- CAMEL
- Rebuff
- LLM Guard
- LocalAI
- LM Studio
- GPT4All
- PrivateGPT
- Tornado
- Pyramid
- Sanic
"""

from .langchain import TorkCallbackHandler, TorkGovernedChain, create_governed_chain
from .guardrails_ai import TorkValidator, TorkGuard, TorkRail, with_tork_governance as guardrails_with_tork
from .dify import TorkDifyNode, TorkDifyHook, TorkDifyApp, dify_governed
from .litellm import TorkLiteLLMCallback, TorkLiteLLMProxy, govern_completion, agovern_completion, litellm_governed
from .nemo_guardrails import (
    TorkNeMoRails,
    TorkNeMoAction,
    tork_input_rail,
    tork_output_rail,
    create_tork_rails_config,
    register_tork_actions,
    TORK_COLANG_TEMPLATE
)
from .ollama import TorkOllamaClient, AsyncTorkOllamaClient, govern_generate, govern_chat, ollama_governed
from .vllm import TorkVLLMEngine, AsyncTorkVLLMEngine, TorkSamplingParams, govern_generate as vllm_govern_generate, vllm_governed
from .chromadb import TorkChromaClient, TorkChromaCollection, govern_add, govern_query as chroma_govern_query, chromadb_governed
from .pinecone import TorkPineconeIndex, TorkPineconeClient, govern_upsert, govern_query as pinecone_govern_query, pinecone_governed
from .weaviate import TorkWeaviateClient, TorkWeaviateCollection, AsyncTorkWeaviateClient, govern_add as weaviate_govern_add, govern_query as weaviate_govern_query, govern_batch as weaviate_govern_batch, WeaviateGovernanceResult
from .qdrant import TorkQdrantClient, AsyncTorkQdrantClient, govern_upsert as qdrant_govern_upsert, govern_search as qdrant_govern_search, govern_scroll, govern_batch as qdrant_govern_batch, QdrantGovernanceResult
from .milvus import TorkMilvusClient, TorkMilvusCollection, AsyncTorkMilvusClient, govern_insert, govern_search as milvus_govern_search, govern_query as milvus_govern_query, MilvusGovernanceResult
from .langsmith import TorkLangSmithClient, TorkTracerCallback, govern_log_run, govern_feedback, create_governed_tracer, LangSmithGovernanceResult
from .helicone import TorkHeliconeClient, govern_log_request, govern_log_response, helicone_governed, HeliconeGovernanceResult
from .wandb import TorkWandbRun, TorkWandbCallback, govern_log, govern_table, wandb_governed, WandbGovernanceResult
from .arize import TorkArizeClient, govern_log_prediction, govern_log_embedding, arize_governed, ArizeGovernanceResult
from .langfuse import TorkLangfuseClient, TorkLangfuseCallback, govern_trace, govern_generation, govern_score, langfuse_governed, LangfuseGovernanceResult
from .phoenix import TorkPhoenixClient, govern_log_traces, govern_log_spans, phoenix_governed, PhoenixGovernanceResult
from .portkey import TorkPortkeyClient, govern_completion as portkey_govern_completion, govern_log as portkey_govern_log, portkey_governed, PortkeyGovernanceResult
from .promptlayer import TorkPromptLayerClient, govern_log_request as promptlayer_govern_log_request, govern_track_prompt, promptlayer_governed, PromptLayerGovernanceResult
from .humanloop import TorkHumanloopClient, govern_log as humanloop_govern_log, govern_feedback as humanloop_govern_feedback, humanloop_governed, HumanloopGovernanceResult
from .openai_sdk import TorkOpenAIClient, govern_chat_completion, govern_completion as openai_govern_completion, govern_embedding, openai_governed, OpenAIGovernanceResult
from .anthropic_sdk import TorkAnthropicClient, govern_message, govern_anthropic_completion, anthropic_governed, AnthropicGovernanceResult
from .google_gemini import TorkGeminiClient, TorkGeminiChat, govern_generate_content, govern_gemini_chat, govern_gemini_embedding, gemini_governed, GeminiGovernanceResult
from .aws_bedrock import TorkBedrockClient, govern_invoke_model, govern_converse, bedrock_governed, BedrockGovernanceResult
from .azure_openai import TorkAzureOpenAIClient, govern_azure_chat_completion, govern_azure_completion, govern_azure_embedding, azure_openai_governed, AzureOpenAIGovernanceResult
from .cohere_sdk import TorkCohereClient, govern_cohere_chat, govern_cohere_generate, govern_cohere_embed, govern_cohere_rerank, cohere_governed, CohereGovernanceResult
from .mistral_sdk import TorkMistralClient, AsyncTorkMistralClient, mistral_governed
from .groq_sdk import TorkGroqClient, AsyncTorkGroqClient, groq_governed
from .together_sdk import TorkTogetherClient, AsyncTorkTogetherClient, together_governed
from .replicate_sdk import TorkReplicateClient, AsyncTorkReplicateClient, replicate_governed
from .huggingface import TorkHFPipeline, TorkHFModel, TorkHFTokenizer, govern_generate as hf_govern_generate, govern_pipeline as hf_govern_pipeline, govern_inference, huggingface_governed, HuggingFaceGovernanceResult
from .n8n_ai import TorkN8nWebhook, TorkN8nNode, TorkN8nAIChain, AsyncTorkN8nAIChain, n8n_governed, create_n8n_governance_node, N8nGovernanceResult
from .crewai import TorkCrewAIMiddleware, GovernedAgent, GovernedCrew
from .autogen import TorkAutoGenMiddleware, GovernedAutoGenAgent
from .openai_agents import TorkOpenAIAgentsMiddleware, GovernedOpenAIAgent
from .fastapi import TorkFastAPIMiddleware, TorkFastAPIDependency
from .django import TorkDjangoMiddleware
from .flask import TorkFlask, tork_required
from .mcp import TorkMCPToolWrapper, TorkMCPServer, TorkMCPMiddleware
from .llamaindex import TorkLlamaIndexCallback, TorkQueryEngine, TorkRetriever
from .semantic_kernel import TorkSKFilter, TorkSKPlugin, TorkSKPromptFilter
from .haystack import TorkHaystackComponent, TorkHaystackPipeline, TorkDocumentProcessor
from .pydantic_ai import TorkPydanticAIMiddleware, TorkPydanticAITool, TorkAgentDependency
from .dspy import TorkDSPyModule, TorkDSPySignature, governed_predict
from .instructor import TorkInstructorClient, TorkInstructorPatch, governed_response
from .guidance import TorkGuidanceProgram, TorkGuidanceGen, governed_block
from .lmql import TorkLMQLQuery, TorkLMQLRuntime, governed_query
from .outlines import TorkOutlinesGenerator, TorkOutlinesModel, governed_generate
from .marvin import TorkMarvinAI, governed_fn, governed_classifier
from .superagi import TorkSuperAGIAgent, TorkSuperAGITool, TorkSuperAGIWorkflow
from .metagpt import TorkMetaGPTRole, TorkMetaGPTTeam, TorkMetaGPTAction
from .babyagi import TorkBabyAGIAgent, TorkBabyAGITaskManager, governed_task
from .agentgpt import TorkAgentGPTAgent, TorkAgentGPTTask, TorkAgentGPTGoal
from .flowise import TorkFlowiseNode, TorkFlowiseFlow, TorkFlowiseAPI
from .langflow import TorkLangflowComponent, TorkLangflowFlow, TorkLangflowAPI
from .starlette import TorkStarletteMiddleware, TorkStarletteRoute, tork_route
from .mirascope_adapter import TorkMirascopeCall, mirascope_governed
from .magentic_adapter import TorkMagenticPrompt, magentic_governed
from .txtai_adapter import TorkTxtaiEmbeddings, TorkTxtaiPipeline, txtai_governed
from .chatdev_adapter import TorkChatDevPhase, chatdev_governed
from .camel_adapter import TorkCamelAgent, TorkCamelRolePlaying, camel_governed
from .rebuff_adapter import TorkRebuff, rebuff_governed
from .llm_guard_adapter import TorkLLMGuard, llm_guard_governed
from .localai_adapter import TorkLocalAIClient, localai_governed
from .lmstudio_adapter import TorkLMStudioClient, lmstudio_governed
from .gpt4all_adapter import TorkGPT4All, gpt4all_governed
from .privategpt_adapter import TorkPrivateGPT, privategpt_governed
from .tornado_adapter import TorkTornadoMixin, TorkTornadoMiddleware, tornado_governed
from .pyramid_adapter import TorkPyramidTween, TorkPyramidMiddleware, pyramid_governed
from .sanic_adapter import TorkSanicMiddleware, sanic_governed

__all__ = [
    # LangChain
    "TorkCallbackHandler",
    "TorkGovernedChain",
    "create_governed_chain",
    # CrewAI
    "TorkCrewAIMiddleware",
    "GovernedAgent",
    "GovernedCrew",
    # AutoGen
    "TorkAutoGenMiddleware",
    "GovernedAutoGenAgent",
    # OpenAI Agents
    "TorkOpenAIAgentsMiddleware",
    "GovernedOpenAIAgent",
    # FastAPI
    "TorkFastAPIMiddleware",
    "TorkFastAPIDependency",
    # Django
    "TorkDjangoMiddleware",
    # Flask
    "TorkFlask",
    "tork_required",
    # MCP (Model Context Protocol)
    "TorkMCPToolWrapper",
    "TorkMCPServer",
    "TorkMCPMiddleware",
    # LlamaIndex
    "TorkLlamaIndexCallback",
    "TorkQueryEngine",
    "TorkRetriever",
    # Semantic Kernel
    "TorkSKFilter",
    "TorkSKPlugin",
    "TorkSKPromptFilter",
    # Haystack
    "TorkHaystackComponent",
    "TorkHaystackPipeline",
    "TorkDocumentProcessor",
    # Pydantic AI
    "TorkPydanticAIMiddleware",
    "TorkPydanticAITool",
    "TorkAgentDependency",
    # DSPy
    "TorkDSPyModule",
    "TorkDSPySignature",
    "governed_predict",
    # Instructor
    "TorkInstructorClient",
    "TorkInstructorPatch",
    "governed_response",
    # Guidance
    "TorkGuidanceProgram",
    "TorkGuidanceGen",
    "governed_block",
    # LMQL
    "TorkLMQLQuery",
    "TorkLMQLRuntime",
    "governed_query",
    # Outlines
    "TorkOutlinesGenerator",
    "TorkOutlinesModel",
    "governed_generate",
    # Marvin
    "TorkMarvinAI",
    "governed_fn",
    "governed_classifier",
    # SuperAGI
    "TorkSuperAGIAgent",
    "TorkSuperAGITool",
    "TorkSuperAGIWorkflow",
    # MetaGPT
    "TorkMetaGPTRole",
    "TorkMetaGPTTeam",
    "TorkMetaGPTAction",
    # BabyAGI
    "TorkBabyAGIAgent",
    "TorkBabyAGITaskManager",
    "governed_task",
    # AgentGPT
    "TorkAgentGPTAgent",
    "TorkAgentGPTTask",
    "TorkAgentGPTGoal",
    # Flowise
    "TorkFlowiseNode",
    "TorkFlowiseFlow",
    "TorkFlowiseAPI",
    # Langflow
    "TorkLangflowComponent",
    "TorkLangflowFlow",
    "TorkLangflowAPI",
    # Starlette
    "TorkStarletteMiddleware",
    "TorkStarletteRoute",
    "tork_route",
    # Guardrails AI
    "TorkValidator",
    "TorkGuard",
    "TorkRail",
    "guardrails_with_tork",
    # Dify
    "TorkDifyNode",
    "TorkDifyHook",
    "TorkDifyApp",
    "dify_governed",
    # LiteLLM
    "TorkLiteLLMCallback",
    "TorkLiteLLMProxy",
    "govern_completion",
    "agovern_completion",
    "litellm_governed",
    # NeMo Guardrails
    "TorkNeMoRails",
    "TorkNeMoAction",
    "tork_input_rail",
    "tork_output_rail",
    "create_tork_rails_config",
    "register_tork_actions",
    "TORK_COLANG_TEMPLATE",
    # Ollama
    "TorkOllamaClient",
    "AsyncTorkOllamaClient",
    "govern_generate",
    "govern_chat",
    "ollama_governed",
    # vLLM
    "TorkVLLMEngine",
    "AsyncTorkVLLMEngine",
    "TorkSamplingParams",
    "vllm_govern_generate",
    "vllm_governed",
    # ChromaDB
    "TorkChromaClient",
    "TorkChromaCollection",
    "govern_add",
    "chroma_govern_query",
    "chromadb_governed",
    # Pinecone
    "TorkPineconeIndex",
    "TorkPineconeClient",
    "govern_upsert",
    "pinecone_govern_query",
    "pinecone_governed",
    # Weaviate
    "TorkWeaviateClient",
    "TorkWeaviateCollection",
    "AsyncTorkWeaviateClient",
    "weaviate_govern_add",
    "weaviate_govern_query",
    "weaviate_govern_batch",
    "WeaviateGovernanceResult",
    # Qdrant
    "TorkQdrantClient",
    "AsyncTorkQdrantClient",
    "qdrant_govern_upsert",
    "qdrant_govern_search",
    "govern_scroll",
    "qdrant_govern_batch",
    "QdrantGovernanceResult",
    # Milvus
    "TorkMilvusClient",
    "TorkMilvusCollection",
    "AsyncTorkMilvusClient",
    "govern_insert",
    "milvus_govern_search",
    "milvus_govern_query",
    "MilvusGovernanceResult",
    # LangSmith
    "TorkLangSmithClient",
    "TorkTracerCallback",
    "govern_log_run",
    "govern_feedback",
    "create_governed_tracer",
    "LangSmithGovernanceResult",
    # Helicone
    "TorkHeliconeClient",
    "govern_log_request",
    "govern_log_response",
    "helicone_governed",
    "HeliconeGovernanceResult",
    # Weights & Biases
    "TorkWandbRun",
    "TorkWandbCallback",
    "govern_log",
    "govern_table",
    "wandb_governed",
    "WandbGovernanceResult",
    # Arize
    "TorkArizeClient",
    "govern_log_prediction",
    "govern_log_embedding",
    "arize_governed",
    "ArizeGovernanceResult",
    # Langfuse
    "TorkLangfuseClient",
    "TorkLangfuseCallback",
    "govern_trace",
    "govern_generation",
    "govern_score",
    "langfuse_governed",
    "LangfuseGovernanceResult",
    # Phoenix (Arize Phoenix)
    "TorkPhoenixClient",
    "govern_log_traces",
    "govern_log_spans",
    "phoenix_governed",
    "PhoenixGovernanceResult",
    # Portkey
    "TorkPortkeyClient",
    "portkey_govern_completion",
    "portkey_govern_log",
    "portkey_governed",
    "PortkeyGovernanceResult",
    # PromptLayer
    "TorkPromptLayerClient",
    "promptlayer_govern_log_request",
    "govern_track_prompt",
    "promptlayer_governed",
    "PromptLayerGovernanceResult",
    # Humanloop
    "TorkHumanloopClient",
    "humanloop_govern_log",
    "humanloop_govern_feedback",
    "humanloop_governed",
    "HumanloopGovernanceResult",
    # OpenAI SDK
    "TorkOpenAIClient",
    "govern_chat_completion",
    "openai_govern_completion",
    "govern_embedding",
    "openai_governed",
    "OpenAIGovernanceResult",
    # Anthropic SDK
    "TorkAnthropicClient",
    "govern_message",
    "govern_anthropic_completion",
    "anthropic_governed",
    "AnthropicGovernanceResult",
    # Google Gemini
    "TorkGeminiClient",
    "TorkGeminiChat",
    "govern_generate_content",
    "govern_gemini_chat",
    "govern_gemini_embedding",
    "gemini_governed",
    "GeminiGovernanceResult",
    # AWS Bedrock
    "TorkBedrockClient",
    "govern_invoke_model",
    "govern_converse",
    "bedrock_governed",
    "BedrockGovernanceResult",
    # Azure OpenAI
    "TorkAzureOpenAIClient",
    "govern_azure_chat_completion",
    "govern_azure_completion",
    "govern_azure_embedding",
    "azure_openai_governed",
    "AzureOpenAIGovernanceResult",
    # Cohere SDK
    "TorkCohereClient",
    "govern_cohere_chat",
    "govern_cohere_generate",
    "govern_cohere_embed",
    "govern_cohere_rerank",
    "cohere_governed",
    "CohereGovernanceResult",
    # Mistral SDK
    "TorkMistralClient",
    "AsyncTorkMistralClient",
    "mistral_governed",
    # Groq SDK
    "TorkGroqClient",
    "AsyncTorkGroqClient",
    "groq_governed",
    # Together AI SDK
    "TorkTogetherClient",
    "AsyncTorkTogetherClient",
    "together_governed",
    # Replicate SDK
    "TorkReplicateClient",
    "AsyncTorkReplicateClient",
    "replicate_governed",
    # Hugging Face Transformers
    "TorkHFPipeline",
    "TorkHFModel",
    "TorkHFTokenizer",
    "hf_govern_generate",
    "hf_govern_pipeline",
    "govern_inference",
    "huggingface_governed",
    "HuggingFaceGovernanceResult",
    # n8n AI
    "TorkN8nWebhook",
    "TorkN8nNode",
    "TorkN8nAIChain",
    "AsyncTorkN8nAIChain",
    "n8n_governed",
    "create_n8n_governance_node",
    "N8nGovernanceResult",
    # Mirascope
    "TorkMirascopeCall",
    "mirascope_governed",
    # Magentic
    "TorkMagenticPrompt",
    "magentic_governed",
    # txtai
    "TorkTxtaiEmbeddings",
    "TorkTxtaiPipeline",
    "txtai_governed",
    # ChatDev
    "TorkChatDevPhase",
    "chatdev_governed",
    # CAMEL
    "TorkCamelAgent",
    "TorkCamelRolePlaying",
    "camel_governed",
    # Rebuff
    "TorkRebuff",
    "rebuff_governed",
    # LLM Guard
    "TorkLLMGuard",
    "llm_guard_governed",
    # LocalAI
    "TorkLocalAIClient",
    "localai_governed",
    # LM Studio
    "TorkLMStudioClient",
    "lmstudio_governed",
    # GPT4All
    "TorkGPT4All",
    "gpt4all_governed",
    # PrivateGPT
    "TorkPrivateGPT",
    "privategpt_governed",
    # Tornado
    "TorkTornadoMixin",
    "TorkTornadoMiddleware",
    "tornado_governed",
    # Pyramid
    "TorkPyramidTween",
    "TorkPyramidMiddleware",
    "pyramid_governed",
    # Sanic
    "TorkSanicMiddleware",
    "sanic_governed",
]

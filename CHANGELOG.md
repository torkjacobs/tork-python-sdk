# Changelog

All notable changes to the Tork Governance Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] - 2026-02-02

### Added

#### n8n AI Adapter
- **TorkN8nWebhook** - Governed webhook handler
  - Handle incoming webhook requests with PII governance
  - Configurable text field detection
  - Response governance for outgoing data
  - Receipt tracking for audit

- **TorkN8nNode** - Custom n8n node execution wrapper
  - Execute workflow items with governance
  - Process n8n item json data recursively
  - Output processing with governance
  - Compatible with n8n item structure

- **TorkN8nAIChain** - AI chain processor for LLM operations
  - Chat completions with message governance
  - Completion requests with prompt governance
  - Response processing and governance
  - Model configuration support

- **AsyncTorkN8nAIChain** - Async version of AI chain
  - Async chat and completion methods
  - Async response processing
  - Full governance support

- **n8n_governed** - Decorator for workflow functions
  - Wrap existing n8n functions with governance
  - Automatic n8n items array handling
  - Configurable text fields

- **create_n8n_governance_node** - Generate n8n node definition
  - Ready-to-use n8n node configuration
  - Multiple operation modes (Govern Text, Govern All, Check Only)
  - Configurable governance actions (redact, hash, block)
  - Receipt inclusion option

- **N8nGovernanceResult** - Result container
  - Structured output for n8n workflows
  - JSON serialization support
  - Timestamp and metadata tracking

---

## [0.16.0] - 2026-02-01

### Added

#### NeMo Guardrails Adapter
- **TorkNeMoRails** - Governed NeMo Guardrails wrapper
  - Async generate with input/output governance
  - Sync wrapper for non-async contexts
  - Block-on-PII option for strict enforcement

- **TorkNeMoAction** - Action server integration
  - govern_input/govern_output actions
  - check_pii action for detection without modification
  - Ready for NeMo action server registration

- **tork_input_rail** / **tork_output_rail** - Rail functions
  - Drop-in rail functions for Colang flows
  - Configurable blocking behavior
  - Receipt tracking for audit

- **register_tork_actions** - Register with existing Rails
  - Add Tork governance to any LLMRails instance
  - No config modification required

- **TORK_COLANG_TEMPLATE** - Ready-to-use Colang flows
  - Pre-built flows for input/output governance
  - Sensitive info detection patterns
  - Customizable bot responses

#### Mistral SDK Adapter
- **TorkMistralClient** - Governed sync client
  - Chat completions with PII governance
  - Streaming support via chat_stream
  - Embeddings with input governance

- **AsyncTorkMistralClient** - Governed async client
  - Async chat and embeddings
  - Full governance support

- **mistral_governed** - Decorator for existing code
  - Wrap existing Mistral API calls
  - Configurable input/output governance

#### Groq SDK Adapter
- **TorkGroqClient** - Governed sync client
  - Chat completions with PII governance
  - Streaming support via chat_stream
  - Whisper audio transcription with output governance

- **AsyncTorkGroqClient** - Governed async client
  - Async chat and transcription
  - Full governance support

- **groq_governed** - Decorator for existing code
  - Wrap existing Groq API calls
  - Configurable input/output governance

#### Together AI SDK Adapter
- **TorkTogetherClient** - Governed sync client
  - Chat completions with PII governance
  - Streaming support via chat_stream
  - Legacy completions API support
  - Embeddings with input governance

- **AsyncTorkTogetherClient** - Governed async client
  - Async chat, completions, and embeddings
  - Full governance support

- **together_governed** - Decorator for existing code
  - Wrap existing Together AI API calls
  - Configurable input/output governance

#### Replicate SDK Adapter
- **TorkReplicateClient** - Governed sync client
  - Run predictions with PII governance
  - Streaming support
  - Predictions create/get API

- **AsyncTorkReplicateClient** - Governed async client
  - Async run and stream
  - Full governance support

- **replicate_governed** - Decorator for existing code
  - Wrap existing Replicate API calls
  - Automatic text field detection

---

## [0.15.0] - 2026-02-01

### Added

#### Dify Adapter
- **TorkDifyNode** - Dify workflow node for PII governance
  - Custom node integration for Dify workflows
  - Automatic PII detection and redaction
  - Governance receipts for audit trails
  - Schema export for Dify node registration

- **TorkDifyHook** - Webhook/API hook for Dify
  - Intercepts API calls to/from Dify
  - Governs chat messages, completion requests and responses
  - Request and response governance options

- **TorkDifyApp** - Full Dify application wrapper
  - Wraps entire Dify apps with governance
  - Chat method with input/query governance
  - Receipt tracking for all interactions

- **dify_governed** - Decorator for Dify workflow functions
  - Simple decorator-based governance
  - Configurable input/output governance

---

## [0.14.0] - 2026-02-01

### Added

#### Hugging Face Transformers Adapter
- **TorkHFPipeline** - Governed Hugging Face pipeline wrapper
  - Wraps any HF pipeline (text-generation, summarization, translation, etc.)
  - Automatic PII detection and redaction in inputs and outputs
  - Batch processing support
  - Governance receipts for all operations
  - Streaming support for text generation

- **TorkHFModel** - Governed model wrapper
  - Wraps AutoModel, AutoModelForCausalLM, and other model types
  - Input/output governance for forward pass and generate
  - Tokenizer integration for automatic text governance

- **TorkHFTokenizer** - Governed tokenizer wrapper
  - Wraps AutoTokenizer for encode/decode governance
  - PII detection during encoding/decoding
  - Batch encoding support with governance

- **Convenience Functions**
  - `govern_generate()` - Govern text generation from any model
  - `govern_pipeline()` - Govern any pipeline operation
  - `govern_inference()` - Govern model inference

- **Decorator**
  - `@huggingface_governed` - Add governance to any HF function

### Changed
- Total Python adapters increased from 49 to 50
- Total adapters across all SDKs: 74 (was 73)
- Version bump to 0.14.0

## [0.13.0] - 2026-02-01

### Added

#### New LLM Provider SDK Adapters (6 new)
- **OpenAI SDK adapter** - Direct OpenAI SDK governance
  - `TorkOpenAIClient` - Governed OpenAI client wrapper
  - `govern_chat_completion` / `govern_completion` / `govern_embedding` - Convenience functions
  - Streaming support for chat completions
  - Automatic PII redaction in prompts, responses, function calls
  - Governance receipts attached to all operations

- **Anthropic SDK adapter** - Direct Claude SDK governance
  - `TorkAnthropicClient` - Governed Anthropic client wrapper
  - `govern_message` / `govern_anthropic_completion` - Convenience functions
  - Content block handling for Claude's response format
  - Automatic PII redaction in messages and completions
  - Governance receipts for all API calls

- **Google Gemini adapter** - Google Generative AI governance
  - `TorkGeminiClient` - Governed Gemini client wrapper
  - `TorkGeminiChat` - Governed chat session
  - `govern_generate_content` / `govern_gemini_chat` / `govern_gemini_embedding` - Convenience functions
  - Multi-modal content support (text, images)
  - Automatic PII redaction in prompts and responses

- **AWS Bedrock adapter** - Amazon Bedrock governance
  - `TorkBedrockClient` - Governed Bedrock client wrapper
  - `govern_invoke_model` / `govern_converse` - Convenience functions
  - Model-specific body handling (Claude, Titan, Llama)
  - Automatic PII redaction in request/response bodies
  - Governance receipts for all invocations

- **Azure OpenAI adapter** - Azure OpenAI Service governance
  - `TorkAzureOpenAIClient` - Governed Azure OpenAI client wrapper
  - `govern_azure_chat_completion` / `govern_azure_completion` / `govern_azure_embedding` - Convenience functions
  - Deployment name support
  - Streaming support for chat completions
  - Automatic PII redaction in prompts and responses

- **Cohere SDK adapter** - Cohere API governance
  - `TorkCohereClient` - Governed Cohere client wrapper
  - `govern_cohere_chat` / `govern_cohere_generate` / `govern_cohere_embed` / `govern_cohere_rerank` - Convenience functions
  - Support for chat, generate, embed, rerank, and classify operations
  - Automatic PII redaction in messages, documents, texts
  - Governance receipts for all operations

### Changed
- Total Python adapters increased from 43 to 49
- Total adapters across all SDKs: 73 (was 67)
- Version bump to 0.13.0

## [0.12.0] - 2026-02-01

### Added

#### New LLM Observability Adapters (4 new)
- **Phoenix adapter** - Arize Phoenix open-source LLM observability governance
  - `TorkPhoenixClient` - Governed client wrapper
  - `govern_log_traces` / `govern_log_spans` - Trace and span governance
  - Automatic PII redaction in inputs, outputs, metadata, attributes
  - Governance receipts for all operations

- **Portkey adapter** - Portkey AI gateway governance
  - `TorkPortkeyClient` - Governed client wrapper
  - `govern_completion` / `govern_log` - Completion and logging governance
  - Support for virtual keys and caching
  - Automatic PII redaction in prompts, responses
  - Governance receipts attached to requests

- **PromptLayer adapter** - PromptLayer prompt management governance
  - `TorkPromptLayerClient` - Governed client wrapper
  - `govern_log_request` / `govern_track_prompt` - Request and prompt tracking
  - Automatic PII detection in prompts, responses, tags, metadata
  - Governance receipts for all logging operations

- **Humanloop adapter** - Humanloop prompt optimization governance
  - `TorkHumanloopClient` - Governed client wrapper
  - `govern_log` / `govern_feedback` - Logging and feedback governance
  - Automatic PII redaction in prompts, completions, feedback
  - Governance receipts for all operations

### Changed
- Total Python adapters increased from 39 to 43
- Total adapters across all SDKs: 67 (was 63)
- Version bump to 0.12.0

## [0.11.0] - 2026-02-01

### Added

#### New Observability/Monitoring Adapters (4 new)
- **Helicone adapter** - Helicone LLM observability governance
  - `TorkHeliconeClient` - Governed client wrapper
  - `govern_log_request` / `govern_log_response` - Request/response logging
  - Automatic PII redaction in prompts, completions, metadata
  - OpenAI proxy mode support
  - Governance receipts attached to logs

- **Weights & Biases adapter** - W&B experiment tracking governance
  - `TorkWandbRun` - Governed run wrapper
  - `TorkWandbCallback` - LangChain callback handler
  - `govern_log` / `govern_table` - Metric and table logging
  - Automatic PII detection in experiment data, configs, artifacts
  - Governance receipts for all logging operations

- **Arize adapter** - Arize ML observability governance
  - `TorkArizeClient` - Governed client wrapper
  - `govern_log_prediction` / `govern_log_embedding` - Prediction logging
  - Automatic PII detection in features, predictions, tags
  - Batch logging support with governance

- **Langfuse adapter** - Langfuse LLM analytics governance
  - `TorkLangfuseClient` - Governed client wrapper
  - `TorkLangfuseCallback` - LangChain callback handler
  - `govern_trace` / `govern_generation` / `govern_score` - Trace operations
  - Automatic PII redaction in inputs, outputs, metadata
  - Governance receipts attached to traces

### Changed
- Total Python adapters increased from 35 to 39
- Total adapters across all SDKs: 63 (was 59)
- Version bump to 0.11.0

## [0.10.0] - 2026-02-01

### Added

#### New Vector DB Adapters (3 new)
- **Weaviate adapter** - Weaviate vector database governance
  - `TorkWeaviateClient` - Governed client wrapper
  - `TorkWeaviateCollection` - Governed collection operations
  - `govern_add` / `govern_query` / `govern_batch` - Convenience functions
  - Automatic PII detection in document content and metadata
  - Sync and async support

- **Qdrant adapter** - Qdrant vector database governance
  - `TorkQdrantClient` - Governed client wrapper
  - `govern_upsert` / `govern_search` / `govern_scroll` - Convenience functions
  - Automatic PII detection in payloads
  - Batch operations with governance

- **Milvus adapter** - Milvus vector database governance
  - `TorkMilvusClient` - Governed client wrapper
  - `TorkMilvusCollection` - Governed collection operations
  - `govern_insert` / `govern_search` / `govern_query` - Convenience functions
  - Automatic PII detection in fields

#### New Observability Adapter (1 new)
- **LangSmith adapter** - LangSmith tracing governance
  - `TorkLangSmithClient` - Governed client wrapper
  - `TorkTracerCallback` - LangChain callback for governed traces
  - `govern_log_run` / `govern_feedback` - Convenience functions
  - Automatic PII redaction in traces, inputs, outputs
  - Governance receipts attached to traces

### Changed
- Total Python adapters increased from 31 to 35
- Total adapters across all SDKs: 59 (was 55)
- Version bump to 0.10.0

## [0.9.0] - 2026-02-01

### Added
- All SDK documentation synced across Python, JavaScript, Ruby, Go, Rust, and Java
- 55 total framework adapters across all SDKs:
  - **Python SDK**: 31 AI framework adapters (LangChain, CrewAI, AutoGen, OpenAI, LiteLLM, Ollama, vLLM, ChromaDB, Pinecone, and more)
  - **JavaScript SDK**: 8 adapters (Express, Fastify, Koa, Hono, Hapi, Next.js, LangChain.js, NestJS)
  - **Ruby SDK**: 2 adapters (Rails, Grape)
  - **Go SDK**: 4 adapters (Gin, Echo, Fiber, Chi)
  - **Rust SDK**: 3 adapters (Actix-web, Axum, Rocket)
  - **Java SDK**: 3 adapters (Spring Boot, Quarkus, Micronaut)

### Changed
- Version bump to 0.9.0 (approaching stable 1.0 release)
- Production-ready status for all adapters

## [0.3.0] - 2026-01-31

### Added

#### New AI Framework Adapters (9 new)
- **LiteLLM adapter** - Unified interface for 100+ LLMs with governance
  - `TorkLiteLLMCallback` - Callback handler for completion calls
  - `TorkLiteLLMProxy` - Governed client wrapper
  - `govern_completion` / `agovern_completion` - Convenience functions
  - Streaming support

- **NeMo Guardrails adapter** - NVIDIA guardrails integration
  - `TorkNeMoAction` - Custom action for Colang flows
  - `TorkRailsConfig` - Wrapper for RailsConfig
  - `TorkNeMoMiddleware` - Middleware for LLMRails
  - Colang flow definitions included

- **Ollama adapter** - Local LLM governance
  - `TorkOllamaClient` - Governed sync client
  - `AsyncTorkOllamaClient` - Governed async client
  - `govern_generate` / `govern_chat` - Convenience functions
  - Streaming support for generate and chat

- **vLLM adapter** - High-throughput LLM serving governance
  - `TorkVLLMEngine` - Governed vLLM wrapper
  - `AsyncTorkVLLMEngine` - Async engine support
  - `TorkSamplingParams` - Sampling params with governance options
  - Batch generation support

- **ChromaDB adapter** - Vector database governance
  - `TorkChromaClient` - Governed client wrapper
  - `TorkChromaCollection` - Governed collection
  - `govern_add` / `govern_query` - Convenience functions
  - Document and metadata governance

- **Pinecone adapter** - Managed vector database governance
  - `TorkPineconeIndex` - Governed index wrapper
  - `TorkPineconeClient` - Governed client
  - `govern_upsert` / `govern_query` - Convenience functions
  - Configurable text metadata key detection

- **Guardrails AI adapter** - Validator integration (already existed, now documented)
  - `TorkValidator` - Guardrails AI validator
  - `TorkGuard` - Wrapped guard with governance
  - `TorkRail` - Custom Rail specification

- **Dify adapter** - Workflow governance (already existed, now documented)
  - `TorkDifyNode` - Workflow node for Dify
  - `TorkDifyHook` - API hook integration
  - `TorkDifyApp` - Full app wrapper

### Changed
- Total AI adapters increased from 27 to 31
- Improved async support across all adapters
- Enhanced receipt tracking with `receipts` property on all adapters
- Version bump to 0.3.0

## [0.2.0] - 2026-01-31

### Added
- **Comprehensive Test Suite** - 937 tests total (786 PII/compliance + 151 core/adapter tests)
- **Core Module Tests** (67 tests)
  - PIIType and GovernanceAction enum tests
  - Dataclass tests (PIIMatch, PIIResult, Receipt, GovernanceResult, TorkConfig)
  - Utility function tests (detect_pii, redact_pii, hash_text, generate_receipt_id)
  - Tork class comprehensive tests (govern, get_stats, reset_stats)
  - Edge case and error handling tests
- **Adapter Tests** (84 tests)
  - Import and instantiation tests for all 27 framework adapters
  - LangChain, CrewAI, AutoGen, OpenAI Agents SDK
  - FastAPI, Django, Flask, Starlette
  - MCP (Model Context Protocol)
  - LlamaIndex, Semantic Kernel, Haystack
  - Pydantic AI, DSPy, Instructor, Guidance, LMQL, Outlines, Marvin
  - SuperAGI, MetaGPT, BabyAGI, AgentGPT
  - Flowise, Langflow, Guardrails AI, Dify
- **GitHub Actions CI/CD Workflow**
  - Multi-Python version testing (3.10, 3.11, 3.12)
  - Code coverage reporting with Codecov
  - Compliance matrix validation gates
  - Test summary in GitHub Actions

### Changed
- **Code Coverage Improvement**
  - `pii_patterns.py`: 90% coverage
  - `core.py`: 100% coverage (up from 55%)

### Fixed
- Custom pattern detection now properly accessible via `result.pii.redacted_text`

## [0.1.0] - 2026-01-15

### Added
- Initial release of Tork Governance Python SDK
- Core governance functionality with `Tork` class
- PII detection for 50+ patterns across 7 regions
- PII redaction with configurable replacement tokens
- Cryptographic receipts with SHA256 hashing
- Support for 8 compliance frameworks:
  - GDPR, HIPAA, PCI-DSS, SOC 2
  - CCPA/CPRA, FERPA, GLBA, COPPA
- 27 framework adapters for seamless integration
- Zero external dependencies for core functionality
- On-device processing (no data leaves your infrastructure)

### Framework Adapters
- **AI Agent Frameworks**: LangChain, CrewAI, AutoGen, OpenAI Agents SDK
- **Web Frameworks**: FastAPI, Django, Flask, Starlette
- **LLM Tools**: LlamaIndex, Semantic Kernel, Haystack
- **Structured Output**: Pydantic AI, DSPy, Instructor, Guidance, LMQL, Outlines, Marvin
- **Agent Orchestration**: SuperAGI, MetaGPT, BabyAGI, AgentGPT
- **Visual Builders**: Flowise, Langflow
- **Other**: MCP, Guardrails AI, Dify

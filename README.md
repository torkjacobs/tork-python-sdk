# Tork Governance Python SDK

On-device AI governance with PII detection, redaction, and cryptographic receipts.

[![PyPI version](https://badge.fury.io/py/tork-governance.svg)](https://badge.fury.io/py/tork-governance)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install tork-governance
```

With optional framework support:

```bash
pip install tork-governance[langchain]
pip install tork-governance[fastapi]
pip install tork-governance[all]
```

## Quick Start

```python
from tork_governance import Tork

tork = Tork()

# Detect and redact PII
result = tork.govern("My SSN is 123-45-6789 and email is john@example.com")

print(result.output)  # "My SSN is [SSN_REDACTED] and email is [EMAIL_REDACTED]"
print(result.pii.types)  # ['ssn', 'email']
print(result.receipt.receipt_id)  # Cryptographic receipt ID
```

## Supported AI Frameworks (53 Adapters)

### LLM Provider SDKs
- **OpenAI SDK** - Direct OpenAI API governance with streaming
- **Anthropic SDK** - Claude API governance
- **Google Gemini** - Gemini API with multi-modal support
- **AWS Bedrock** - Bedrock with Claude, Titan, Llama support
- **Azure OpenAI** - Azure OpenAI Service governance
- **Cohere SDK** - Chat, embed, rerank, classify governance
- **Mistral SDK** - Mistral AI chat and embeddings governance
- **Groq SDK** - Groq LPU chat and audio transcription governance
- **Together AI SDK** - Together AI chat, completions, and embeddings governance
- **Replicate SDK** - Replicate model run and predictions governance

### LLM Orchestration
- **LangChain** - Chain and agent governance
- **LlamaIndex** - Query engine and retriever governance
- **Semantic Kernel** - Microsoft SK filters and plugins
- **Haystack** - Pipeline and document processor governance
- **LiteLLM** - Unified interface for 100+ LLMs
- **vLLM** - High-throughput LLM serving
- **Ollama** - Local LLM governance

### Agent Frameworks
- **CrewAI** - Multi-agent crew governance
- **AutoGen** - Microsoft AutoGen agent governance
- **OpenAI Agents SDK** - Function calling governance
- **SuperAGI** - Autonomous agent governance
- **MetaGPT** - Multi-agent role governance
- **BabyAGI** - Task-driven agent governance
- **AgentGPT** - Goal-oriented agent governance

### Structured Output & Guardrails
- **Pydantic AI** - Type-safe AI with governance
- **Instructor** - Structured outputs governance
- **DSPy** - Stanford DSPy module governance
- **Guidance** - Microsoft Guidance governance
- **LMQL** - Query language governance
- **Outlines** - Structured generation governance
- **Marvin** - AI function governance
- **Guardrails AI** - Validator integration
- **NeMo Guardrails** - NVIDIA Colang integration

### Visual Builders & Platforms
- **Flowise** - Visual workflow governance
- **Langflow** - Visual LangChain governance
- **Dify** - Low-code AI platform governance

### Vector Databases
- **ChromaDB** - AI-native vector DB governance
- **Pinecone** - Managed vector DB governance
- **Weaviate** - Vector search governance
- **Qdrant** - Vector similarity governance
- **Milvus** - Scalable vector DB governance

### LLM Observability
- **LangSmith** - LangChain tracing governance
- **Langfuse** - LLM analytics governance
- **Phoenix** - Arize Phoenix observability
- **Helicone** - LLM monitoring governance
- **Weights & Biases** - Experiment tracking governance
- **Arize** - ML observability governance
- **Portkey** - AI gateway governance
- **PromptLayer** - Prompt management governance
- **Humanloop** - Prompt optimization governance

### Protocols
- **MCP** - Model Context Protocol governance

### Web Frameworks
- **FastAPI** - Middleware and dependency injection
- **Django** - Middleware integration
- **Flask** - Extension and decorator support
- **Starlette** - ASGI middleware

## Framework Examples

### LiteLLM - Unified LLM Interface

```python
from tork_governance.adapters.litellm import TorkLiteLLMProxy, govern_completion

# Option 1: Governed proxy client
proxy = TorkLiteLLMProxy()
response = proxy.completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
)

# Option 2: One-off governed completion
response = govern_completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "My email is john@example.com"}]
)
```

### Ollama - Local LLM Governance

```python
from tork_governance.adapters.ollama import TorkOllamaClient, govern_generate

# Governed Ollama client
client = TorkOllamaClient()
response = client.generate(
    model="llama2",
    prompt="My phone number is 555-123-4567"
)
print(response["response"])  # PII redacted

# Chat with governance
response = client.chat(
    model="llama2",
    messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
)
```

### ChromaDB - Vector Database Governance

```python
from tork_governance.adapters.chromadb import TorkChromaClient

# Governed ChromaDB client
client = TorkChromaClient()
collection = client.get_or_create_collection("my_docs")

# Documents are governed before storage
collection.add(
    documents=["User John has SSN 123-45-6789"],
    ids=["doc1"]
)

# Query results are governed before returning
results = collection.query(query_texts=["Find user data"])
```

### LangChain Integration

```python
from langchain.llms import OpenAI
from tork_governance.adapters.langchain import TorkCallbackHandler

llm = OpenAI(callbacks=[TorkCallbackHandler()])
response = llm("My credit card is 4111-1111-1111-1111")
# PII automatically redacted in prompts and responses
```

### FastAPI Middleware

```python
from fastapi import FastAPI
from tork_governance.adapters.fastapi import TorkFastAPIMiddleware

app = FastAPI()
app.add_middleware(TorkFastAPIMiddleware)

@app.post("/chat")
async def chat(message: str):
    # Request body is automatically governed
    return {"response": message}
```

## PII Detection

Detects 50+ PII types across multiple regions:

| Category | Types |
|----------|-------|
| **US** | SSN, EIN, ITIN, Passport, Driver's License, Phone |
| **Australia** | TFN, ABN, ACN, Medicare, Driver's License |
| **EU/UK** | NINO, NHS, IBAN, VAT, National ID |
| **Financial** | Credit Card, Bank Account, SWIFT/BIC |
| **Healthcare** | MRN, NPI, DEA, ICD-10 codes |
| **Universal** | Email, IP Address, URL, DOB, Phone |

## Compliance Support

- **GDPR** - EU data protection
- **HIPAA** - Healthcare (18 PHI identifiers)
- **PCI-DSS** - Payment card data
- **SOC 2** - Security controls
- **CCPA/CPRA** - California privacy
- **FERPA** - Education records
- **GLBA** - Financial privacy
- **COPPA** - Children's privacy

## Cryptographic Receipts

Every governance action generates a verifiable receipt:

```python
result = tork.govern("Sensitive data here")

receipt = result.receipt
print(receipt.receipt_id)    # Unique identifier
print(receipt.timestamp)     # ISO 8601 timestamp
print(receipt.input_hash)    # SHA-256 of input
print(receipt.output_hash)   # SHA-256 of output
print(receipt.policy_version)  # Applied policy version
```

## Configuration

```python
from tork_governance import Tork, TorkConfig

tork = Tork(
    config=TorkConfig(
        policy_version="1.0.0",
        default_action="redact",  # or "allow", "deny"
        custom_patterns={
            "employee_id": r"EMP-\d{6}"
        }
    )
)
```

## Documentation

- [Full Documentation](https://docs.tork.network)
- [API Reference](https://docs.tork.network/api)
- [Framework Guides](https://docs.tork.network/frameworks)

## License

MIT License - see [LICENSE](LICENSE) for details.

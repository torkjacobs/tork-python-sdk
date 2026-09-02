# Tork Governance Python SDK

On-device AI governance with PII detection, redaction, and local audit receipts.

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
print(result.receipt.receipt_id)  # Locally-generated receipt ID
```

## Regional PII Detection (v1.1)

Activate country-specific and industry-specific PII patterns with the optional `region` and `industry` parameters:

```python
from tork_governance import Tork

tork = Tork()

# UAE regional detection — Emirates ID, +971 phone, PO Box
result = tork.govern(
    "Emirates ID: 784-1234-1234567-1",
    region=["ae"]
)

# Multi-region + industry
result = tork.govern(
    "Aadhaar: 1234 5678 9012, ICD-10: J45.20",
    region=["in"],
    industry="healthcare"
)

# Available regions: AU, US, GB, EU, AE, SA, NG, IN, JP, CN, KR, BR
# Available industries: healthcare, finance, legal
```

## Supported AI Frameworks (67 Adapters)

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
- **LocalAI** - Local OpenAI-compatible LLM governance
- **LM Studio** - LM Studio local inference governance
- **GPT4All** - GPT4All local LLM governance
- **PrivateGPT** - PrivateGPT private document AI governance

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
- **Rebuff** - Prompt injection detection with governance
- **LLM Guard** - Input/output scanning with governance

### AI Development Frameworks
- **Mirascope** - Decorator-based LLM call governance
- **Magentic** - @prompt decorator governance
- **txtai** - Embeddings and pipeline governance
- **ChatDev** - Multi-agent software development governance
- **CAMEL** - Multi-agent role-playing governance

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
- **Tornado** - RequestHandler mixin and middleware
- **Pyramid** - Tween and middleware governance
- **Sanic** - Async request/response middleware

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

`Tork.govern()` and `Tork.scan_tool_result()` run one of two on-device PII detectors,
chosen by `TorkConfig.detector`, the `Tork(detector=...)` constructor kwarg, or the
`TORK_PII_DETECTOR` environment variable (constructor kwarg wins, then the env var,
then the default):

| `detector` | Default? | Type vocabulary | Checksum validation |
|---|---|---|---|
| `"regional"` | **Yes** | 42 types across US/AU/EU/UK + universal/financial/healthcare/biometric (`tork_governance.detectors.pii_patterns`) | Yes, on the types that have one (SSN, credit card, IBAN, TFN, NHS, ABN, Medicare, NINO, routing number, NPI, DEA) — a lookalike that fails its checksum is not flagged |
| `"basic"` | No — opt in | 10 types: `ssn`, `credit_card`, `email`, `phone`, `address`, `ip_address`, `date_of_birth`, `passport`, `drivers_license`, `bank_account` | No |

```python
from tork_governance import Tork

# Default: the wider, checksum-validated regional detector
tork = Tork()
result = tork.govern("IBAN: DE89370400440532013000")
print(result.pii.types)  # ['iban']

# Opt back into the original 10-type detector
basic_tork = Tork(detector="basic")
# ...or: TorkConfig(detector="basic"), or `TORK_PII_DETECTOR=basic` in the environment
```

**Wider vocabulary than the JS SDK.** `@torknetwork/sdk` (JS) implements only the 10
basic types above — it has no regional detector. A Python `govern()`/`scan_tool_result()`
result's `pii.types` (or `tool_result_scan` receipt block finding types) may therefore
contain labels with no JS-SDK equivalent, e.g. `"iban"`, `"tfn"`, `"nhs_uk"`. Don't
assume the two SDKs' outputs are directly comparable without accounting for this —
use `detector="basic"` (or `TORK_PII_DETECTOR=basic`) on the Python side to match the
JS SDK's exact 10-type vocabulary and behavior byte-for-byte.

Full list of regional types by category, generated from
`PIIDetector(regions=['all']).get_supported_types()`:

| Category | Types |
|----------|-------|
| **US** (6) | `driver_license_us`, `ein`, `itin`, `passport_us`, `phone_us`, `ssn` |
| **Australia** (5) | `abn`, `acn`, `medicare_au`, `phone_au`, `tfn` |
| **EU** (5) | `french_ssn`, `german_id`, `iban`, `phone_eu`, `vat_eu` |
| **UK** (4) | `nhs_uk`, `nino_uk`, `postcode_uk`, `sort_code_uk` |
| **Universal** (6) | `credit_card`, `date_of_birth`, `email`, `ip_address`, `ipv6_address`, `mac_address` |
| **Financial** (6) | `bank_account`, `card_expiry`, `crypto_address`, `cvv`, `routing_number`, `swift_bic` |
| **Healthcare** (7) | `cpt_code`, `dea_number`, `health_plan_id`, `icd_code`, `mrn`, `npi`, `patient_id` |
| **Biometric** (3) | `biometric_id`, `face_id`, `fingerprint_id` |

## Compliance Support

- **GDPR** - EU data protection
- **HIPAA** - Healthcare (18 PHI identifiers)
- **PCI-DSS** - Payment card data
- **SOC 2** - Security controls
- **CCPA/CPRA** - California privacy
- **FERPA** - Education records
- **GLBA** - Financial privacy
- **COPPA** - Children's privacy

## Receipts & Attestation

Every `govern()` call **locally mints** a receipt, entirely on-device. This happens
every time, regardless of network access, and doesn't depend on whether a server was
ever reached:

```python
result = tork.govern("Sensitive data here")

receipt = result.receipt
print(receipt.receipt_id)    # Locally-generated identifier
print(receipt.timestamp)     # ISO 8601 timestamp
print(receipt.input_hash)    # SHA-256 of input
print(receipt.output_hash)   # SHA-256 of output
print(receipt.policy_version)  # Applied policy version
```

If you supply an `api_key` (via `Tork(api_key=...)` or `TorkConfig`), `govern()`
additionally attempts to report the decision to tork.network as a separate **server
attestation**. This is optional, asynchronous, and best-effort:

- It runs on a background thread — `govern()` never blocks on it.
- The network call (and its one retry) can fail; nothing about the local decision
  above is affected either way.
- Check `result.report.attempted` and `.succeeded` before treating a decision as
  anchored on the server — don't assume success just because reporting was attempted.
- On success, `result.report.receipt_id` is the **server's** receipt ID, a different
  value from the local `receipt.receipt_id` above.

```python
report = result.report
print(report.attempted)   # Whether reporting was attempted (api_key configured)
print(report.succeeded)   # Whether the server actually persisted the attestation
print(report.receipt_id)  # Server-side receipt ID, only set once succeeded
print(report.reason)      # Why it hasn't succeeded (or its current status)

# Block until the background attempt settles, if you need the confirmed
# outcome before proceeding — most callers don't need this.
report.wait(timeout=5)
```

## Scanning tool results

A tool result returned by an MCP server — or any external system you do not control — is untrusted input that is about to be appended to a model's context. `Tork.scan_tool_result()` scans it first, on-device, for PII and prompt injection:

```python
from tork_governance import Tork

tork = Tork()
outcome = tork.scan_tool_result(
    "lookup_customer",
    tool_result,                       # whatever the server returned
    "mcp://crm.internal/customers",
    block_on_injection=True,
)

if outcome.blocked:
    print(outcome.reason)              # do not append anything
else:
    append_to_context(outcome.sanitized)  # PII masked in place

outcome.findings
# [ToolResultFinding(kind='pii', type='email', count=1, location='$.content[0].text'),
#  ToolResultFinding(kind='injection', type='heuristic:instruction_override', count=1, location='$.content[0].text')]
```

There is also a standalone `scan_tool_result(tool_name, payload, server_uri=None, **options)` function with the same signature (minus the receipt) that returns an object with `sanitized`, `findings`, `blocked`, and `reason`, and produces no receipt.

- **PII uses the same on-device detector as `govern()`** — same patterns, same redaction labels. Matches are masked in place; the payload structure is otherwise unchanged, and a clean payload comes back untouched (same object identity, not just equal).
- **Injection detection is heuristic.** A conservative pattern set (`tork-injection-heuristics-v1`) covering instruction-override phrases, role reassignment, and exfiltration URLs. Every injection finding is typed `heuristic:<name>` because that is exactly what it is: a regex match over untrusted text, with false positives and false negatives, not a verified determination. Without `block_on_injection`, matches are reported and the result is still returned; with it, `sanitized` is `None` so no masked copy can be appended by accident.
- **Zero network calls.** The scan is pure and synchronous. The payload never leaves the machine, whether or not an `api_key` is configured.
- **Recorded on the receipt as counts only.** `receipt.tool_result_scan` carries `attested_by: 'client'`, `capture_mode: 'edge'`, the tool name and server URI, counts by kind and type, the blocked flag, and the SDK version. It never carries the payload, a matched value, or a location path.

**This is a client-side, client-attested control.** The scan runs in your process, and the receipt says so: Tork did not execute it and cannot verify it ran at all — the same honest boundary as every other edge attestation this SDK produces. **Gateway-side enforcement, where a caller cannot skip the scan, is a separate and later control.** Do not read a `tool_result_scan` block as proof that every tool result reaching a model was scanned; read it as a record of the scans a caller chose to run and report.

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

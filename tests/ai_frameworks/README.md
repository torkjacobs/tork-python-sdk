# AI Framework Adapter Tests

Comprehensive test suite for Tork Governance AI framework adapters.

## Overview

This test suite validates governance functionality across 21 AI frameworks, ensuring consistent PII detection, redaction, and compliance receipt generation.

## Frameworks Tested

| # | Framework | Adapter Module | Test File | Tests |
|---|-----------|----------------|-----------|-------|
| 1 | LangChain | `langchain.py` | `test_langchain_adapter.py` | 39 |
| 2 | CrewAI | `crewai.py` | `test_crewai_adapter.py` | 39 |
| 3 | AutoGen | `autogen.py` | `test_autogen_adapter.py` | 39 |
| 4 | OpenAI Agents | `openai_agents.py` | `test_openai_agents_adapter.py` | 39 |
| 5 | MCP | `mcp.py` | `test_mcp_adapter.py` | 39 |
| 6 | LlamaIndex | `llamaindex.py` | `test_llamaindex_adapter.py` | 39 |
| 7 | Semantic Kernel | `semantic_kernel.py` | `test_semantic_kernel_adapter.py` | 39 |
| 8 | Haystack | `haystack.py` | `test_haystack_adapter.py` | 41 |
| 9 | Pydantic AI | `pydantic_ai.py` | `test_pydantic_ai_adapter.py` | 41 |
| 10 | DSPy | `dspy.py` | `test_dspy_adapter.py` | 41 |
| 11 | Instructor | `instructor.py` | `test_instructor_adapter.py` | 39 |
| 12 | Guidance | `guidance.py` | `test_guidance_adapter.py` | 48 |
| 13 | LMQL | `lmql.py` | `test_lmql_adapter.py` | 48 |
| 14 | Outlines | `outlines.py` | `test_outlines_adapter.py` | 48 |
| 15 | Marvin | `marvin.py` | `test_marvin_adapter.py` | 36 |
| 16 | SuperAGI | `superagi.py` | `test_superagi_adapter.py` | 35 |
| 17 | MetaGPT | `metagpt.py` | `test_metagpt_adapter.py` | 31 |
| 18 | BabyAGI | `babyagi.py` | `test_babyagi_adapter.py` | 31 |
| 19 | AgentGPT | `agentgpt.py` | `test_agentgpt_adapter.py` | 31 |
| 20 | Flowise | `flowise.py` | `test_flowise_adapter.py` | 35 |
| 21 | Langflow | `langflow.py` | `test_langflow_adapter.py` | 34 |

**Total: 812 tests across 21 frameworks**

## Test Categories

Each adapter test file covers these standard categories:

### 1. Import/Instantiation
- Verify adapter classes can be imported
- Test default instantiation
- Validate initial state (empty receipts, etc.)

### 2. Configuration
- Test with existing Tork instance
- Test with API key configuration
- Validate proper instance sharing

### 3. PII Detection & Redaction
- **Email**: `user@example.com` -> `[EMAIL_REDACTED]`
- **Phone**: `(555) 123-4567` -> `[PHONE_REDACTED]`
- **SSN**: `123-45-6789` -> `[SSN_REDACTED]`
- **Credit Card**: `4111111111111111` -> `[CARD_REDACTED]`
- Clean text passes through unchanged

### 4. Error Handling
- Empty string handling
- Whitespace-only input
- Edge cases specific to each framework

### 5. Compliance Receipts
- Receipt generation on operations
- Receipt type validation
- Receipt ID presence
- `get_receipts()` method validation

### 6. Framework-Specific Tests
Each framework has additional tests for its unique features:
- LangChain: Chain, Agent, Tool, Callback governance
- CrewAI: Crew, Agent, Task, Tool governance
- AutoGen: Agent, Group Chat, Tool governance
- OpenAI Agents: Runner, Tool, Handoff governance
- MCP: Tool, Resource, Prompt, Server governance
- And more...

## Running Tests

### Run All AI Framework Tests
```bash
pytest tests/ai_frameworks/ -v
```

### Run Specific Framework Tests
```bash
pytest tests/ai_frameworks/test_langchain_adapter.py -v
pytest tests/ai_frameworks/test_crewai_adapter.py -v
```

### Run with Coverage
```bash
pytest tests/ai_frameworks/ --cov=tork_governance.adapters --cov-report=html
```

### Run PII Detection Tests Only
```bash
pytest tests/ai_frameworks/ -v -k "PIIDetection"
```

### Run Configuration Tests Only
```bash
pytest tests/ai_frameworks/ -v -k "Configuration"
```

## Test Data

All tests use shared test data from `test_data.py`:

```python
PII_SAMPLES = {
    "email": "user@example.com",
    "phone_us": "(555) 123-4567",
    "ssn": "123-45-6789",
    "credit_card": "4111111111111111"
}

PII_MESSAGES = {
    "email_message": "Contact me at user@example.com",
    "phone_message": "Call (555) 123-4567",
    "ssn_message": "My SSN is 123-45-6789",
    "credit_card_message": "Card: 4111111111111111"
}
```

## Fixtures

Common fixtures are defined in `conftest.py`:

- `tork_instance`: Pre-configured Tork instance for testing
- Other framework-specific fixtures as needed

## Adding New Framework Tests

1. Create `test_{framework}_adapter.py`
2. Import from `tork_governance.adapters.{framework}`
3. Import `PII_SAMPLES` and `PII_MESSAGES` from `.test_data`
4. Implement standard test categories
5. Add framework-specific tests
6. Update this README

## Test Standards

- Use `assert len(receipts) >= N` for receipt counts (adapters may generate input + output receipts)
- Use `[CARD_REDACTED]` not `[CREDIT_CARD_REDACTED]`
- Mock objects with `__init__` for instance attributes
- Use `@pytest.mark.asyncio` for async tests
- Keep tests focused and independent

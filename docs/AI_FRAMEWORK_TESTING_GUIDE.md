# AI Framework Testing Guide

Comprehensive guide to testing Tork Governance across 21 AI frameworks.

## Table of Contents

1. [Overview](#overview)
2. [Test Categories Explained](#test-categories-explained)
3. [PII Test Data Used](#pii-test-data-used)
4. [How to Run Tests](#how-to-run-tests)
5. [How to Replicate a Test](#how-to-replicate-a-test)
6. [Adding Tests for New Frameworks](#adding-tests-for-new-frameworks)
7. [Framework Coverage Table](#framework-coverage-table)
8. [CI/CD Integration](#cicd-integration)

---

## Overview

### What the Test Suite Covers

The Tork Governance AI Framework Test Suite provides comprehensive validation of governance functionality across 21 major AI and LLM frameworks. Each adapter is tested to ensure:

- **PII Detection**: Automatically identifies sensitive data (emails, phone numbers, SSNs, credit cards)
- **PII Redaction**: Replaces detected PII with standardized redaction tokens
- **Compliance Receipts**: Generates audit-ready receipts for every governance action
- **Error Handling**: Gracefully handles edge cases and malformed inputs
- **Framework Integration**: Works seamlessly with each framework's unique patterns

### Why Comprehensive Testing Matters for Governance

Governance in AI systems is critical because:

1. **Data Privacy Compliance**: GDPR, CCPA, HIPAA require PII protection
2. **Audit Requirements**: Organizations need proof of governance actions
3. **Consistency**: Same governance rules must apply across all AI frameworks
4. **Trust**: Users and regulators need confidence in AI system behavior

### Total Coverage

| Metric | Value |
|--------|-------|
| Total Frameworks | 21 |
| Total Tests | 812 |
| Pass Rate | 100% |
| Test Categories | 10 |

---

## Test Categories Explained

### 1. Import/Instantiation Tests

**What it tests**: Verifies that adapter classes can be imported and instantiated without errors.

**Why it matters**: Ensures the adapter module is properly structured and all dependencies are correctly configured.

```python
def test_import_agent(self):
    """Test TorkLangChainAgent can be imported."""
    from tork_governance.adapters.langchain import TorkLangChainAgent
    assert TorkLangChainAgent is not None

def test_instantiate_agent_default(self):
    """Test agent instantiation with defaults."""
    agent = TorkLangChainAgent()
    assert agent is not None
    assert agent.tork is not None
    assert agent.receipts == []
```

### 2. Configuration Tests

**What it tests**: Validates that adapters can be configured with existing Tork instances or API keys.

**Why it matters**: Production environments often share a single Tork instance across multiple adapters for consistent policy enforcement.

```python
def test_agent_with_tork_instance(self, tork_instance):
    """Test agent with existing Tork instance."""
    agent = TorkLangChainAgent(tork=tork_instance)
    assert agent.tork is tork_instance

def test_agent_with_api_key(self):
    """Test agent with API key."""
    agent = TorkLangChainAgent(api_key="test-key")
    assert agent.tork is not None
```

### 3. PII Detection Tests

**What it tests**: Verifies that each type of PII is correctly detected and redacted.

**Why it matters**: Different PII types require different detection patterns. Missing even one type creates compliance gaps.

```python
def test_govern_email_pii(self):
    """Test email PII is detected and redacted."""
    agent = TorkLangChainAgent()
    result = agent.govern("Contact me at john.doe@example.com")
    assert "john.doe@example.com" not in result
    assert "[EMAIL_REDACTED]" in result

def test_govern_ssn_pii(self):
    """Test SSN PII is detected and redacted."""
    agent = TorkLangChainAgent()
    result = agent.govern("My SSN is 123-45-6789")
    assert "123-45-6789" not in result
    assert "[SSN_REDACTED]" in result
```

### 4. Error Handling Tests

**What it tests**: Ensures adapters gracefully handle edge cases like empty strings, whitespace, and unusual inputs.

**Why it matters**: Real-world inputs are unpredictable. Robust error handling prevents crashes and data leaks.

```python
def test_agent_empty_string(self):
    """Test agent handles empty string."""
    agent = TorkLangChainAgent()
    result = agent.govern("")
    assert result == ""

def test_agent_whitespace(self):
    """Test agent handles whitespace."""
    agent = TorkLangChainAgent()
    result = agent.govern("   ")
    assert result == "   "
```

### 5. Compliance Receipt Tests

**What it tests**: Validates that governance actions generate proper audit receipts with required fields.

**Why it matters**: Receipts provide the audit trail required for compliance reporting and incident investigation.

```python
def test_agent_invoke_generates_receipt(self):
    """Test agent invoke generates receipt."""
    agent = TorkLangChainAgent(MockAgent())
    agent.invoke({"input": "Test input"})
    assert len(agent.receipts) >= 1
    assert agent.receipts[0]["type"] == "agent_input"
    assert "receipt_id" in agent.receipts[0]
```

### 6. Framework-Specific Tests

**What it tests**: Validates governance for each framework's unique features and patterns.

**Why it matters**: Each framework has different abstractions (chains, agents, tools, etc.) that all need governance.

Examples by framework:
- **LangChain**: Chain execution, agent tools, callbacks
- **CrewAI**: Crew orchestration, agent tasks, tool usage
- **AutoGen**: Group chat, multi-agent conversation
- **OpenAI Agents**: Runner execution, handoffs, tool calls

---

## PII Test Data Used

All tests use consistent PII samples defined in `test_data.py`:

### Test Samples

| PII Type | Sample Value | Redacted Output |
|----------|--------------|-----------------|
| Email | `john.doe@example.com` | `[EMAIL_REDACTED]` |
| Phone (US) | `(555) 123-4567` | `[PHONE_REDACTED]` |
| SSN | `123-45-6789` | `[SSN_REDACTED]` |
| Credit Card | `4111-1111-1111-1111` | `[CARD_REDACTED]` |

### Test Messages

```python
PII_SAMPLES = {
    "email": "john.doe@example.com",
    "phone_us": "(555) 123-4567",
    "ssn": "123-45-6789",
    "credit_card": "4111111111111111"
}

PII_MESSAGES = {
    "email_message": "Contact me at john.doe@example.com for details",
    "phone_message": "Call me at (555) 123-4567",
    "ssn_message": "My SSN is 123-45-6789",
    "credit_card_message": "Card number: 4111111111111111"
}
```

---

## How to Run Tests

### Run All AI Framework Tests

```bash
# Basic run
python3 -m pytest tests/ai_frameworks/ -v

# With summary
python3 -m pytest tests/ai_frameworks/ -v --tb=short
```

### Run Specific Framework Tests

```bash
# LangChain only
python3 -m pytest tests/ai_frameworks/test_langchain_adapter.py -v

# CrewAI only
python3 -m pytest tests/ai_frameworks/test_crewai_adapter.py -v

# Multiple frameworks
python3 -m pytest tests/ai_frameworks/test_langchain_adapter.py tests/ai_frameworks/test_crewai_adapter.py -v
```

### Run Specific Test Categories

```bash
# PII detection tests only
python3 -m pytest tests/ai_frameworks/ -v -k "PIIDetection"

# Configuration tests only
python3 -m pytest tests/ai_frameworks/ -v -k "Configuration"

# Error handling tests only
python3 -m pytest tests/ai_frameworks/ -v -k "ErrorHandling"
```

### Run with Coverage Report

```bash
# Terminal coverage report
python3 -m pytest tests/ai_frameworks/ --cov=tork_governance.adapters --cov-report=term-missing

# HTML coverage report
python3 -m pytest tests/ai_frameworks/ --cov=tork_governance.adapters --cov-report=html
open htmlcov/index.html
```

### Run with Timing Information

```bash
# Show slowest tests
python3 -m pytest tests/ai_frameworks/ -v --durations=10
```

---

## How to Replicate a Test

### Complete Example: LangChain Agent PII Test

Here's a complete, runnable example from `test_langchain_adapter.py`:

```python
"""
Test: Email PII Detection in LangChain Agent
File: tests/ai_frameworks/test_langchain_adapter.py
"""

import pytest
from tork_governance.adapters.langchain import TorkLangChainAgent

# Test data
PII_SAMPLES = {
    "email": "john.doe@example.com"
}

PII_MESSAGES = {
    "email_message": "Contact me at john.doe@example.com for details"
}


class TestLangChainPIIDetection:
    """Test PII detection and redaction in LangChain adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        # Create adapter instance
        agent = TorkLangChainAgent()

        # Govern text containing PII
        result = agent.govern(PII_MESSAGES["email_message"])

        # Verify PII is redacted
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

        # Print for verification
        print(f"Input:  {PII_MESSAGES['email_message']}")
        print(f"Output: {result}")
```

### Expected Output

```
Input:  Contact me at john.doe@example.com for details
Output: Contact me at [EMAIL_REDACTED] for details
```

### Running This Test

```bash
# Run just this test
python3 -m pytest tests/ai_frameworks/test_langchain_adapter.py::TestLangChainPIIDetection::test_govern_email_pii -v

# Output:
# tests/ai_frameworks/test_langchain_adapter.py::TestLangChainPIIDetection::test_govern_email_pii PASSED
```

---

## Adding Tests for New Frameworks

### Step 1: Create Test File

Create `tests/ai_frameworks/test_[framework]_adapter.py`:

```python
"""
Tests for [Framework] adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- [Framework-specific features]
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.[framework] import (
    Tork[Framework]Agent,
    Tork[Framework]Tool,
)
from .test_data import PII_SAMPLES, PII_MESSAGES
```

### Step 2: Add Standard Test Classes

```python
class Test[Framework]ImportInstantiation:
    """Test import and instantiation of [Framework] adapter."""

    def test_import_agent(self):
        """Test Tork[Framework]Agent can be imported."""
        assert Tork[Framework]Agent is not None

    def test_instantiate_agent_default(self):
        """Test agent instantiation with defaults."""
        agent = Tork[Framework]Agent()
        assert agent is not None
        assert agent.tork is not None
        assert agent.receipts == []


class Test[Framework]Configuration:
    """Test configuration of [Framework] adapter."""

    def test_agent_with_tork_instance(self, tork_instance):
        """Test agent with existing Tork instance."""
        agent = Tork[Framework]Agent(tork=tork_instance)
        assert agent.tork is tork_instance

    def test_agent_with_api_key(self):
        """Test agent with API key."""
        agent = Tork[Framework]Agent(api_key="test-key")
        assert agent.tork is not None


class Test[Framework]PIIDetection:
    """Test PII detection and redaction in [Framework] adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        agent = Tork[Framework]Agent()
        result = agent.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        agent = Tork[Framework]Agent()
        result = agent.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        agent = Tork[Framework]Agent()
        result = agent.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        agent = Tork[Framework]Agent()
        result = agent.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        agent = Tork[Framework]Agent()
        clean_text = "Hello, how are you?"
        result = agent.govern(clean_text)
        assert result == clean_text


class Test[Framework]ErrorHandling:
    """Test error handling in [Framework] adapter."""

    def test_agent_empty_string(self):
        """Test agent handles empty string."""
        agent = Tork[Framework]Agent()
        result = agent.govern("")
        assert result == ""

    def test_agent_whitespace(self):
        """Test agent handles whitespace."""
        agent = Tork[Framework]Agent()
        result = agent.govern("   ")
        assert result == "   "

    def test_agent_empty_receipts(self):
        """Test agent starts with empty receipts."""
        agent = Tork[Framework]Agent()
        assert agent.get_receipts() == []


class Test[Framework]ComplianceReceipts:
    """Test compliance receipt generation in [Framework] adapter."""

    def test_agent_generates_receipt(self):
        """Test agent operation generates receipt."""
        class MockAgent:
            def run(self, input_text, **kwargs):
                return f"Processed: {input_text}"

        agent = Tork[Framework]Agent(MockAgent())
        agent.run("Test input")
        assert len(agent.receipts) >= 1
        assert "receipt_id" in agent.receipts[0]
```

### Step 3: Add Framework-Specific Tests

```python
class Test[Framework]SpecificFeature:
    """Test [specific feature] governance."""

    def test_feature_governs_input(self):
        """Test [feature] governs input."""
        # Add framework-specific test
        pass

    def test_feature_governs_output(self):
        """Test [feature] governs output."""
        # Add framework-specific test
        pass
```

### Step 4: Run and Verify

```bash
# Run new tests
python3 -m pytest tests/ai_frameworks/test_[framework]_adapter.py -v

# Verify all tests pass
python3 -m pytest tests/ai_frameworks/ -v --tb=short
```

---

## Framework Coverage Table

| # | Framework | Adapter File | Test File | Tests |
|---|-----------|--------------|-----------|-------|
| 1 | LangChain | `langchain.py` | `test_langchain_adapter.py` | 34 |
| 2 | CrewAI | `crewai.py` | `test_crewai_adapter.py` | 38 |
| 3 | AutoGen | `autogen.py` | `test_autogen_adapter.py` | 38 |
| 4 | OpenAI Agents | `openai_agents.py` | `test_openai_agents_adapter.py` | 40 |
| 5 | MCP | `mcp.py` | `test_mcp_adapter.py` | 45 |
| 6 | LlamaIndex | `llamaindex.py` | `test_llamaindex_adapter.py` | 36 |
| 7 | Semantic Kernel | `semantic_kernel.py` | `test_semantic_kernel_adapter.py` | 39 |
| 8 | Haystack | `haystack.py` | `test_haystack_adapter.py` | 40 |
| 9 | Pydantic AI | `pydantic_ai.py` | `test_pydantic_ai_adapter.py` | 41 |
| 10 | DSPy | `dspy.py` | `test_dspy_adapter.py` | 45 |
| 11 | Instructor | `instructor.py` | `test_instructor_adapter.py` | 37 |
| 12 | Guidance | `guidance.py` | `test_guidance_adapter.py` | 43 |
| 13 | LMQL | `lmql.py` | `test_lmql_adapter.py` | 44 |
| 14 | Outlines | `outlines.py` | `test_outlines_adapter.py` | 50 |
| 15 | Marvin | `marvin.py` | `test_marvin_adapter.py` | 45 |
| 16 | SuperAGI | `superagi.py` | `test_superagi_adapter.py` | 35 |
| 17 | MetaGPT | `metagpt.py` | `test_metagpt_adapter.py` | 32 |
| 18 | BabyAGI | `babyagi.py` | `test_babyagi_adapter.py` | 32 |
| 19 | AgentGPT | `agentgpt.py` | `test_agentgpt_adapter.py` | 32 |
| 20 | Flowise | `flowise.py` | `test_flowise_adapter.py` | 32 |
| 21 | Langflow | `langflow.py` | `test_langflow_adapter.py` | 34 |
| **Total** | | | | **812** |

---

## CI/CD Integration

### GitHub Actions Workflow

Add to `.github/workflows/test.yml`:

```yaml
name: AI Framework Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-ai-frameworks:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run AI Framework Tests
        run: |
          python -m pytest tests/ai_frameworks/ -v --tb=short --junitxml=test-results.xml

      - name: Upload Test Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: test-results.xml

      - name: Generate Coverage Report
        run: |
          python -m pytest tests/ai_frameworks/ --cov=tork_governance.adapters --cov-report=xml

      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: ai-frameworks
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: ai-framework-tests
        name: AI Framework Tests
        entry: python -m pytest tests/ai_frameworks/ -v --tb=short -x
        language: system
        pass_filenames: false
        always_run: true
```

### Makefile Target

Add to `Makefile`:

```makefile
.PHONY: test-ai-frameworks

test-ai-frameworks:
	python -m pytest tests/ai_frameworks/ -v --tb=short

test-ai-frameworks-coverage:
	python -m pytest tests/ai_frameworks/ --cov=tork_governance.adapters --cov-report=html
	open htmlcov/index.html
```

---

## Quick Reference

### Test Commands

| Command | Description |
|---------|-------------|
| `pytest tests/ai_frameworks/ -v` | Run all tests |
| `pytest tests/ai_frameworks/ -k "PII"` | Run PII tests only |
| `pytest tests/ai_frameworks/ --collect-only` | List all tests |
| `pytest tests/ai_frameworks/ -x` | Stop on first failure |
| `pytest tests/ai_frameworks/ --lf` | Run last failed tests |

### Redaction Tokens

| PII Type | Token |
|----------|-------|
| Email | `[EMAIL_REDACTED]` |
| Phone | `[PHONE_REDACTED]` |
| SSN | `[SSN_REDACTED]` |
| Credit Card | `[CARD_REDACTED]` |

---

*Documentation generated: 2026-01-31*
*Tork Governance SDK v0.2.0*

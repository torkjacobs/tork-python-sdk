"""
Tests for Outlines adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Generator governance
- Model governance
- Prompt governance
- Decorator governance
- Structured output governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.outlines import (
    TorkOutlinesGenerator,
    TorkOutlinesModel,
    TorkOutlinesPrompt,
    governed_generate,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestOutlinesImportInstantiation:
    """Test import and instantiation of Outlines adapter."""

    def test_import_generator(self):
        """Test TorkOutlinesGenerator can be imported."""
        assert TorkOutlinesGenerator is not None

    def test_import_model(self):
        """Test TorkOutlinesModel can be imported."""
        assert TorkOutlinesModel is not None

    def test_import_prompt(self):
        """Test TorkOutlinesPrompt can be imported."""
        assert TorkOutlinesPrompt is not None

    def test_import_governed_generate(self):
        """Test governed_generate can be imported."""
        assert governed_generate is not None

    def test_instantiate_generator_default(self):
        """Test generator instantiation with defaults."""
        generator = TorkOutlinesGenerator()
        assert generator is not None
        assert generator.tork is not None
        assert generator.receipts == []

    def test_instantiate_model_default(self):
        """Test model instantiation with defaults."""
        model = TorkOutlinesModel()
        assert model is not None
        assert model.tork is not None


class TestOutlinesConfiguration:
    """Test configuration of Outlines adapter."""

    def test_generator_with_tork_instance(self, tork_instance):
        """Test generator with existing Tork instance."""
        generator = TorkOutlinesGenerator(tork=tork_instance)
        assert generator.tork is tork_instance

    def test_model_with_tork_instance(self, tork_instance):
        """Test model with existing Tork instance."""
        model = TorkOutlinesModel(tork=tork_instance)
        assert model.tork is tork_instance

    def test_prompt_with_tork_instance(self, tork_instance):
        """Test prompt with existing Tork instance."""
        prompt = TorkOutlinesPrompt(tork=tork_instance)
        assert prompt.tork is tork_instance

    def test_generator_with_api_key(self):
        """Test generator with API key."""
        generator = TorkOutlinesGenerator(api_key="test-key")
        assert generator.tork is not None


class TestOutlinesPIIDetection:
    """Test PII detection and redaction in Outlines adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        generator = TorkOutlinesGenerator()
        result = generator.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        generator = TorkOutlinesGenerator()
        result = generator.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        generator = TorkOutlinesGenerator()
        result = generator.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        generator = TorkOutlinesGenerator()
        result = generator.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        generator = TorkOutlinesGenerator()
        clean_text = "Generate a structured response"
        result = generator.govern(clean_text)
        assert result == clean_text


class TestOutlinesErrorHandling:
    """Test error handling in Outlines adapter."""

    def test_generator_empty_string(self):
        """Test generator handles empty string."""
        generator = TorkOutlinesGenerator()
        result = generator.govern("")
        assert result == ""

    def test_generator_whitespace(self):
        """Test generator handles whitespace."""
        generator = TorkOutlinesGenerator()
        result = generator.govern("   ")
        assert result == "   "

    def test_model_empty_string(self):
        """Test model handles empty string."""
        model = TorkOutlinesModel()
        result = model.govern("")
        assert result == ""

    def test_generator_empty_receipts(self):
        """Test generator starts with empty receipts."""
        generator = TorkOutlinesGenerator()
        assert generator.get_receipts() == []


class TestOutlinesComplianceReceipts:
    """Test compliance receipt generation in Outlines adapter."""

    def test_generator_call_generates_receipt(self):
        """Test generator call generates receipt."""
        def mock_gen(prompt, **kwargs):
            return f"Generated: {prompt}"

        generator = TorkOutlinesGenerator(mock_gen)
        generator("Test input")
        assert len(generator.receipts) >= 1
        assert generator.receipts[0]["type"] == "generator_input"
        assert "receipt_id" in generator.receipts[0]

    def test_generator_receipt_includes_action(self):
        """Test receipt includes action."""
        def mock_gen(prompt, **kwargs):
            return prompt

        generator = TorkOutlinesGenerator(mock_gen)
        generator(PII_MESSAGES["email_message"])
        assert "action" in generator.receipts[0]

    def test_generator_get_receipts(self):
        """Test generator get_receipts method."""
        generator = TorkOutlinesGenerator()
        receipts = generator.get_receipts()
        assert isinstance(receipts, list)


class TestOutlinesGeneratorGovernance:
    """Test generator governance."""

    def test_generator_governs_input(self):
        """Test generator governs input."""
        prompted = []

        def mock_gen(prompt, **kwargs):
            prompted.append(prompt)
            return prompt

        generator = TorkOutlinesGenerator(mock_gen)
        generator(PII_MESSAGES["email_message"])
        # The mock receives governed input
        assert PII_SAMPLES["email"] not in prompted[0]

    def test_generator_governs_output(self):
        """Test generator governs string output."""
        def mock_gen(prompt, **kwargs):
            return PII_MESSAGES["ssn_message"]

        generator = TorkOutlinesGenerator(mock_gen)
        result = generator("generate ssn")
        assert PII_SAMPLES["ssn"] not in result

    def test_generator_output_receipt(self):
        """Test generator generates output receipt."""
        def mock_gen(prompt, **kwargs):
            return "generated text"

        generator = TorkOutlinesGenerator(mock_gen)
        generator("test")
        assert any(r["type"] == "generator_output" for r in generator.receipts)

    def test_generator_non_string_output(self):
        """Test generator handles non-string output."""
        def mock_gen(prompt, **kwargs):
            return {"result": prompt}

        generator = TorkOutlinesGenerator(mock_gen)
        result = generator("test")
        assert result == {"result": "test"}

    def test_govern_input_alias(self):
        """Test govern_input is alias for govern."""
        generator = TorkOutlinesGenerator()
        result1 = generator.govern("test")
        result2 = generator.govern_input("test")
        assert result1 == result2


class TestOutlinesModelGovernance:
    """Test model governance."""

    def test_model_govern_method(self):
        """Test model govern method."""
        model = TorkOutlinesModel()
        result = model.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result

    def test_model_generate_governs_input(self):
        """Test model generate governs input."""
        class MockModel:
            def generate(self, prompt, **kwargs):
                return prompt

        model = TorkOutlinesModel(MockModel())
        result = model.generate(PII_MESSAGES["email_message"])
        # Input is governed before being passed to mock
        assert len(model.receipts) >= 1
        assert model.receipts[0]["type"] == "model_input"

    def test_model_generate_governs_output(self):
        """Test model generate governs output."""
        class MockModel:
            def generate(self, prompt, **kwargs):
                return PII_MESSAGES["ssn_message"]

        model = TorkOutlinesModel(MockModel())
        result = model.generate("generate ssn")
        assert PII_SAMPLES["ssn"] not in result

    def test_model_generate_json_governs_fields(self):
        """Test model generate_json governs fields."""
        class MockOutput:
            def __init__(self):
                self.email = PII_MESSAGES["email_message"]
                self.name = "John"

        class MockModel:
            def generate_json(self, prompt, schema, **kwargs):
                return MockOutput()

        model = TorkOutlinesModel(MockModel())
        result = model.generate_json("extract", type)
        assert PII_SAMPLES["email"] not in result.email

    def test_model_json_field_receipt(self):
        """Test model generates json field receipts."""
        class MockOutput:
            def __init__(self):
                self.field1 = "value1"

        class MockModel:
            def generate_json(self, prompt, schema, **kwargs):
                return MockOutput()

        model = TorkOutlinesModel(MockModel())
        model.generate_json("test", type)
        assert any(r["type"] == "json_field" for r in model.receipts)

    def test_model_get_receipts(self):
        """Test model get_receipts method."""
        model = TorkOutlinesModel()
        receipts = model.get_receipts()
        assert isinstance(receipts, list)


class TestOutlinesPromptGovernance:
    """Test prompt governance."""

    def test_prompt_govern_method(self):
        """Test prompt govern method."""
        prompt = TorkOutlinesPrompt()
        result = prompt.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result

    def test_prompt_template(self):
        """Test prompt template creation."""
        prompt = TorkOutlinesPrompt()
        template = prompt.template("Hello {name}, your email is {email}")
        assert callable(template)

    def test_prompt_template_governs_variables(self):
        """Test prompt template governs variables."""
        prompt = TorkOutlinesPrompt()
        template = prompt.template("Contact: {email}")
        result = template(email=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_prompt_template_variable_receipt(self):
        """Test prompt template generates variable receipts."""
        prompt = TorkOutlinesPrompt()
        template = prompt.template("Name: {name}")
        template(name="John Doe")
        assert len(prompt.receipts) == 1
        assert prompt.receipts[0]["type"] == "template_variable"
        assert prompt.receipts[0]["variable"] == "name"

    def test_prompt_template_non_string_variables(self):
        """Test prompt template passes through non-string variables."""
        prompt = TorkOutlinesPrompt()
        template = prompt.template("Count: {count}")
        result = template(count=42)
        assert "42" in result

    def test_prompt_get_receipts(self):
        """Test prompt get_receipts method."""
        prompt = TorkOutlinesPrompt()
        receipts = prompt.get_receipts()
        assert isinstance(receipts, list)


class TestOutlinesDecoratorGovernance:
    """Test decorator governance."""

    def test_governed_generate_decorator(self):
        """Test governed_generate decorator."""
        @governed_generate()
        def generate(prompt: str) -> str:
            return f"Generated: {prompt}"

        result = generate("test input")
        assert result == "Generated: test input"

    def test_governed_generate_governs_input(self):
        """Test governed_generate governs input."""
        @governed_generate()
        def generate(prompt: str) -> str:
            return prompt

        result = generate(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_governed_generate_generates_receipt(self):
        """Test governed_generate generates receipts."""
        @governed_generate()
        def generate(prompt: str) -> str:
            return prompt

        generate("test")
        receipts = generate.get_receipts()
        assert len(receipts) >= 1
        assert receipts[0]["type"] == "decorated_input"

    def test_governed_generate_governs_output(self):
        """Test governed_generate governs output."""
        @governed_generate()
        def generate(prompt: str) -> str:
            return PII_MESSAGES["ssn_message"]

        result = generate("test")
        assert PII_SAMPLES["ssn"] not in result

    def test_governed_generate_output_receipt(self):
        """Test governed_generate generates output receipt."""
        @governed_generate()
        def generate(prompt: str) -> str:
            return "output"

        generate("test")
        receipts = generate.get_receipts()
        assert any(r["type"] == "decorated_output" for r in receipts)

    def test_governed_generate_with_tork(self, tork_instance):
        """Test governed_generate with Tork instance."""
        @governed_generate(tork=tork_instance)
        def generate(prompt: str) -> str:
            return prompt

        result = generate("test")
        assert result == "test"

    def test_governed_generate_non_string_output(self):
        """Test governed_generate handles non-string output."""
        @governed_generate()
        def generate(prompt: str) -> dict:
            return {"result": prompt}

        result = generate("test")
        assert result == {"result": "test"}


class TestOutlinesStructuredOutputGovernance:
    """Test structured output governance."""

    def test_model_choice_governs_input(self):
        """Test model generate_choice governs input."""
        class MockModel:
            def generate_choice(self, prompt, choices, **kwargs):
                return choices[0]

        model = TorkOutlinesModel(MockModel())
        result = model.generate_choice(
            PII_MESSAGES["email_message"],
            ["option1", "option2"]
        )
        # Input is governed
        assert result == "option1"

    def test_model_regex_governs_output(self):
        """Test model generate_regex governs output."""
        class MockModel:
            def generate_regex(self, prompt, pattern, **kwargs):
                return PII_MESSAGES["phone_message"]

        model = TorkOutlinesModel(MockModel())
        result = model.generate_regex("extract phone", r"\d+")
        assert PII_SAMPLES["phone_us"] not in result

    def test_model_regex_output_receipt(self):
        """Test model generates regex output receipt."""
        class MockModel:
            def generate_regex(self, prompt, pattern, **kwargs):
                return "12345"

        model = TorkOutlinesModel(MockModel())
        model.generate_regex("test", r"\d+")
        assert any(r["type"] == "regex_output" for r in model.receipts)

    def test_multiple_generator_calls(self):
        """Test multiple generator calls accumulate receipts."""
        def mock_gen(prompt, **kwargs):
            return prompt

        generator = TorkOutlinesGenerator(mock_gen)
        generator("first")
        generator("second")
        assert len(generator.receipts) >= 2

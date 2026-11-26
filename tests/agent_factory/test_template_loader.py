"""Tests for Agent Factory Template Loader and Starter Templates."""

import pytest
from agent_factory.templates.loader import TemplateLoader
from agent_factory.spec.validator import SpecValidator


def test_starter_templates_loaded():
    loader = TemplateLoader()
    templates = loader.list_templates()
    template_names = {t["name"] for t in templates}

    expected_templates = {
        "c-suite-advisory",
        "finance-reconciliation",
        "marketing-campaign",
        "software-engineering-review",
        "devops-incident-triage",
        "defensive-cybersecurity-audit"
    }

    assert expected_templates.issubset(template_names), f"Missing starter templates: {expected_templates - template_names}"


def test_resolve_template_by_name_and_version():
    loader = TemplateLoader()
    t_latest = loader.resolve("finance-reconciliation")
    assert t_latest is not None
    assert t_latest.category == "finance"

    t_versioned = loader.resolve("finance-reconciliation@1.0.0")
    assert t_versioned is not None
    assert t_versioned.version == "1.0.0"

    t_nonexistent = loader.resolve("nonexistent-template@9.9.9")
    assert t_nonexistent is None


def test_instantiate_template_produces_valid_spec():
    loader = TemplateLoader()
    validator = SpecValidator()

    t = loader.resolve("c-suite-advisory")
    assert t is not None

    instantiated = t.instantiate({
        "name": "ceo-strategic-adviser",
        "display_name": "CEO Strategic Adviser",
        "role_title": "Executive AI Adviser",
        "mission": "Provide executive briefings and monitor high-level business goals"
    })

    result = validator.validate(instantiated)
    assert result.is_valid, f"Instantiated spec failed validation: {result.errors}"
    assert instantiated["metadata"]["name"] == "ceo-strategic-adviser"
    assert instantiated["metadata"]["category"] == "c_suite"
    assert instantiated["identity"]["may_use_employees"] is False

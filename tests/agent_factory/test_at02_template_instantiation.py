"""ZONATA Agent Factory - Acceptance Test AT-02: Agent from Template.

AT-02:
Given template 'software-engineering-review' active
When instantiate with valid params
Then template_ref set; spec equals base_spec ⊕ params; parameters outside schema -> 422/ValueError;
instantiation makes no redundant model call for fields given by params.
"""

import pytest
from agent_factory.templates.loader import TemplateLoader


def test_at02_agent_from_template():
    loader = TemplateLoader()

    # 1. Verify template exists
    tpl = loader.resolve("software-engineering-review")
    assert tpl is not None
    assert tpl.name == "software-engineering-review"
    assert tpl.category == "software_engineering"

    # 2. Instantiate with valid params
    params = {
        "role_title": "Senior Pull Request Auditor",
        "mission": "Audit PRs for performance, thread safety, and security"
    }

    spec = tpl.instantiate(params)

    assert spec["apiVersion"] == "zonata.agent/v1"
    assert spec["metadata"]["template"] == "software-engineering-review@1.0.0"
    assert spec["metadata"]["category"] == "software_engineering"
    assert spec["role"]["title"] == "Senior Pull Request Auditor"
    assert spec["role"]["mission"] == "Audit PRs for performance, thread safety, and security"
    # Base spec responsibilities and instructions preserved
    assert len(spec["role"]["responsibilities"]) > 0
    assert "Act as an uncompromising senior engineer" in spec["role"]["instructions"]

    # 3. Invalid parameter outside schema throws ValueError
    with pytest.raises(ValueError) as exc_info:
        tpl.instantiate({
            "role_title": "Valid Title",
            "unauthorized_escalation_flag": True
        })
    assert "AF-PARAM-SCHEMA" in str(exc_info.value)
    assert "unauthorized_escalation_flag" in str(exc_info.value)

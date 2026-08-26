from __future__ import annotations

import pytest

from browser_agent_evaluation.provider import ProviderContractError, parse_planner_proposal


def test_minimal_planner_output_maps_only_semantic_actions() -> None:
    proposal = parse_planner_proposal(
        '{"action":"click","role":"link","name":"Playwright"}', step_index=4
    )

    assert proposal.step_index == 4
    assert proposal.action is not None
    assert proposal.action.type == "click"
    assert proposal.action.target is not None
    assert proposal.action.target.role == "link"


@pytest.mark.parametrize(
    ("content", "action_type", "target_field"),
    [
        ('{"action":"select","label":"Dropdown (select)","value":"Two"}', "select", "label"),
        ('{"action":"check","label":"Default checkbox"}', "check", "label"),
        ('{"action":"wait"}', "wait", None),
        ('{"action":"extract_text","role":"heading","name":"Result"}', "extract_text", "role"),
    ],
)
def test_minimal_planner_output_maps_all_supported_semantic_actions(
    content: str, action_type: str, target_field: str | None
) -> None:
    proposal = parse_planner_proposal(content, step_index=2)

    assert proposal.action is not None
    assert proposal.action.type == action_type
    if target_field is None:
        assert proposal.action.target is None
    else:
        assert proposal.action.target is not None
        assert getattr(proposal.action.target, target_field) is not None


def test_minimal_planner_output_preserves_optional_expected_state() -> None:
    proposal = parse_planner_proposal(
        '{"action":"wait","expected_state":{"kind":"text_visible","value":"Done!"}}',
        step_index=3,
    )

    assert proposal.action is not None
    assert proposal.action.type == "wait"
    assert proposal.expected_state is not None
    assert proposal.expected_state.kind == "text_visible"
    assert proposal.expected_state.value == "Done!"


@pytest.mark.parametrize(
    "content",
    [
        '{"action":"click","selector":"#unsafe"}',
        '{"action":"evaluate","code":"alert(1)"}',
        '{"action":"navigate","url":"https://example.test","extra":true}',
        '{"action":"fill","label":"Search Wikipedia"}',
    ],
)
def test_minimal_planner_output_rejects_unsafe_or_ambiguous_forms(content: str) -> None:
    with pytest.raises(ProviderContractError, match="violates"):
        parse_planner_proposal(content, step_index=1)

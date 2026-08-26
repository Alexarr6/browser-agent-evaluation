from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from browser_agent_evaluation.core.models import RestrictedBrowserAction, TaskSpec

_SUBMISSION_NAMES = {"submit", "send", "enviar", "continuar", "continue"}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


def _target_names(action: RestrictedBrowserAction) -> tuple[str, ...]:
    target = action.target
    if target is None:
        return ()
    return tuple(
        value.strip().casefold()
        for value in (target.label, target.name, target.placeholder, target.text)
        if value and value.strip()
    )


def _is_authorized_submit_target(task: TaskSpec, action: RestrictedBrowserAction) -> bool:
    allowed = {label.strip().casefold() for label in task.policy.allowed_submit_labels}
    return bool(allowed.intersection(_target_names(action)))


def _is_submission(task: TaskSpec, action: RestrictedBrowserAction) -> bool:
    if action.type == "press" and (action.value or "").strip().casefold() == "enter":
        # A semantic ARIA searchbox is an explicitly bounded, read-only search action;
        # it cannot designate a checkout, login, or arbitrary form submit control.
        if action.target is not None and (action.target.role or "").casefold() == "searchbox":
            return False
        return not _is_authorized_submit_target(task, action)
    if action.type != "click" or action.target is None:
        return False
    names = _target_names(action)
    return any(name in _SUBMISSION_NAMES for name in names)


def validate_action(task: TaskSpec, action: RestrictedBrowserAction) -> PolicyDecision:
    if action.type == "navigate":
        hostname = urlparse(action.value or "").hostname
        if hostname not in task.policy.allowed_domains:
            return PolicyDecision(allowed=False, reason="domain_not_allowed")
    if _is_submission(task, action) and not task.policy.allow_form_submit:
        return PolicyDecision(allowed=False, reason="form_submit_not_allowed")
    return PolicyDecision(allowed=True, reason="allowed")

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from browser_agent_evaluation.core.models import TrialEvidence


@dataclass(frozen=True)
class RedactionResult:
    text: str
    events: tuple[str, ...]


def redact_and_bound(text: str, *, markers: list[str], max_bytes: int) -> RedactionResult:
    if max_bytes < 0:
        raise ValueError("max_bytes must not be negative")
    redacted = text
    events: list[str] = []
    for marker in markers:
        if marker and marker in redacted:
            redacted = redacted.replace(marker, "[REDACTED]")
            events.append("marker")
    encoded = redacted.encode("utf-8")
    if len(encoded) > max_bytes:
        redacted = encoded[:max_bytes].decode("utf-8", errors="ignore")
        events.append("truncated")
    return RedactionResult(text=redacted, events=tuple(dict.fromkeys(events)))


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_trial_evidence(
    evidence: TrialEvidence,
    *,
    output_dir: Path,
    raw_trace: str,
    markers: list[str],
    forbidden_paths: list[str],
    max_trace_bytes: int,
) -> Path:
    safe_trace = redact_and_bound(raw_trace, markers=markers, max_bytes=max_trace_bytes)
    safe_text = safe_trace.text
    path_events: list[str] = []
    for forbidden_path in forbidden_paths:
        if forbidden_path and forbidden_path in safe_text:
            safe_text = safe_text.replace(forbidden_path, "[REDACTED_PATH]")
            path_events.append("path")
    bounded = redact_and_bound(safe_text, markers=[], max_bytes=max_trace_bytes)
    payload = evidence.model_dump(mode="json")
    payload.update(
        {
            "trace": bounded.text,
            "trace_sha256": "sha256:" + hashlib.sha256(bounded.text.encode("utf-8")).hexdigest(),
            "trace_redaction_events": list(
                dict.fromkeys((*safe_trace.events, *path_events, *bounded.events)).keys()
            ),
        }
    )
    path = output_dir / f"{evidence.trial_id}.json"
    _atomic_write(path, json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return path

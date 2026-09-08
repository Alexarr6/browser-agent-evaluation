"""Lossless spelling normalization for named browser keys, not character input."""

_NAMED_KEYS = {
    key.casefold(): key
    for key in (
        "Enter",
        "Escape",
        "Tab",
        "Home",
        "End",
        "PageUp",
        "PageDown",
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "Backspace",
        "Delete",
    )
}


def normalize_key(value: str) -> str:
    return _NAMED_KEYS.get(value.casefold(), value)

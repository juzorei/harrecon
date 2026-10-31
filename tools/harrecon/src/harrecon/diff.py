"""Diff two captures of the same API: what changed between builds/deploys."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re

from .har import ApiCall, api_calls, schema_for


def schema_changes(before: dict, after: dict, path: str = "$") -> list[dict]:
    """Describe observed shape differences with unambiguous JSON-style paths.

    These are capture differences, not a claim of backward incompatibility.
    A renamed key is deliberately reported as a removal and an addition.
    """
    changes = []

    def add(kind, old, new):
        changes.append({"path": path, "kind": kind, "before": old, "after": new})

    if bool(before.get("optional")) != bool(after.get("optional")):
        add("optional_changed", bool(before.get("optional")), bool(after.get("optional")))
    if before.get("type") != after.get("type"):
        add("type_changed", before.get("type"), after.get("type"))
        return changes
    if before.get("type") == "object":
        old_fields, new_fields = before.get("fields", {}), after.get("fields", {})
        for key in sorted(old_fields.keys() | new_fields.keys()):
            child = path + (f".{key}" if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key)
                            else f"[{json.dumps(key, ensure_ascii=False)}]")
            if key not in old_fields or key not in new_fields:
                changes.append({"path": child,
                                "kind": "field_added" if key in new_fields else "field_removed",
                                "before": old_fields.get(key), "after": new_fields.get(key)})
            else:
                changes.extend(schema_changes(old_fields[key], new_fields[key], child))
    elif before.get("type") == "array":
        changes.extend(schema_changes(before.get("items") or {"type": "unknown"},
                                      after.get("items") or {"type": "unknown"}, path + "[]"))
    return changes


@dataclass
class ApiDiff:
    added: list[ApiCall] = field(default_factory=list)
    removed: list[ApiCall] = field(default_factory=list)
    changed: list[tuple[ApiCall, dict, dict]] = field(default_factory=list)  # call, before, after

    @property
    def quiet(self) -> bool:
        return not (self.added or self.removed or self.changed)


def diff(har_a: list, har_b: list, host: str | None = None) -> ApiDiff:
    def index(entries):
        return {(c.entries[0].method, c.host, c.endpoint): c for c in api_calls(entries, host)}

    before, after = index(har_a), index(har_b)
    d = ApiDiff()
    for key, call in after.items():
        if key not in before:
            d.added.append(call)
        else:
            sa, sb = schema_for(before[key]), schema_for(call)
            if sa != sb:
                d.changed.append((call, sa, sb))
    for key, call in before.items():
        if key not in after:
            d.removed.append(call)
    return d

"""Diff two captures of the same API: what changed between builds/deploys."""

from __future__ import annotations

from dataclasses import dataclass, field

from .har import ApiCall, api_calls, schema_for


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

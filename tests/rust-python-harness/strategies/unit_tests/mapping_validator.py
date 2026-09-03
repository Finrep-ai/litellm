from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from pydantic import BaseModel, ConfigDict


class TestMapping(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    python: str
    rust: str


@dataclass(frozen=True, slots=True)
class MappingReport:
    pairs: tuple[TestMapping, ...]
    problems: tuple[str, ...]


def _name(node: str) -> str:
    return node.rsplit("::", 1)[-1].split("[", 1)[0]


def validate_mapping(
    python_tests: Sequence[str],
    rust_tests: Sequence[str],
    annotations: Sequence[TestMapping] = (),
) -> MappingReport:
    explicit_problems: Final = (
        *(f"missing Python counterpart: {pair.python}" for pair in annotations if pair.python not in python_tests),
        *(f"missing Rust counterpart: {pair.rust}" for pair in annotations if pair.rust not in rust_tests),
        *(
            f"ambiguous Python annotation: {name}"
            for name, count in Counter(p.python for p in annotations).items()
            if count > 1
        ),
        *(
            f"ambiguous Rust annotation: {name}"
            for name, count in Counter(p.rust for p in annotations).items()
            if count > 1
        ),
    )
    explicit_python: Final = {pair.python for pair in annotations}
    candidates: Final = {
        python: tuple(rust for rust in rust_tests if _name(python) == _name(rust))
        for python in python_tests
        if python not in explicit_python
    }
    pairs: Final = (
        *annotations,
        *(TestMapping(python=python, rust=matches[0]) for python, matches in candidates.items() if len(matches) == 1),
    )
    problems: Final = (
        *explicit_problems,
        *(f"missing Rust counterpart: {python}" for python, matches in candidates.items() if not matches),
        *(
            f"ambiguous Rust counterparts: {python}: {matches}"
            for python, matches in candidates.items()
            if len(matches) > 1
        ),
        *(
            f"ambiguous Python counterparts: {rust}"
            for rust, count in Counter(pair.rust for pair in pairs).items()
            if count > 1
        ),
        *(f"missing Python counterpart: {rust}" for rust in rust_tests if rust not in {pair.rust for pair in pairs}),
        *(("no Python tests collected",) if not python_tests else ()),
        *(("no Rust tests collected",) if not rust_tests else ()),
    )
    return MappingReport(pairs, problems)

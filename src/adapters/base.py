"""Source adapter contract."""

from collections.abc import Iterable
from typing import Protocol

from domain import NormalizedJob


class JobAdapter(Protocol):
    def fetch(self) -> Iterable[NormalizedJob]: ...

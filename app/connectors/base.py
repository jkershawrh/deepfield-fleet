"""Base connector interface for data source adapters."""

from abc import ABC, abstractmethod
from typing import Iterator


class BaseConnector(ABC):
    name: str = "base"

    @abstractmethod
    def connect(self, config: dict) -> bool:
        ...

    @abstractmethod
    def sample(self, count: int = 200) -> list[dict]:
        ...

    def stream(self) -> Iterator[dict]:
        yield from self.sample()

    def describe(self) -> dict:
        return {"name": self.name, "connected": False}

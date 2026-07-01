"""Microagent registry — discovers and manages instances by modality."""

from app.microagents.base import BaseMicroagent

_agents: dict[str, BaseMicroagent] = {}


def register(agent: BaseMicroagent) -> None:
    _agents[agent.name] = agent


def get_agent(name: str) -> BaseMicroagent:
    return _agents[name]


def get_all_agents() -> list[BaseMicroagent]:
    return list(_agents.values())


def get_agents_for_modality(modality: str) -> list[BaseMicroagent]:
    return [a for a in _agents.values() if _handles_modality(a, modality)]


def _handles_modality(agent: BaseMicroagent, modality: str) -> bool:
    modality_map = getattr(agent, "modalities", None)
    if modality_map:
        return modality in modality_map
    return True

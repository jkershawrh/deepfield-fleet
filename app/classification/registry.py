"""Agent registry — maps tier+name to handler callables."""

_registry: dict[str, dict[str, object]] = {"nano": {}, "micro": {}, "macro": {}}


def register(agent_tier: str, agent_name: str, handler: object) -> None:
    if agent_tier not in _registry:
        _registry[agent_tier] = {}
    _registry[agent_tier][agent_name] = handler


def get_handlers(agent_tier: str) -> list:
    return list(_registry.get(agent_tier, {}).values())

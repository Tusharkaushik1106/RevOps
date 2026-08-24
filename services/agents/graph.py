from .state import RecoveryCase

def build_graph():
    raise NotImplementedError("Recovery agent graph is deferred beyond Phase 0")

def placeholder_node(case: RecoveryCase) -> RecoveryCase:
    raise NotImplementedError("Agent node implementation is deferred beyond Phase 0")

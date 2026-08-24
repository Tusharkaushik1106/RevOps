from typing import Protocol, Any

class Executor(Protocol):
    def execute(self, action: dict[str, Any]) -> dict[str, Any]: ...
class RazorpayAdapter(Protocol):
    def create_payment_link(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def get_payment_status(self, payment_id: str) -> dict[str, Any]: ...

class MockExecutor:
    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        return {"status": "mocked", "action": action}

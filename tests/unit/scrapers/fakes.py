"""Small HTTP fakes used by scraper adapter unit tests."""

from typing import Any


class FakeResponse:
    def __init__(
        self,
        payload: Any,
        *,
        status_code: int = 200,
        text: str | None = None,
        headers: dict[str, str] | None = None,
        url: str = "https://example.com",
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = text if text is not None else ""
        self.headers = headers or {"Content-Type": "application/json"}
        self.url = url

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("No fake response remains for this request")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

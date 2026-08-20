from __future__ import annotations

from hearth.llm import AnthropicClient


class _HttpError(Exception):
	def __init__(self, status_code: int, message: str = "") -> None:
		super().__init__(message)
		self.status_code = status_code


class _TextBlock:
	type = "text"
	text = "hello"


class _ApiResponse:
	stop_reason = "end_turn"
	content = [_TextBlock()]


class _ScriptedAPI:
	def __init__(self, outcomes: list[object]) -> None:
		self.outcomes = list(outcomes)
		self.calls: list[dict] = []

	@property
	def messages(self) -> _ScriptedAPI:
		return self

	def create(self, **kwargs):
		self.calls.append(kwargs)
		outcome = self.outcomes.pop(0)
		if isinstance(outcome, BaseException):
			raise outcome
		return outcome


def _complete(client: AnthropicClient, messages: list) -> object:
	return client.complete(
		model="fake",
		system="sys",
		messages=messages,
		tools=[],
		max_tokens=100,
	)


def test_retries_after_429_then_returns_text() -> None:
	api = _ScriptedAPI([_HttpError(429, "rate limit"), _ApiResponse()])
	slept: list[float] = []
	client = AnthropicClient(api, sleep=slept.append)
	result = _complete(client, [{"role": "user", "content": "hi"}])
	assert result.text == "hello"
	assert len(api.calls) == 2
	assert slept == [0.5]


def test_retries_after_529() -> None:
	api = _ScriptedAPI([_HttpError(529, "overloaded"), _ApiResponse()])
	client = AnthropicClient(api, sleep=lambda _delay: None)
	result = _complete(client, [{"role": "user", "content": "hi"}])
	assert result.text == "hello"
	assert len(api.calls) == 2


def test_prompt_too_long_snips_then_retries() -> None:
	huge = "x" * 8000
	messages = [
		{"role": "user", "content": "start"},
		{"role": "assistant", "content": "working"},
		{
			"role": "user",
			"content": [
				{
					"type": "tool_result",
					"tool_use_id": "t-old",
					"content": huge,
				}
			],
		},
		{"role": "user", "content": "n1"},
		{"role": "user", "content": "n2"},
		{"role": "user", "content": "n3"},
		{"role": "user", "content": "n4"},
		{"role": "user", "content": "now"},
	]
	api = _ScriptedAPI(
		[_HttpError(400, "prompt is too long"), _ApiResponse()]
	)
	client = AnthropicClient(api, sleep=lambda _delay: None)
	result = _complete(client, messages)
	assert result.text == "hello"
	assert len(api.calls) == 2
	snipped = api.calls[1]["messages"][2]["content"][0]["content"]
	assert snipped != huge
	assert "[compacted]" in snipped


def test_other_errors_are_not_retried() -> None:
	api = _ScriptedAPI([_HttpError(400, "bad request")])
	client = AnthropicClient(api, sleep=lambda _delay: None)
	try:
		_complete(client, [{"role": "user", "content": "hi"}])
	except _HttpError as error:
		assert error.status_code == 400
	else:
		raise AssertionError("expected the 400 to propagate")
	assert len(api.calls) == 1

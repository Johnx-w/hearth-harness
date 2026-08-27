from __future__ import annotations

from hearth.llm import (
	CIRCUIT_COOLDOWN_SECONDS,
	MAX_RATE_RETRIES,
	AnthropicClient,
	CircuitOpenError,
)


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


class _Clock:
	def __init__(self) -> None:
		self.now = 0.0

	def __call__(self) -> float:
		return self.now

	def advance(self, seconds: float) -> None:
		self.now += seconds


def _client(
	api: _ScriptedAPI,
	*,
	slept: list[float] | None = None,
	rng: float = 0.0,
	clock: _Clock | None = None,
) -> AnthropicClient:
	return AnthropicClient(
		api,
		sleep=(slept.append if slept is not None else lambda _delay: None),
		rng=lambda: rng,
		clock=clock,
	)


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
	client = _client(api, slept=slept)
	result = _complete(client, [{"role": "user", "content": "hi"}])
	assert result.text == "hello"
	assert len(api.calls) == 2
	assert slept == [0.5]


def test_retries_after_529_wait_longer_than_429() -> None:
	api = _ScriptedAPI([_HttpError(529, "overloaded"), _ApiResponse()])
	slept: list[float] = []
	client = _client(api, slept=slept)
	result = _complete(client, [{"role": "user", "content": "hi"}])
	assert result.text == "hello"
	assert slept == [2.0]


def test_retry_delay_includes_jitter() -> None:
	api = _ScriptedAPI([_HttpError(429, "rate limit"), _ApiResponse()])
	slept: list[float] = []
	client = _client(api, slept=slept, rng=1.0)
	_complete(client, [{"role": "user", "content": "hi"}])
	assert slept == [0.625]


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
	client = _client(api)
	result = _complete(client, messages)
	assert result.text == "hello"
	assert len(api.calls) == 2
	snipped = api.calls[1]["messages"][2]["content"][0]["content"]
	assert snipped != huge
	assert "[compacted]" in snipped


def test_other_errors_are_not_retried() -> None:
	api = _ScriptedAPI([_HttpError(400, "bad request")])
	client = _client(api)
	try:
		_complete(client, [{"role": "user", "content": "hi"}])
	except _HttpError as error:
		assert error.status_code == 400
	else:
		raise AssertionError("expected the 400 to propagate")
	assert len(api.calls) == 1


def test_circuit_opens_after_consecutive_exhausted_retries() -> None:
	burst = MAX_RATE_RETRIES + 1
	api = _ScriptedAPI(
		[_HttpError(429, "rate limit")] * (burst * 2) + [_ApiResponse()]
	)
	clock = _Clock()
	client = _client(api, clock=clock)
	messages = [{"role": "user", "content": "hi"}]
	for _ in range(2):
		try:
			_complete(client, messages)
		except _HttpError as error:
			assert error.status_code == 429
		else:
			raise AssertionError("expected retries to be exhausted")
	assert len(api.calls) == burst * 2
	try:
		_complete(client, messages)
	except CircuitOpenError:
		pass
	else:
		raise AssertionError("expected the circuit to be open")
	assert len(api.calls) == burst * 2
	clock.advance(CIRCUIT_COOLDOWN_SECONDS)
	result = _complete(client, messages)
	assert result.text == "hello"


def test_circuit_does_not_open_on_non_rate_errors() -> None:
	api = _ScriptedAPI(
		[_HttpError(400, "bad request"), _ApiResponse()]
	)
	client = _client(api)
	try:
		_complete(client, [{"role": "user", "content": "hi"}])
	except _HttpError:
		pass
	result = _complete(client, [{"role": "user", "content": "again"}])
	assert result.text == "hello"

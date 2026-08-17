from __future__ import annotations

import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db_llm_runtime_v5 import ChEMBLLLMQuery, DspyProvider, FallbackEndpointConfig, SharedQuotaFallbackState
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status={self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_new_profile_resolves_to_requested_chain() -> None:
    endpoint, fallback = resolve_profile("zai-glm47-local-fallbacks")

    assert endpoint is not None
    assert endpoint.provider == "zai-anthropic"
    assert endpoint.model == "glm-4.7"
    assert isinstance(fallback, list)
    assert [item.base_url for item in fallback] == [
        "http://127.0.0.1:18081",
        "http://127.0.0.1:8081",
    ]
    assert [item.model for item in fallback] == [
        "nemotron-cascade-2-30b-a3b",
        "nemotron-cascade-2-30b-a3b",
    ]


def test_build_provider_skips_unreachable_fallbacks_and_adopts_advertised_model(monkeypatch) -> None:
    def fake_get(url: str, timeout: float):
        if "127.0.0.1:18081" in url:
            return _FakeResponse({"data": [{"id": "nemotron-cascade-2-30b-a3b"}]})
        if "127.0.0.1:8081" in url:
            raise requests.exceptions.ConnectionError("closed")
        raise AssertionError(url)

    monkeypatch.setattr("db_llm_v5.provider.requests.get", fake_get)

    provider = build_provider(
        endpoint=EndpointConfig(
            provider="zai-anthropic",
            model="glm-4.7",
            base_url="https://api.z.ai/api/anthropic",
        ),
        fallback=[
            EndpointConfig(provider="llamacpp", model="Qwen3.5-35B-A3B", base_url="http://127.0.0.1:18081"),
            EndpointConfig(provider="llamacpp", model="Qwen3.5-35B-A3B", base_url="http://127.0.0.1:8081"),
        ],
    )

    state = provider.shared_quota_fallback_state
    assert state is not None
    assert len(state.configs) == 1
    assert state.configs[0].base_url == "http://127.0.0.1:18081"
    assert state.configs[0].model == "nemotron-cascade-2-30b-a3b"


def test_active_local_fallback_advances_on_request_failure() -> None:
    state = SharedQuotaFallbackState(
        [
            FallbackEndpointConfig(
                provider="llamacpp",
                model="first-model",
                base_url="http://127.0.0.1:18081",
            ),
            FallbackEndpointConfig(
                provider="llamacpp",
                model="second-model",
                base_url="http://127.0.0.1:8081",
            ),
        ]
    )
    assert state.activate(reason="quota")

    provider = DspyProvider(
        provider="llamacpp",
        model="first-model",
        base_url="http://127.0.0.1:18081",
        temperature=0.2,
        timeout=30,
        shared_quota_fallback_state=state,
    )

    advanced = provider._advance_shared_fallback_on_request_failure(OSError("server closed"))

    assert advanced is True
    assert provider.base_url == "http://127.0.0.1:8081/v1"
    assert provider.model == "second-model"


def test_single_fallback_failure_forces_primary_retry() -> None:
    state = SharedQuotaFallbackState(
        [
            FallbackEndpointConfig(
                provider="llamacpp",
                model="fallback-model",
                base_url="http://127.0.0.1:18081",
            ),
        ],
        primary_config=FallbackEndpointConfig(
            provider="zai-anthropic",
            model="glm-4.7",
            base_url="https://api.z.ai/api/anthropic",
        ),
        quota_retry_seconds=3600.0,
    )
    assert state.activate(reason="zai-anthropic quota code 1308") is True

    provider = DspyProvider(
        provider="llamacpp",
        model="fallback-model",
        base_url="http://127.0.0.1:18081",
        temperature=0.2,
        timeout=30,
        shared_quota_fallback_state=state,
    )
    provider._fallback_applied_index = 0

    advanced = provider._advance_shared_fallback_on_request_failure(OSError("connection refused"))

    assert advanced is True
    assert provider.provider == "zai-anthropic"
    assert provider.model == "glm-4.7"
    assert provider.base_url == "https://api.z.ai/api/anthropic"
    assert state.active is False


def test_local_responses_api_disables_llama_cpp_thinking(monkeypatch) -> None:
    captured_payloads: list[dict] = []

    def fake_post(url: str, *, headers: dict, json: dict, timeout: int):
        captured_payloads.append(dict(json))
        assert url == "http://127.0.0.1:18081/v1/responses"
        assert headers["Authorization"] == "Bearer EMPTY"
        assert timeout == 30
        return _FakeResponse(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"up":"hello"}',
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr("db_llm_runtime_v5.requests.post", fake_post)

    provider = DspyProvider(
        provider="llamacpp",
        model="nemotron-cascade-2-30b-a3b",
        base_url="http://127.0.0.1:18081",
        temperature=0.2,
        timeout=30,
    )

    text = provider.generate_text(
        [{"role": "user", "content": "Return JSON."}],
        max_tokens=50,
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    assert text == '{"up":"hello"}'
    assert captured_payloads[0]["chat_template_kwargs"] == {"enable_thinking": False}



def test_shared_fallback_state_does_not_skip_first_local_fallback_on_parallel_primary_quota() -> None:
    state = SharedQuotaFallbackState(
        [
            FallbackEndpointConfig(
                provider="llamacpp",
                model="remote-fast",
                base_url="http://127.0.0.1:18081/v1",
            ),
            FallbackEndpointConfig(
                provider="llamacpp",
                model="local-slow",
                base_url="http://127.0.0.1:8081/v1",
            ),
        ],
        primary_config=FallbackEndpointConfig(
            provider="zai-anthropic",
            model="glm-4.7",
            base_url="https://api.z.ai/api/anthropic",
        ),
    )

    assert state.activate(reason="zai-anthropic quota code 1302: Rate limit reached") is True
    assert state.current_index == 0

    # A second in-flight request can report the same primary quota error after
    # fallback is already active; it must not skip the preferred 18081 fallback.
    assert state.activate(reason="zai-anthropic quota code 1302: Rate limit reached") is False
    assert state.current_index == 0
    assert state.config.base_url == "http://127.0.0.1:18081/v1"

    # Real fallback request failure still advances to the next local endpoint.
    assert state.activate(reason="llamacpp request failure: ReadTimeout") is True
    assert state.current_index == 1
    assert state.config.base_url == "http://127.0.0.1:8081/v1"

def test_shared_fallback_state_restores_primary_after_quota_cooldown() -> None:
    clock = {"now": 0.0}

    state = SharedQuotaFallbackState(
        [
            FallbackEndpointConfig(
                provider="llamacpp",
                model="fallback-model",
                base_url="http://127.0.0.1:18081/v1",
            )
        ],
        primary_config=FallbackEndpointConfig(
            provider="zai-anthropic",
            model="glm-4.7",
            base_url="https://api.z.ai/api/anthropic",
        ),
        quota_retry_seconds=9000.0,
        time_fn=lambda: clock["now"],
    )

    assert state.activate(reason="zai-anthropic quota code 1308")
    assert state.maybe_restore_primary() is None

    clock["now"] = 9000.0
    restored = state.maybe_restore_primary()

    assert restored is not None
    assert restored.provider == "zai-anthropic"
    assert restored.model == "glm-4.7"
    assert state.active is False


def test_query_v5_runtime_builds_one_hour_primary_retry_state() -> None:
    query = ChEMBLLLMQuery(
        db_path=":memory:",
        provider="zai-anthropic",
        sql_model="glm-4.7",
        judge_model="glm-4.7",
        up_model="glm-4.7",
        provider_base_url="https://api.z.ai/api/anthropic",
        quota_fallback_provider="llamacpp",
        quota_fallback_model="nemotron-cascade-2-30b-a3b",
        quota_fallback_base_url="https://fallback.local:8081",
        save_intermediate=False,
        memory_json_path=None,
    )
    try:
        state = query.shared_quota_fallback_state
        assert state is not None
        assert state.primary_config is not None
        assert state.primary_config.provider == "zai-anthropic"
        assert state.primary_config.model == "glm-4.7"
        assert state.quota_retry_seconds == 3600.0
        assert state._refresh_interval_seconds == 3600.0
        assert state._refresh_callback is not None
    finally:
        query.conn.close()


def test_shared_fallback_state_refreshes_configs_hourly() -> None:
    clock = {"now": 0.0}
    refresh_calls: list[float] = []

    def refresh() -> list[FallbackEndpointConfig]:
        refresh_calls.append(clock["now"])
        return [
            FallbackEndpointConfig(
                provider="llamacpp",
                model="nemotron-cascade-2-30b-a3b",
                base_url="http://127.0.0.1:18081/v1",
            ),
            FallbackEndpointConfig(
                provider="llamacpp",
                model="Qwen3.5-35B-A3B",
                base_url="http://127.0.0.1:8081/v1",
            ),
        ]

    state = SharedQuotaFallbackState(
        [
            FallbackEndpointConfig(
                provider="llamacpp",
                model="Qwen3.5-35B-A3B",
                base_url="http://127.0.0.1:8081/v1",
            )
        ],
        refresh_callback=refresh,
        refresh_interval_seconds=3600.0,
        time_fn=lambda: clock["now"],
    )

    assert state.maybe_refresh_configs() is False

    clock["now"] = 3600.0
    assert state.maybe_refresh_configs() is True
    assert refresh_calls == [3600.0]
    assert [config.base_url for config in state.configs] == [
        "http://127.0.0.1:18081/v1",
        "http://127.0.0.1:8081/v1",
    ]

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db_llm_runtime_v5 import DspyProvider, FallbackEndpointConfig, SharedQuotaFallbackState

LOGGER = logging.getLogger(__name__)
LOCAL_OPENAI_COMPAT_PROVIDERS = {"llamacpp", "mlxlm", "local"}
LOCAL_ENDPOINT_PROBE_TIMEOUT_SECONDS = 3.0
FALLBACK_REPROBE_INTERVAL_SECONDS = 3600.0
ZAI_PRIMARY_RETRY_SECONDS = 3600.0


@dataclass(slots=True)
class EndpointConfig:
    provider: str
    model: str
    base_url: str | None = None
    temperature: float = 0.2
    timeout: int = 1200


@dataclass(slots=True)
class CallResult:
    text: str | None
    parsed_json: dict[str, Any] | None


def _local_fallback_chain(default_model: str = "nemotron-cascade-2-30b-a3b") -> list[EndpointConfig]:
    return [
        EndpointConfig(
            provider="llamacpp",
            model=default_model,
            base_url="http://127.0.0.1:18081",
            temperature=0.2,
            timeout=1200,
        ),
        EndpointConfig(
            provider="llamacpp",
            model=default_model,
            base_url="http://127.0.0.1:8081",
            temperature=0.2,
            timeout=1200,
        ),
    ]


def resolve_profile(profile: str | None) -> tuple[EndpointConfig | None, EndpointConfig | list[EndpointConfig] | None]:
    if not profile:
        return None, None
    if profile in {
        "zai-glm-4.7-anthropic",
        "zai-glm47-local-fallbacks",
        "zai-glm47-then-local18081-then-local8081",
    }:
        return (
            EndpointConfig(
                provider="zai-anthropic",
                model="glm-4.7",
                base_url="https://api.z.ai/api/anthropic",
                temperature=0.2,
                timeout=1200,
            ),
            _local_fallback_chain(),
        )
    if profile == "zai-glm-5-turbo":
        return (
            EndpointConfig(
                provider="zai",
                model="glm-5-turbo",
                base_url="https://api.z.ai/api/paas/v4",
                temperature=0.2,
                timeout=1200,
            ),
            _local_fallback_chain(),
        )
    if profile in {"zai-glm47-then-glm5-then-local", "zai-glm47-glm5-local"}:
        return (
            EndpointConfig(
                provider="zai-anthropic",
                model="glm-4.7",
                base_url="https://api.z.ai/api/anthropic",
                temperature=0.2,
                timeout=1200,
            ),
            [
                EndpointConfig(
                    provider="zai",
                    model="glm-5-turbo",
                    base_url="https://api.z.ai/api/paas/v4",
                    temperature=0.2,
                    timeout=1200,
                ),
                *_local_fallback_chain(),
            ],
        )
    if profile in {"zai-glm51-then-local", "zai-glm51-local"}:
        return (
            EndpointConfig(
                provider="zai-anthropic",
                model="glm-5.1",
                temperature=0.2,
                timeout=1200,
            ),
            _local_fallback_chain(default_model="nemotron-cascade-2-30b-a3b"),
        )
    if profile == "local-qwen35":
        return (
            EndpointConfig(
                provider="llamacpp",
                model="Qwen3.5-35B-A3B",
                base_url="http://127.0.0.1:18081",
                temperature=0.2,
                timeout=1200,
            ),
            None,
        )
    if profile == "opencode-go-dsv4-flash":
        opencode_go_key = __import__("os").getenv(
            "OPENCODE_GO_LJ_API_KEY",
            __import__("os").getenv("OPENCODE_GO_API_KEY", ""),
        )
        opencode_go_base = __import__("os").getenv(
            "OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1"
        )
        return (
            EndpointConfig(
                provider="openai",
                model="deepseek-v4-flash",
                base_url=opencode_go_base,
                temperature=0.2,
                timeout=1200,
            ),
            None,
        )
    raise ValueError(f"unsupported profile: {profile}")


def build_provider(
    *,
    endpoint: EndpointConfig,
    fallback: EndpointConfig | list[EndpointConfig] | None = None,
) -> DspyProvider:
    endpoint = _prepare_primary_endpoint(endpoint)
    shared_fallback_state = None
    fallback_list: list[EndpointConfig] | None = None
    if fallback is not None:
        fallback_list = fallback if isinstance(fallback, list) else [fallback]
        fallback_list = _prepare_fallback_chain(fallback_list)
        if not fallback_list:
            LOGGER.warning(
                "No reachable fallback endpoints remain for primary %s/%s.",
                endpoint.provider,
                endpoint.model,
            )
            fallback_list = None
    if fallback is not None and fallback_list is not None:
        refresh_callback = _build_fallback_refresh_callback(
            fallback if isinstance(fallback, list) else [fallback]
        )
        quota_retry_seconds = (
            ZAI_PRIMARY_RETRY_SECONDS if endpoint.provider in {"zai", "zai-anthropic"} else None
        )
        shared_fallback_state = SharedQuotaFallbackState(
            [
                FallbackEndpointConfig(
                    provider=item.provider,
                    model=item.model,
                    base_url=item.base_url,
                )
                for item in fallback_list
            ],
            primary_config=FallbackEndpointConfig(
                provider=endpoint.provider,
                model=endpoint.model,
                base_url=endpoint.base_url,
            ),
            refresh_callback=refresh_callback,
            refresh_interval_seconds=FALLBACK_REPROBE_INTERVAL_SECONDS,
            quota_retry_seconds=quota_retry_seconds,
        )
    return DspyProvider(
        provider=endpoint.provider,
        model=endpoint.model,
        base_url=endpoint.base_url,
        temperature=endpoint.temperature,
        timeout=endpoint.timeout,
        shared_quota_fallback_state=shared_fallback_state,
    )


def _prepare_primary_endpoint(endpoint: EndpointConfig) -> EndpointConfig:
    if not _should_probe_endpoint(endpoint):
        return endpoint
    available_models = _probe_endpoint_models(endpoint)
    if not available_models:
        LOGGER.warning(
            "Primary local endpoint probe failed for %s; keeping configured model %s.",
            endpoint.base_url,
            endpoint.model,
        )
        return endpoint
    if endpoint.model in available_models:
        return endpoint
    selected_model = available_models[0]
    LOGGER.warning(
        "Primary local endpoint %s does not advertise %s; using %s.",
        endpoint.base_url,
        endpoint.model,
        selected_model,
    )
    return EndpointConfig(
        provider=endpoint.provider,
        model=selected_model,
        base_url=endpoint.base_url,
        temperature=endpoint.temperature,
        timeout=endpoint.timeout,
    )


def _prepare_fallback_chain(fallback_list: list[EndpointConfig]) -> list[EndpointConfig]:
    prepared: list[EndpointConfig] = []
    for endpoint in fallback_list:
        if not _should_probe_endpoint(endpoint):
            prepared.append(endpoint)
            continue
        available_models = _probe_endpoint_models(endpoint)
        if not available_models:
            LOGGER.warning("Skipping unreachable fallback endpoint %s.", endpoint.base_url)
            continue
        selected_model = endpoint.model
        if selected_model not in available_models:
            selected_model = available_models[0]
            LOGGER.warning(
                "Fallback endpoint %s does not advertise %s; using %s.",
                endpoint.base_url,
                endpoint.model,
                selected_model,
            )
        prepared.append(
            EndpointConfig(
                provider=endpoint.provider,
                model=selected_model,
                base_url=endpoint.base_url,
                temperature=endpoint.temperature,
                timeout=endpoint.timeout,
            )
        )
    return prepared


def _build_fallback_refresh_callback(
    fallback_list: list[EndpointConfig],
):
    original_chain = [
        EndpointConfig(
            provider=item.provider,
            model=item.model,
            base_url=item.base_url,
            temperature=item.temperature,
            timeout=item.timeout,
        )
        for item in fallback_list
    ]

    def refresh() -> list[FallbackEndpointConfig]:
        refreshed = _prepare_fallback_chain(original_chain)
        return [
            FallbackEndpointConfig(
                provider=item.provider,
                model=item.model,
                base_url=item.base_url,
            )
            for item in refreshed
        ]

    return refresh


def _should_probe_endpoint(endpoint: EndpointConfig) -> bool:
    return (
        endpoint.provider in LOCAL_OPENAI_COMPAT_PROVIDERS
        and bool(endpoint.base_url)
        and str(endpoint.base_url).startswith("http://")
    )


def _probe_endpoint_models(endpoint: EndpointConfig) -> list[str]:
    if not endpoint.base_url:
        return []
    base_url = str(endpoint.base_url).rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    try:
        response = requests.get(
            f"{base_url}/models",
            timeout=LOCAL_ENDPOINT_PROBE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Endpoint probe failed for %s: %s", endpoint.base_url, exc)
        return []

    models: list[str] = []
    payload = data.get("data")
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
    if not models:
        payload = data.get("models")
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    model_id = item.get("id") or item.get("model") or item.get("name")
                    if model_id:
                        models.append(str(model_id))
    if models:
        LOGGER.info("Endpoint probe %s -> models=%s", endpoint.base_url, models)
    else:
        LOGGER.warning("Endpoint probe %s returned no model ids.", endpoint.base_url)
    return models


def run_json_call(
    *,
    provider: DspyProvider,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1200,
    temperature: float | None = None,
    expected_key: str | None = None,
) -> CallResult:
    text = provider.generate_text(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=provider.temperature if temperature is None else temperature,
        response_format={"type": "json_object"},
    )
    parsed = _parse_json_object(text)
    if parsed is None and expected_key:
        parsed = _coerce_expected_payload(text, expected_key)
    return CallResult(text=text, parsed_json=parsed)


def run_json_call_with_retry(
    *,
    provider: DspyProvider,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1200,
    temperature: float | None = None,
    expected_key: str | None = None,
    max_attempts: int = 3,
    retry_backoff_seconds: float = 1.0,
) -> CallResult:
    last_result: CallResult | None = None
    last_error: Exception | None = None
    attempts = max(1, int(max_attempts))
    for attempt_idx in range(attempts):
        try:
            result = run_json_call(
                provider=provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                expected_key=expected_key,
            )
            last_result = result
            if _is_usable_result(result, expected_key=expected_key):
                return result
        except Exception as exc:
            last_error = exc
        if attempt_idx + 1 < attempts and retry_backoff_seconds > 0:
            time.sleep(retry_backoff_seconds * (attempt_idx + 1))
    if last_result is not None:
        return last_result
    if last_error is not None:
        raise last_error
    return CallResult(text=None, parsed_json=None)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _parse_json_object(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = json.loads(stripped)
        return value if isinstance(value, dict) else None
    except Exception:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        value = json.loads(stripped[start : end + 1])
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _coerce_expected_payload(text: str | None, expected_key: str) -> dict[str, Any] | None:
    cleaned = _strip_fences(text)
    if not cleaned:
        return None
    if expected_key == "sql":
        upper = cleaned.lstrip().upper()
        if upper.startswith("SELECT") or upper.startswith("WITH"):
            return {"sql": cleaned}
    if expected_key in {"up", "up_exec", "uq_surface", "intent_sketch"}:
        return {expected_key: cleaned}
    if expected_key in {"analysis", "decision"}:
        return None
    return None


def _is_usable_result(result: CallResult, *, expected_key: str | None) -> bool:
    if not (result.text or "").strip():
        return False
    if expected_key is None:
        return result.parsed_json is not None or bool((result.text or "").strip())
    if not isinstance(result.parsed_json, dict):
        return False
    value = result.parsed_json.get(expected_key)
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _strip_fences(text: str | None) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if not lines:
        return stripped
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()

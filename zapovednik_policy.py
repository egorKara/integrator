from __future__ import annotations

from typing import Final, Literal, TypedDict, cast

ProfileName = Literal["research", "coding", "ops"]
DEFAULT_PROFILE: Final[ProfileName] = "coding"


class ZapovednikPolicy(TypedDict):
    context_window_tokens: int
    message_soft_limit: int
    size_soft_limit_kb: int
    token_soft_ratio: float
    token_hard_ratio: float
    min_repeated_tokens: int
    min_repeat_frequency: int
    score_threshold: float
    latency_degradation: float


POLICY_PROFILES: Final[dict[ProfileName, ZapovednikPolicy]] = {
    "research": {
        "context_window_tokens": 240000,
        "message_soft_limit": 80,
        "size_soft_limit_kb": 320,
        "token_soft_ratio": 0.82,
        "token_hard_ratio": 0.93,
        "min_repeated_tokens": 7,
        "min_repeat_frequency": 4,
        "score_threshold": 0.85,
        "latency_degradation": 0.0,
    },
    "coding": {
        "context_window_tokens": 180000,
        "message_soft_limit": 45,
        "size_soft_limit_kb": 190,
        "token_soft_ratio": 0.72,
        "token_hard_ratio": 0.86,
        "min_repeated_tokens": 5,
        "min_repeat_frequency": 3,
        "score_threshold": 0.76,
        "latency_degradation": 0.0,
    },
    "ops": {
        "context_window_tokens": 120000,
        "message_soft_limit": 24,
        "size_soft_limit_kb": 96,
        "token_soft_ratio": 0.55,
        "token_hard_ratio": 0.7,
        "min_repeated_tokens": 4,
        "min_repeat_frequency": 3,
        "score_threshold": 0.6,
        "latency_degradation": 0.0,
    },
}


def get_policy(profile: str) -> ZapovednikPolicy:
    key = str(profile).strip().lower()
    if key not in POLICY_PROFILES:
        key = DEFAULT_PROFILE
    selected = POLICY_PROFILES[cast(ProfileName, key)]
    return cast(ZapovednikPolicy, dict(selected))

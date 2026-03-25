"""
Reasoning Service — 유사도 근거 문장 자동 생성 (Rule-based)
기획안 v5 §8-2 기준
"""
from app.core.schemas import MatchReason

# 차원별 레이블 정의 (사용자 값 기준)
_VISUAL_LABELS = {
    "eye_size_score":          ("작은 눈",   "큰 눈"),
    "eye_distance_score":      ("좁은 미간", "넓은 미간"),
    "eye_roundness_score":     ("날카로운 눈매", "둥근 눈매"),
    "eye_tail_score":          ("처진 눈꼬리", "올라간 눈꼬리"),
    "face_roundness_score":    ("각진 얼굴형", "둥근 얼굴형"),
    "face_proportion_score":   ("가로형 얼굴", "세로형 얼굴"),
    "feature_size_score":      ("작은 이목구비", "큰 이목구비"),
    "feature_emphasis_score":  ("부드러운 인상", "강한 이목구비"),
    "mouth_curve_score":       ("차분한 표정", "밝은 미소"),
    "overall_symmetry":        ("개성 있는 비대칭", "뚜렷한 좌우 대칭"),
}

_IMPRESSION_LABELS = {
    "cute_score":      "귀여운 인상",
    "calm_score":      "차분한 인상",
    "smart_score":     "지적인 인상",
    "fierce_score":    "강렬한 인상",
    "gentle_score":    "온화한 인상",
    "lively_score":    "활기찬 인상",
    "innocent_score":  "순수한 인상",
    "confident_score": "당당한 인상",
    "unique_score":    "독특한 인상",
}


def _label(dim: str, value: float) -> str:
    if dim in _VISUAL_LABELS:
        lo, hi = _VISUAL_LABELS[dim]
        return hi if value >= 0.5 else lo
    return _IMPRESSION_LABELS.get(dim, dim)


def generate_reasons(
    user_visual: dict,
    user_impression: dict,
    pokemon_row: dict,
    top_n: int = 3,
) -> list[MatchReason]:
    """
    사용자 벡터와 포켓몬 벡터의 각 차원 차이를 계산해
    가장 유사한 상위 top_n개 차원을 근거로 반환
    """
    # 비교 대상 차원 목록
    comparisons: list[tuple[str, float, float, float]] = []

    # visual 10차원 비교
    for dim in _VISUAL_LABELS:
        u_val = float(user_visual.get(dim, 0.5))
        p_key = dim  # pokemon_row 컬럼명과 동일
        p_val = float(pokemon_row.get(p_key, 0.5))
        similarity = 1.0 - abs(u_val - p_val)
        comparisons.append((dim, u_val, p_val, similarity))

    # impression 9차원 비교
    imp_map = {
        "cute_score": "cute", "calm_score": "calm", "smart_score": "smart",
        "fierce_score": "fierce", "gentle_score": "gentle", "lively_score": "lively",
        "innocent_score": "innocent", "confident_score": "confident", "unique_score": "unique",
    }
    for p_key, u_key in imp_map.items():
        u_val = float(user_impression.get(u_key, 0.5))
        p_val = float(pokemon_row.get(p_key, 0.5))
        similarity = 1.0 - abs(u_val - p_val)
        comparisons.append((p_key, u_val, p_val, similarity))

    # 유사도 높은 순 정렬 후 top_n개 선택
    comparisons.sort(key=lambda x: x[3], reverse=True)
    top = comparisons[:top_n]

    return [
        MatchReason(
            dimension=dim,
            label=_label(dim, u_val),
            user_value=round(u_val, 3),
            pokemon_value=round(p_val, 3),
        )
        for dim, u_val, p_val, _ in top
    ]

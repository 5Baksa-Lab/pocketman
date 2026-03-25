"""
Step 1. PokeAPI 배치 수집 스크립트
대상: 1~3세대 포켓몬 #001 ~ #386
저장: pokemon_master, pokemon_stats 테이블
보완: 한국어 도감 설명 없으면 Fandom summary 수집 후 저장

실행 방법:
    python scripts/01_fetch_pokeapi.py
    python scripts/01_fetch_pokeapi.py --start 1 --end 30   # 범위 지정
    python scripts/01_fetch_pokeapi.py --dry-run             # DB 저장 없이 출력만
"""

import os
import time
import argparse
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 환경 설정
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

POKEAPI_BASE    = "https://pokeapi.co/api/v2"
FANDOM_API_BASE = "https://pokemon.fandom.com/api.php"
REQUEST_DELAY   = 0.15          # 초 (rate limit 방지)
MAX_RETRY       = 3             # 실패 시 재시도 횟수
RETRY_BACKOFF   = 2.0           # 재시도 간격 배수
POKEMON_START   = 1
POKEMON_END     = 386
COMMIT_BATCH_SIZE = 50

TYPE_KR = {
    "normal": "노말", "fire": "불꽃", "water": "물", "grass": "풀",
    "electric": "전기", "ice": "얼음", "fighting": "격투", "poison": "독",
    "ground": "땅", "flying": "비행", "psychic": "에스퍼", "bug": "벌레",
    "rock": "바위", "ghost": "고스트", "dragon": "드래곤", "dark": "악",
    "steel": "강철", "fairy": "페어리",
}

COLOR_KR = {
    "black": "검정", "blue": "파랑", "brown": "갈색", "gray": "회색",
    "green": "초록", "pink": "분홍", "purple": "보라", "red": "빨강",
    "white": "흰색", "yellow": "노랑",
}


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------
@dataclass
class PokemonMaster:
    pokemon_id:      int
    name_kr:         str
    name_en:         str
    name_jp:         Optional[str]
    generation:      int = 1
    pokedex_category: Optional[str] = None
    primary_type:    str  = ""
    secondary_type:  Optional[str] = None
    height_dm:       Optional[int] = None
    weight_hg:       Optional[int] = None
    color:           Optional[str] = None
    shape:           Optional[str] = None
    habitat:         Optional[str] = None
    is_legendary:    bool = False
    is_mythical:     bool = False
    pokedex_text_kr: Optional[str] = None
    sprite_url:      Optional[str] = None


@dataclass
class PokemonStats:
    pokemon_id:      int
    hp:              int
    attack:          int
    defense:         int
    special_attack:  int
    special_defense: int
    speed:           int


# ---------------------------------------------------------------------------
# API 호출 (재시도 포함)
# ---------------------------------------------------------------------------
def fetch_with_retry(
    client: httpx.Client,
    url: str,
    params: Optional[dict] = None,
) -> Optional[dict]:
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            log.warning(f"HTTP 오류 {e.response.status_code} | {url} | 시도 {attempt}/{MAX_RETRY}")
        except httpx.RequestError as e:
            log.warning(f"요청 오류 {e} | {url} | 시도 {attempt}/{MAX_RETRY}")

        if attempt < MAX_RETRY:
            sleep_time = REQUEST_DELAY * (RETRY_BACKOFF ** attempt)
            time.sleep(sleep_time)

    log.error(f"최대 재시도 초과: {url}")
    return None


# ---------------------------------------------------------------------------
# 이름 추출 헬퍼
# ---------------------------------------------------------------------------
def extract_name(names: list, lang: str) -> Optional[str]:
    for entry in names:
        if entry["language"]["name"] == lang:
            return entry["name"]
    return None


def extract_flavor_text(entries: list, lang: str = "ko") -> Optional[str]:
    """
    도감 설명 추출: 언어 필터 후 가장 최근 버전 반환
    줄바꿈·특수문자 정리 포함
    """
    texts = [
        e["flavor_text"]
        for e in entries
        if e["language"]["name"] == lang
    ]
    if not texts:
        return None
    # 가장 마지막(최신 버전) 텍스트 사용, 개행문자 정리
    raw = texts[-1]
    cleaned = raw.replace("\n", " ").replace("\f", " ").replace("\r", " ")
    return " ".join(cleaned.split())


def extract_genus(genera: list, lang: str = "ko") -> Optional[str]:
    for g in genera:
        if g["language"]["name"] == lang:
            return g["genus"]
    return None


def normalize_text(raw: str) -> str:
    cleaned = raw.replace("\n", " ").replace("\f", " ").replace("\r", " ").replace("\t", " ")
    return " ".join(cleaned.split())


def build_fandom_title_candidates(name_en: str) -> list[str]:
    base = (name_en or "").strip()
    if not base:
        return []

    candidates = [base]

    # PokeAPI name에서 성별 심볼이 풀려 있는 케이스 보정
    if base.endswith(" F"):
        candidates.append(base[:-2] + "♀")
    if base.endswith(" M"):
        candidates.append(base[:-2] + "♂")

    unique: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def extract_fandom_summary(payload: dict) -> Optional[str]:
    pages = payload.get("query", {}).get("pages", [])
    for page in pages:
        summary = page.get("extract")
        if summary:
            return normalize_text(summary)
    return None


def fetch_fandom_flavor_text(
    client: httpx.Client,
    name_en: str,
) -> Optional[str]:
    for title in build_fandom_title_candidates(name_en):
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
            "redirects": "1",
            "titles": title,
            "format": "json",
            "formatversion": "2",
        }
        payload = fetch_with_retry(client, FANDOM_API_BASE, params=params)
        if not payload:
            continue
        summary = extract_fandom_summary(payload)
        if summary:
            return summary
    return None


# ---------------------------------------------------------------------------
# 포켓몬 1마리 수집
# ---------------------------------------------------------------------------
def fetch_single_pokemon(
    client: httpx.Client,
    pokemon_id: int,
) -> tuple[Optional[PokemonMaster], Optional[PokemonStats]]:

    # --- 기본 정보 ---
    poke_url    = f"{POKEAPI_BASE}/pokemon/{pokemon_id}"
    species_url = f"{POKEAPI_BASE}/pokemon-species/{pokemon_id}"

    poke_data    = fetch_with_retry(client, poke_url)
    species_data = fetch_with_retry(client, species_url)

    if not poke_data or not species_data:
        log.error(f"#{pokemon_id} 수집 실패 - 건너뜀")
        return None, None

    # --- 이름 ---
    name_en = poke_data.get("name", "").replace("-", " ").title()
    name_kr = extract_name(species_data.get("names", []), "ko") or name_en
    name_jp = extract_name(species_data.get("names", []), "ja")

    # --- 타입 ---
    types = sorted(poke_data.get("types", []), key=lambda t: t["slot"])
    primary_type   = types[0]["type"]["name"] if len(types) >= 1 else "normal"
    secondary_type = types[1]["type"]["name"] if len(types) >= 2 else None

    primary_type_kr   = TYPE_KR.get(primary_type, primary_type)
    secondary_type_kr = TYPE_KR.get(secondary_type, secondary_type) if secondary_type else None

    # --- 종족치 ---
    stats_map = {s["stat"]["name"]: s["base_stat"] for s in poke_data.get("stats", [])}
    pokemon_stats = PokemonStats(
        pokemon_id      = pokemon_id,
        hp              = stats_map.get("hp", 0),
        attack          = stats_map.get("attack", 0),
        defense         = stats_map.get("defense", 0),
        special_attack  = stats_map.get("special-attack", 0),
        special_defense = stats_map.get("special-defense", 0),
        speed           = stats_map.get("speed", 0),
    )

    # --- 종(species) 정보 ---
    color_name   = species_data.get("color", {}).get("name")
    shape_name   = species_data.get("shape", {}).get("name") if species_data.get("shape") else None
    habitat_name = species_data.get("habitat", {}).get("name") if species_data.get("habitat") else None

    # --- 스프라이트 ---
    sprite_url = (
        poke_data.get("sprites", {}).get("front_default")
        or poke_data.get("sprites", {}).get("front_shiny")
    )

    # --- 도감 설명 ---
    # 우선순위: PokeAPI 한국어 → Fandom 보완 → PokeAPI 영어
    flavor_text = extract_flavor_text(
        species_data.get("flavor_text_entries", []), lang="ko"
    )
    if not flavor_text:
        flavor_text = fetch_fandom_flavor_text(client, name_en)
        if flavor_text:
            log.info(f"  도감 보완(Fandom): {name_en}")

    if not flavor_text:
        # Fandom도 실패하면 영어 설명으로 대체
        flavor_text = extract_flavor_text(
            species_data.get("flavor_text_entries", []), lang="en"
        )

    # --- 도감 분류 (genus) ---
    genus_kr = extract_genus(species_data.get("genera", []), lang="ko")
    if not genus_kr:
        genus_kr = extract_genus(species_data.get("genera", []), lang="en")

    pokemon_master = PokemonMaster(
        pokemon_id       = pokemon_id,
        name_kr          = name_kr,
        name_en          = name_en,
        name_jp          = name_jp,
        generation       = {"generation-i": 1, "generation-ii": 2, "generation-iii": 3}.get(
                               species_data.get("generation", {}).get("name", "generation-i"), 1),
        pokedex_category = genus_kr,
        primary_type     = primary_type_kr,
        secondary_type   = secondary_type_kr,
        height_dm        = poke_data.get("height"),
        weight_hg        = poke_data.get("weight"),
        color            = COLOR_KR.get(color_name, color_name),
        shape            = shape_name,
        habitat          = habitat_name,
        is_legendary     = species_data.get("is_legendary", False),
        is_mythical      = species_data.get("is_mythical", False),
        pokedex_text_kr  = flavor_text,
        sprite_url       = sprite_url,
    )

    return pokemon_master, pokemon_stats


# ---------------------------------------------------------------------------
# DB 저장
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def upsert_pokemon_master(cursor, p: PokemonMaster):
    sql = """
        INSERT INTO pokemon_master (
            pokemon_id, name_kr, name_en, name_jp, generation,
            pokedex_category, primary_type, secondary_type,
            height_dm, weight_hg, color, shape, habitat,
            is_legendary, is_mythical, pokedex_text_kr, sprite_url
        ) VALUES (
            %(pokemon_id)s, %(name_kr)s, %(name_en)s, %(name_jp)s, %(generation)s,
            %(pokedex_category)s, %(primary_type)s, %(secondary_type)s,
            %(height_dm)s, %(weight_hg)s, %(color)s, %(shape)s, %(habitat)s,
            %(is_legendary)s, %(is_mythical)s, %(pokedex_text_kr)s, %(sprite_url)s
        )
        ON CONFLICT (pokemon_id) DO UPDATE SET
            name_kr          = EXCLUDED.name_kr,
            name_en          = EXCLUDED.name_en,
            name_jp          = EXCLUDED.name_jp,
            pokedex_category = EXCLUDED.pokedex_category,
            primary_type     = EXCLUDED.primary_type,
            secondary_type   = EXCLUDED.secondary_type,
            height_dm        = EXCLUDED.height_dm,
            weight_hg        = EXCLUDED.weight_hg,
            color            = EXCLUDED.color,
            shape            = EXCLUDED.shape,
            habitat          = EXCLUDED.habitat,
            is_legendary     = EXCLUDED.is_legendary,
            is_mythical      = EXCLUDED.is_mythical,
            pokedex_text_kr  = EXCLUDED.pokedex_text_kr,
            sprite_url       = EXCLUDED.sprite_url,
            updated_at       = NOW();
    """
    cursor.execute(sql, p.__dict__)


def upsert_pokemon_stats(cursor, s: PokemonStats):
    sql = """
        INSERT INTO pokemon_stats (
            pokemon_id, hp, attack, defense,
            special_attack, special_defense, speed
        ) VALUES (
            %(pokemon_id)s, %(hp)s, %(attack)s, %(defense)s,
            %(special_attack)s, %(special_defense)s, %(speed)s
        )
        ON CONFLICT (pokemon_id) DO UPDATE SET
            hp              = EXCLUDED.hp,
            attack          = EXCLUDED.attack,
            defense         = EXCLUDED.defense,
            special_attack  = EXCLUDED.special_attack,
            special_defense = EXCLUDED.special_defense,
            speed           = EXCLUDED.speed;
    """
    cursor.execute(sql, s.__dict__)


# ---------------------------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------------------------
def run(start: int, end: int, dry_run: bool = False):
    log.info(f"===== PokeAPI 배치 수집 시작: #{start} ~ #{end} =====")

    success_count = 0
    fail_count    = 0
    fail_ids      = []

    conn   = None
    cursor = None

    if not dry_run:
        conn   = get_db_connection()
        cursor = conn.cursor()
        log.info("DB 연결 완료")
    pending_commits = 0

    with httpx.Client(headers={"User-Agent": "pokeman-project/1.0"}) as client:
        for pokemon_id in range(start, end + 1):
            log.info(f"수집 중: #{pokemon_id:03d}")

            master, stats = fetch_single_pokemon(client, pokemon_id)

            if master is None or stats is None:
                fail_count += 1
                fail_ids.append(pokemon_id)
                continue

            if dry_run:
                # 저장 없이 출력만
                log.info(
                    f"  [DRY-RUN] #{master.pokemon_id:03d} {master.name_kr} "
                    f"| {master.primary_type}"
                    f"{'/' + master.secondary_type if master.secondary_type else ''}"
                    f" | HP:{stats.hp} ATK:{stats.attack}"
                )
                success_count += 1
            else:
                cursor.execute("SAVEPOINT sp_fetch_row")
                try:
                    upsert_pokemon_master(cursor, master)
                    upsert_pokemon_stats(cursor, stats)
                    cursor.execute("RELEASE SAVEPOINT sp_fetch_row")
                    pending_commits += 1
                    if pending_commits >= COMMIT_BATCH_SIZE:
                        conn.commit()
                        pending_commits = 0
                    log.info(
                        f"  저장 완료: #{master.pokemon_id:03d} {master.name_kr} "
                        f"| {master.primary_type}"
                    )
                    success_count += 1
                except Exception as e:
                    cursor.execute("ROLLBACK TO SAVEPOINT sp_fetch_row")
                    cursor.execute("RELEASE SAVEPOINT sp_fetch_row")
                    log.error(f"  DB 저장 오류 #{pokemon_id}: {e}")
                    fail_count += 1
                    fail_ids.append(pokemon_id)

            # Rate limit 방지 딜레이
            time.sleep(REQUEST_DELAY)

    if not dry_run and conn and pending_commits > 0:
        conn.commit()

    if not dry_run and cursor:
        cursor.close()
    if not dry_run and conn:
        conn.close()

    # 결과 요약
    log.info("=" * 50)
    log.info(f"수집 완료 | 성공: {success_count} | 실패: {fail_count}")
    if fail_ids:
        log.warning(f"실패 목록: {fail_ids}")
        log.warning("위 번호들은 스크립트를 --start --end 로 범위 지정하여 재실행하세요.")
    log.info("=" * 50)


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PokeAPI Gen1~3 배치 수집 스크립트")
    parser.add_argument("--start",   type=int, default=POKEMON_START, help=f"시작 번호 (기본: {POKEMON_START})")
    parser.add_argument("--end",     type=int, default=POKEMON_END,   help=f"끝 번호   (기본: {POKEMON_END})")
    parser.add_argument("--dry-run", action="store_true",              help="DB 저장 없이 수집 결과만 출력")
    args = parser.parse_args()

    if args.start < 1 or args.end > 386 or args.start > args.end:
        parser.error("범위는 1~386 사이여야 하며 start <= end 이어야 합니다.")

    run(start=args.start, end=args.end, dry_run=args.dry_run)

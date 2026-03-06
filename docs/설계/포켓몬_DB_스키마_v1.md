# 포켓몬 데이터베이스 스키마 명세서 (1~3세대)

**작성일:** 2026년 3월 5일
**참고 API:** PokeAPI (v2), 전국도감 위키
**대상 범위:** 1세대(관동, 1~151) / 2세대(성도, 152~251) / 3세대(호연, 252~386) - 총 386마리

---

## 1. 개요 (DB 아키텍처)
본 스키마는 **관계형 데이터베이스(RDB - PostgreSQL/MySQL 등)** 사용을 가정하고 설계되었습니다. 
'Pokéman' 프로젝트에서 CV로 추출한 사용자 특징을 포켓몬의 '속성(타입)', '종족치(스탯)'와 매핑하기 위해 PokeAPI의 방대한 데이터 중 **매핑과 표출에 필수적인 데이터**만 추출하여 정규화했습니다.

---

## 2. 테이블 명세 (Tables)

### 2.1. `Pokemon` (포켓몬 기본 정보)
포켓몬의 가장 기본적인 식별 정보와 신체 데이터를 저장하는 핵심 테이블입니다.

| 컬럼명 (Column) | 데이터 타입 (Type) | 제약 조건 (Constraints) | 설명 (Description) | 예시 (Example) |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INT | PK | 전국도감 번호 (PokeAPI의 `id`) | `1` (이상해씨), `132` (메타몽) |
| `name_ko` | VARCHAR(50) | NOT NULL | 포켓몬 한국어 이름 | "메타몽" |
| `name_en` | VARCHAR(50) | NOT NULL | 포켓몬 영어 이름 | "ditto" |
| `generation` | INT | NOT NULL | 세대 (1, 2, 3 중 하나) | `1` |
| `height` | FLOAT | | 키 (미터 단위, API: `height / 10`) | `0.3` |
| `weight` | FLOAT | | 몸무게 (킬로그램 단위, API: `weight / 10`) | `4.0` |
| `image_url` | VARCHAR(255) | | 기본 스프라이트 또는 공식 일러스트 URL | `https://.../132.png` |

---

### 2.2. `Pokemon_Stats` (종족치 / 스탯)
CV 매핑 시 (예: 눈이 크면 시야가 넓음 $\rightarrow$ 특수공격 높음 등) 기준이 되는 포켓몬의 6가지 기본 스탯 정보입니다. 1:1 관계로 구성됩니다.

| 컬럼명 (Column) | 데이터 타입 (Type) | 제약 조건 (Constraints) | 설명 (Description) | 예시 (메타몽) |
| :--- | :--- | :--- | :--- | :--- |
| `pokemon_id` | INT | PK, FK | `Pokemon` 테이블 참조 | `132` |
| `hp` | INT | NOT NULL | 체력 | `48` |
| `attack` | INT | NOT NULL | 공격 | `48` |
| `defense` | INT | NOT NULL | 방어 | `48` |
| `special_attack`| INT | NOT NULL | 특수 공격 | `48` |
| `special_defense`|INT | NOT NULL | 특수 방어 | `48` |
| `speed` | INT | NOT NULL | 스피드 | `48` |

---

### 2.3. `Types` (타입 마스터)
포켓몬의 속성(불, 물, 풀 등)을 관리하는 정적 마스터 테이블입니다. (총 18개 타입)

| 컬럼명 (Column) | 데이터 타입 (Type) | 제약 조건 (Constraints) | 설명 (Description) |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | 타입 ID (PokeAPI 기준) |
| `name_ko` | VARCHAR(20) | NOT NULL | 타입 한국어 이름 (예: "노말", "불꽃") |
| `name_en` | VARCHAR(20) | NOT NULL | 타입 영어 이름 (예: "normal", "fire") |

---

### 2.4. `Pokemon_Types` (포켓몬-타입 다대다 연결)
포켓몬은 1개 또는 2개의 타입을 가질 수 있으므로, 다대다(N:M) 연결 테이블로 관리합니다.

| 컬럼명 (Column) | 데이터 타입 (Type) | 제약 조건 (Constraints) | 설명 (Description) |
| :--- | :--- | :--- | :--- |
| `pokemon_id` | INT | PK, FK | `Pokemon` 테이블 참조 |
| `type_id` | INT | PK, FK | `Types` 테이블 참조 |
| `slot` | INT | NOT NULL | 주타입(1) / 부타입(2) 구분 (PokeAPI `slot`) |

---

### 2.5. `Abilities` (특성 마스터) - *선택적 매핑 요소*
포켓몬의 특성(예: '유연', '심록')을 저장합니다. (생성형 AI 스토리 작성 시 아주 좋은 재료가 됩니다.)

| 컬럼명 (Column) | 데이터 타입 (Type) | 제약 조건 (Constraints) | 설명 (Description) |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK | 특성 ID |
| `name_ko` | VARCHAR(50) | NOT NULL | 특성 한국어 이름 |
| `name_en` | VARCHAR(50) | NOT NULL | 특성 영어 이름 (예: "limber") |

---

### 2.6. `Pokemon_Abilities` (포켓몬-특성 다대다 연결)
한 포켓몬이 여러 특성(일반 특성, 숨겨진 특성)을 가질 수 있습니다.

| 컬럼명 (Column) | 데이터 타입 (Type) | 제약 조건 (Constraints) | 설명 (Description) |
| :--- | :--- | :--- | :--- |
| `pokemon_id` | INT | PK, FK | `Pokemon` 테이블 참조 |
| `ability_id` | INT | PK, FK | `Abilities` 테이블 참조 |
| `is_hidden` | BOOLEAN | NOT NULL | 숨겨진 특성 여부 (`true` / `false`) |

---

## 3. 요약 (ERD 구조)
*   **1마리의 포켓몬(`Pokemon`)**은
*   **1개의 스탯 정보(`Pokemon_Stats`)**를 가지며,
*   **1~2개의 타입(`Types`)**을 가지고 (`Pokemon_Types`로 연결),
*   **1~3개의 특성(`Abilities`)**을 가집니다 (`Pokemon_Abilities`로 연결).

이 구조를 바탕으로 파이썬 스크립트(PokeAPI 크롤러)를 작성하면 1~3세대(1번~386번) 포켓몬 386마리의 데이터를 한 번에 수집하여 DB에 적재할 수 있습니다.

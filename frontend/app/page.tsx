"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createCreature,
  generateCreature,
  getCreature,
  getVeoJob,
  matchFace
} from "@/lib/api";
import {
  Creature,
  CreatureCreatePayload,
  GenerationResponse,
  MatchResponse,
  PokemonMatchResult
} from "@/lib/types";

type Step = "upload" | "select" | "generating" | "result";

const MAX_VEO_POLL_COUNT = 25;
const VEO_POLL_INTERVAL_MS = 3000;

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function buildInitialCreaturePayload(selected: PokemonMatchResult, isPublic: boolean): CreatureCreatePayload {
  return {
    matched_pokemon_id: selected.pokemon_id,
    match_rank: selected.rank,
    similarity_score: selected.similarity,
    match_reasons: selected.reasons as unknown as Record<string, unknown>[],
    name: `${selected.name_kr} 타입 크리처`,
    story: "생성 중입니다.",
    image_url: null,
    video_url: null,
    is_public: isPublic
  };
}

function toPublicPayload(creature: Creature, editedName: string): CreatureCreatePayload {
  return {
    matched_pokemon_id: creature.matched_pokemon_id,
    match_rank: creature.match_rank,
    similarity_score: creature.similarity_score,
    match_reasons: creature.match_reasons,
    name: editedName.trim() || creature.name,
    story: creature.story,
    image_url: creature.image_url,
    video_url: creature.video_url,
    is_public: true
  };
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "알 수 없는 오류가 발생했습니다.";
}

export default function HomePage() {
  const [step, setStep] = useState<Step>("upload");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [busyMessage, setBusyMessage] = useState<string>("");

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>("");

  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [selectedRank, setSelectedRank] = useState<number>(1);

  const [publishOnCreate, setPublishOnCreate] = useState<boolean>(true);
  const [createdCreatureId, setCreatedCreatureId] = useState<string>("");
  const [generated, setGenerated] = useState<GenerationResponse | null>(null);

  const [editedName, setEditedName] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);
  const [publishedCloneId, setPublishedCloneId] = useState<string>("");

  const selectedPokemon = useMemo<PokemonMatchResult | null>(() => {
    if (!matchResult) {
      return null;
    }
    return matchResult.top3.find((candidate) => candidate.rank === selectedRank) || null;
  }, [matchResult, selectedRank]);

  useEffect(() => {
    return () => {
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
      }
    };
  }, [imagePreview]);

  const handleImageChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setErrorMessage("");

    if (!file) {
      return;
    }

    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));

    setMatchResult(null);
    setSelectedRank(1);
    setGenerated(null);
    setCreatedCreatureId("");
    setEditedName("");
    setPublishedCloneId("");
    setStep("upload");
  };

  const handleMatch = async () => {
    if (!imageFile) {
      setErrorMessage("먼저 이미지 파일을 선택해 주세요.");
      return;
    }

    try {
      setErrorMessage("");
      setBusyMessage("얼굴 특징을 분석하고 Top-3를 계산 중입니다...");
      const result = await matchFace(imageFile);
      setMatchResult(result);
      setSelectedRank(result.top3[0]?.rank ?? 1);
      setStep("select");
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusyMessage("");
    }
  };

  const pollVeoAndRefresh = async (baseResult: GenerationResponse, creatureId: string) => {
    if (!baseResult.veo_job) {
      return baseResult;
    }

    let currentResult = baseResult;
    let status = baseResult.veo_job.status;

    for (let i = 0; i < MAX_VEO_POLL_COUNT; i += 1) {
      if (!["queued", "running"].includes(status)) {
        break;
      }

      setBusyMessage(`영상 생성 상태 확인 중... (${status}, ${i + 1}/${MAX_VEO_POLL_COUNT})`);
      await wait(VEO_POLL_INTERVAL_MS);

      const latestJob = await getVeoJob(baseResult.veo_job.id);
      status = latestJob.status;
      currentResult = { ...currentResult, veo_job: latestJob };

      if (status === "succeeded") {
        const refreshed = await getCreature(creatureId);
        currentResult = { ...currentResult, creature: refreshed };
        break;
      }

      if (["failed", "canceled"].includes(status)) {
        break;
      }
    }

    return currentResult;
  };

  const handleGenerate = async () => {
    if (!selectedPokemon) {
      setErrorMessage("Top-3에서 포켓몬을 선택해 주세요.");
      return;
    }

    try {
      setErrorMessage("");
      setStep("generating");
      setBusyMessage("선택 포켓몬으로 크리처 레코드를 생성 중입니다...");

      const created = await createCreature(buildInitialCreaturePayload(selectedPokemon, publishOnCreate));
      setCreatedCreatureId(created.id);

      setBusyMessage("Imagen/Gemini/Veo 생성 파이프라인을 실행 중입니다...");
      const generatedResult = await generateCreature(created.id);
      const finalResult = await pollVeoAndRefresh(generatedResult, created.id);

      setGenerated(finalResult);
      setEditedName(finalResult.creature.name);
      setStep("result");
      setBusyMessage("");
    } catch (error) {
      setStep("select");
      setBusyMessage("");
      setErrorMessage(getErrorMessage(error));
    }
  };

  const getShareUrl = (): string => {
    if (typeof window === "undefined") {
      return "";
    }
    const targetId = publishedCloneId || createdCreatureId;
    if (!targetId) {
      return `${window.location.origin}/plaza`;
    }
    return `${window.location.origin}/plaza?focus=${targetId}`;
  };

  const handleCopyUrl = async () => {
    try {
      const url = getShareUrl();
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setErrorMessage("클립보드 복사에 실패했습니다. 브라우저 권한을 확인해 주세요.");
    }
  };

  const handleShareTwitter = () => {
    const url = getShareUrl();
    const title = encodeURIComponent(`내 Pocketman 크리처: ${editedName || generated?.creature.name || "Pocket Creature"}`);
    const shareUrl = `https://twitter.com/intent/tweet?text=${title}&url=${encodeURIComponent(url)}`;
    window.open(shareUrl, "_blank", "noopener,noreferrer");
  };

  const handlePublishNow = async () => {
    if (!generated) {
      return;
    }

    if (generated.creature.is_public) {
      setPublishedCloneId(generated.creature.id);
      return;
    }

    try {
      setBusyMessage("현재 결과를 광장 공개용 크리처로 등록 중입니다...");
      const clone = await createCreature(toPublicPayload(generated.creature, editedName));
      setPublishedCloneId(clone.id);
      setBusyMessage("");
    } catch (error) {
      setBusyMessage("");
      setErrorMessage(getErrorMessage(error));
    }
  };

  const resetFlow = () => {
    setStep("upload");
    setErrorMessage("");
    setBusyMessage("");
    setImageFile(null);
    setImagePreview("");
    setMatchResult(null);
    setSelectedRank(1);
    setPublishOnCreate(true);
    setCreatedCreatureId("");
    setGenerated(null);
    setEditedName("");
    setPublishedCloneId("");
  };

  return (
    <div className="grid gap-6">
      <section className="section-card p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">업로드 → 매칭 → 생성</h1>
            <p className="mt-1 text-sm text-ink/80">
              얼굴 사진 업로드 후 Top-3를 고르고, 실제 백엔드 생성 파이프라인(Imagen/Gemini/Veo)을 호출합니다.
            </p>
          </div>
          <button
            type="button"
            onClick={resetFlow}
            className="rounded-full border border-ink/20 px-4 py-2 text-sm transition hover:border-point hover:text-point"
          >
            새로 시작
          </button>
        </div>

        <div className="grid gap-5 md:grid-cols-[1.2fr_1fr]">
          <div className="rounded-xl2 border border-ink/10 bg-white/80 p-4">
            <label htmlFor="face-file" className="mb-2 block text-sm font-semibold">
              얼굴 이미지 (JPEG/PNG/WebP, 10MB 이하)
            </label>
            <input
              id="face-file"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleImageChange}
              className="w-full rounded-lg border border-ink/20 bg-white px-3 py-2 text-sm"
            />

            {imagePreview ? (
              <div className="mt-4 overflow-hidden rounded-xl border border-ink/10 bg-panelSoft/70 p-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={imagePreview} alt="업로드 미리보기" className="mx-auto max-h-64 w-auto rounded-lg" />
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-ink/20 bg-panelSoft/40 p-10 text-center text-sm text-ink/70">
                아직 업로드된 이미지가 없습니다.
              </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleMatch}
                disabled={!imageFile || step === "generating"}
                className="rounded-full bg-point px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-95"
              >
                Top-3 매칭 시작
              </button>
              <label className="inline-flex items-center gap-2 text-sm text-ink/80">
                <input
                  type="checkbox"
                  checked={publishOnCreate}
                  onChange={(event) => setPublishOnCreate(event.target.checked)}
                />
                생성 완료 후 광장 공개 상태로 저장
              </label>
            </div>
          </div>

          <div className="rounded-xl2 border border-ink/10 bg-white/70 p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink/65">진행 상태</h2>
            <ol className="mt-3 space-y-2 text-sm">
              <li className={step === "upload" ? "font-semibold text-point" : "text-ink/75"}>1. 이미지 업로드</li>
              <li className={step === "select" ? "font-semibold text-point" : "text-ink/75"}>2. Top-3 선택</li>
              <li className={step === "generating" ? "font-semibold text-point" : "text-ink/75"}>3. 생성 파이프라인</li>
              <li className={step === "result" ? "font-semibold text-point" : "text-ink/75"}>4. 결과/공유</li>
            </ol>

            {busyMessage ? (
              <div className="mt-4 flex items-center gap-2 rounded-lg bg-panel px-3 py-2 text-sm text-ink/90">
                <span className="pulse-dot" />
                <span>{busyMessage}</span>
              </div>
            ) : null}

            {errorMessage ? (
              <p className="mt-4 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">{errorMessage}</p>
            ) : null}

            {createdCreatureId ? (
              <p className="mt-4 text-xs text-ink/70">현재 크리처 ID: {createdCreatureId}</p>
            ) : null}
          </div>
        </div>
      </section>

      {matchResult ? (
        <section className="section-card p-6">
          <div className="mb-4 flex items-end justify-between">
            <div>
              <h2 className="text-xl font-semibold">Top-3 포켓몬 선택</h2>
              <p className="text-sm text-ink/75">카드를 선택한 뒤 생성 파이프라인을 실행하세요.</p>
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!selectedPokemon || step === "generating"}
              className="rounded-full bg-pointAlt px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-95"
            >
              선택 포켓몬으로 생성
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {matchResult.top3.map((candidate) => {
              const active = candidate.rank === selectedRank;
              return (
                <button
                  key={candidate.pokemon_id}
                  type="button"
                  onClick={() => setSelectedRank(candidate.rank)}
                  className={`text-left rounded-xl2 border p-4 transition ${
                    active
                      ? "border-point bg-point/10 shadow-deck"
                      : "border-ink/10 bg-white/80 hover:border-point/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-semibold">
                      #{candidate.rank}
                    </span>
                    <span className="text-xs font-medium text-ink/65">유사도 {formatPercent(candidate.similarity)}</span>
                  </div>

                  <div className="mt-3 flex items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={candidate.sprite_url || "https://placehold.co/80x80/png?text=?"}
                      alt={candidate.name_kr}
                      className="h-16 w-16 rounded-lg bg-white object-contain p-1"
                    />
                    <div>
                      <p className="text-lg font-semibold">{candidate.name_kr}</p>
                      <p className="text-xs text-ink/70">{candidate.name_en}</p>
                      <p className="mt-1 text-xs text-ink/70">
                        {candidate.primary_type}
                        {candidate.secondary_type ? ` / ${candidate.secondary_type}` : ""}
                      </p>
                    </div>
                  </div>

                  <ul className="mt-3 space-y-1 text-xs text-ink/75">
                    {candidate.reasons.slice(0, 3).map((reason) => (
                      <li key={`${candidate.pokemon_id}-${reason.dimension}`}>• {reason.label}</li>
                    ))}
                  </ul>
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      {step === "result" && generated ? (
        <section className="section-card p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-semibold">생성 결과 / 공유</h2>
              <p className="text-sm text-ink/75">결과 확인 후 공유하고 광장 피드에서 반응을 확인할 수 있습니다.</p>
            </div>
            <Link href="/plaza" className="rounded-full border border-ink/20 px-4 py-2 text-sm hover:border-point hover:text-point">
              광장 피드 보기
            </Link>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
            <div className="rounded-xl2 border border-ink/10 bg-white/80 p-4">
              <label htmlFor="edited-name" className="block text-sm font-semibold">
                크리처 이름 (공유 텍스트용)
              </label>
              <input
                id="edited-name"
                type="text"
                value={editedName}
                onChange={(event) => setEditedName(event.target.value)}
                className="mt-2 w-full rounded-lg border border-ink/20 bg-white px-3 py-2"
              />

              <p className="mt-3 text-sm leading-6 text-ink/85">{generated.creature.story || "스토리가 아직 생성되지 않았습니다."}</p>

              <div className="mt-4 grid gap-2 text-xs text-ink/70 sm:grid-cols-3">
                <div className="rounded-lg bg-panel p-2">story: {generated.story.source}</div>
                <div className="rounded-lg bg-panel p-2">image: {generated.image.source}</div>
                <div className="rounded-lg bg-panel p-2">video: {generated.video.source}</div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleCopyUrl}
                  className="rounded-full bg-point px-4 py-2 text-sm font-semibold text-white"
                >
                  {copied ? "복사 완료" : "URL 복사"}
                </button>
                <button
                  type="button"
                  onClick={handleShareTwitter}
                  className="rounded-full bg-[#1d9bf0] px-4 py-2 text-sm font-semibold text-white"
                >
                  트위터 공유
                </button>
                <button
                  type="button"
                  onClick={handlePublishNow}
                  className="rounded-full bg-pointAlt px-4 py-2 text-sm font-semibold text-white"
                >
                  광장 등록
                </button>
              </div>

              <p className="mt-3 text-xs text-ink/65">
                공개 상태: {generated.creature.is_public || publishedCloneId ? "공개" : "비공개"}
                {publishedCloneId ? ` (등록 ID: ${publishedCloneId})` : ""}
              </p>
            </div>

            <div className="rounded-xl2 border border-ink/10 bg-white/80 p-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={generated.creature.image_url || "https://placehold.co/1024x1024/png?text=No+Image"}
                alt={editedName || generated.creature.name}
                className="h-72 w-full rounded-xl object-cover"
              />

              {generated.creature.video_url ? (
                <video className="mt-3 w-full rounded-xl" controls src={generated.creature.video_url} />
              ) : (
                <div className="mt-3 rounded-xl border border-dashed border-ink/20 bg-panel p-4 text-sm text-ink/70">
                  영상 URL이 아직 없습니다. Veo가 실패한 경우 CSS fallback 연출 상태입니다.
                </div>
              )}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

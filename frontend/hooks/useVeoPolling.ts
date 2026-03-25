"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { generateCreature, getVeoJob } from "@/lib/api";
import { VEO_POLL_INTERVAL_MS, MAX_VEO_POLL_COUNT } from "@/lib/constants";

export type VeoPollingState =
  | "init"
  | "triggering"
  | "polling"
  | "succeeded"
  | "failed"
  | "timeout";

interface UseVeoPollingOptions {
  creatureId: string;
  onSuccess: (creatureId: string) => void;
  onError: (message: string) => void;
}

export function useVeoPolling({ creatureId, onSuccess, onError }: UseVeoPollingOptions) {
  const [pollingState, setPollingState] = useState<VeoPollingState>("init");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollCountRef = useRef(0);
  const mountedRef = useRef(true);
  const inFlightRef = useRef(false); // 폴링 요청 중복 방지

  const clearPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (jobId: string) => {
      pollCountRef.current = 0;
      setPollingState("polling");

      intervalRef.current = setInterval(async () => {
        if (!mountedRef.current) {
          clearPolling();
          return;
        }

        pollCountRef.current += 1;

        // 타임아웃: MAX_VEO_POLL_COUNT 초과
        if (pollCountRef.current > MAX_VEO_POLL_COUNT) {
          clearPolling();
          setPollingState("timeout");
          onError("영상 생성에 시간이 너무 걸리고 있어요. 이미지로 결과를 확인하시겠어요?");
          return;
        }

        // in-flight 가드: 이전 요청 진행 중이면 스킵
        if (inFlightRef.current) return;
        inFlightRef.current = true;

        try {
          const job = await getVeoJob(jobId);

          if (!mountedRef.current) return;

          if (job.status === "succeeded") {
            clearPolling();
            setPollingState("succeeded");
            onSuccess(creatureId);
          } else if (job.status === "failed" || job.status === "canceled") {
            clearPolling();
            setPollingState("failed");
            // canceled는 에러가 아님 — image_url fallback 처리
            onSuccess(creatureId);
          }
          // queued / running → 폴링 계속
        } catch {
          // 네트워크 단절 등 — 폴링 계속 (다음 인터벌에서 재시도)
        } finally {
          inFlightRef.current = false;
        }
      }, VEO_POLL_INTERVAL_MS);
    },
    [creatureId, clearPolling, onSuccess, onError]
  );

  useEffect(() => {
    mountedRef.current = true;

    async function trigger() {
      setPollingState("triggering");
      try {
        const result = await generateCreature(creatureId);

        if (!mountedRef.current) return;

        if (!result.veo_job) {
          // veo_job null → image_url fallback (즉시 결과 페이지 이동)
          setPollingState("succeeded");
          onSuccess(creatureId);
          return;
        }

        startPolling(result.veo_job.id);
      } catch (err) {
        if (!mountedRef.current) return;
        setPollingState("failed");
        onError(err instanceof Error ? err.message : "크리처 생성에 실패했습니다.");
      }
    }

    void trigger();

    return () => {
      mountedRef.current = false;
      clearPolling();
    };
  }, [creatureId, startPolling, clearPolling, onSuccess, onError]);

  return { pollingState };
}

/**
 * ?next= 파라미터를 내부 경로로만 제한합니다.
 * 외부 URL(http://, //로 시작) 또는 빈 값은 fallback으로 대체합니다.
 */
export function getSafeNextPath(
  raw: string | null,
  fallback = "/upload"
): string {
  if (!raw) return fallback;
  // 내부 경로: /로 시작하되 //로 시작하지 않아야 함 (protocol-relative URL 차단)
  if (raw.startsWith("/") && !raw.startsWith("//")) return raw;
  return fallback;
}

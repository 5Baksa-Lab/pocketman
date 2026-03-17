export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="로딩 중"
      className={`h-5 w-5 animate-spin rounded-full border-2 border-point/30 border-t-point ${className}`}
    />
  )
}

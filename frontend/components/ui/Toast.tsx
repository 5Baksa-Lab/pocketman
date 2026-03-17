type ToastType = "error" | "success" | "info"

interface ToastProps {
  message: string
  type?: ToastType
  onClose?: () => void
}

const typeStyles: Record<ToastType, string> = {
  error: "bg-danger/10 text-danger border-danger/20",
  success: "bg-ok/10 text-ok border-ok/20",
  info: "bg-ink/10 text-ink/80 border-ink/20",
}

export function Toast({ message, type = "error", onClose }: ToastProps) {
  if (!message) return null
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${typeStyles[type]}`}
    >
      <span className="flex-1">{message}</span>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 opacity-60 hover:opacity-100"
        >
          ✕
        </button>
      )}
    </div>
  )
}

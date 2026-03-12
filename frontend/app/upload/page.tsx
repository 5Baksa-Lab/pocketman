"use client"

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { matchFace, ApiError } from "@/lib/api"
import { MatchResultStorage } from "@/lib/storage"
import { ACCEPTED_MIME_TYPES, MAX_FILE_SIZE_BYTES, MIN_IMAGE_DIMENSION } from "@/lib/constants"
import { Button } from "@/components/ui/Button"
import { Spinner } from "@/components/ui/Spinner"
import { Toast } from "@/components/ui/Toast"

type UploadStatus = "idle" | "validating" | "uploading" | "done"

async function validateImage(file: File): Promise<string | null> {
  if (!(ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type)) {
    return "JPG, PNG, WebP 파일만 업로드 가능합니다."
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "파일 크기가 10MB를 초과합니다."
  }
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(url)
      if (img.width < MIN_IMAGE_DIMENSION || img.height < MIN_IMAGE_DIMENSION) {
        resolve(`이미지 최소 크기는 ${MIN_IMAGE_DIMENSION}×${MIN_IMAGE_DIMENSION}px입니다.`)
      } else {
        resolve(null)
      }
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve("이미지를 읽을 수 없습니다.")
    }
    img.src = url
  })
}

export default function UploadPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string>("")
  const [status, setStatus] = useState<UploadStatus>("idle")
  const [error, setError] = useState<string>("")
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const selectFile = async (selected: File) => {
    setError("")
    setStatus("validating")

    const validationError = await validateImage(selected)
    if (validationError) {
      setError(validationError)
      setStatus("idle")
      return
    }

    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setStatus("idle")
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) void selectFile(selected)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) void selectFile(dropped)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const handleSubmit = async () => {
    if (!file) return

    try {
      setError("")
      setStatus("uploading")
      const result = await matchFace(file)
      MatchResultStorage.save(result)
      setStatus("done")
      router.push("/match")
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "얼굴을 찾지 못했습니다. 다른 사진을 사용해주세요."
      setError(message)
      setStatus("idle")
    }
  }

  const isBusy = status === "validating" || status === "uploading"

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-ink">사진을 업로드하세요</h1>
        <p className="mt-2 text-sm text-ink/70">정면을 바라보는 밝은 사진일수록 정확도가 높아집니다</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">

        {/* Upload Zone */}
        <div className="section-card p-5">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`relative cursor-pointer rounded-xl border-2 border-dashed transition ${
              isDragging
                ? "border-point bg-point/5"
                : "border-ink/20 hover:border-point/60 hover:bg-point/5"
            }`}
          >
            {preview ? (
              <div className="overflow-hidden rounded-xl">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={preview}
                  alt="업로드 미리보기"
                  className="mx-auto max-h-72 w-full object-contain"
                />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 p-12 text-ink/60">
                <span className="text-5xl">📸</span>
                <p className="text-sm font-medium">클릭하거나 여기에 사진을 끌어다 놓으세요</p>
                <p className="text-xs text-ink/40">JPG · PNG · WebP · 최대 10MB</p>
              </div>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            className="sr-only"
          />

          {error && (
            <div className="mt-3">
              <Toast message={error} type="error" onClose={() => setError("")} />
            </div>
          )}

          <div className="mt-4 flex gap-3">
            <Button
              onClick={handleSubmit}
              disabled={!file || isBusy}
              className="flex items-center gap-2"
            >
              {status === "uploading" ? (
                <>
                  <Spinner className="h-4 w-4" />
                  분석 중...
                </>
              ) : (
                "분석 시작 →"
              )}
            </Button>
            {file && (
              <Button
                variant="ghost"
                onClick={() => {
                  setFile(null)
                  setPreview("")
                  setError("")
                  if (fileInputRef.current) fileInputRef.current.value = ""
                }}
                disabled={isBusy}
              >
                다시 선택
              </Button>
            )}
          </div>
        </div>

        {/* Guide */}
        <div className="section-card p-5">
          <h2 className="text-base font-semibold text-ink">좋은 사진 고르는 법</h2>
          <ul className="mt-4 space-y-3 text-sm text-ink/80">
            {[
              { icon: "✅", text: "정면을 바라보는 사진" },
              { icon: "✅", text: "밝고 균일한 조명" },
              { icon: "✅", text: "얼굴이 크게 나온 사진" },
              { icon: "❌", text: "선글라스나 마스크 착용" },
              { icon: "❌", text: "측면 또는 후면 촬영" },
              { icon: "❌", text: "너무 어둡거나 역광" },
            ].map((item, i) => (
              <li key={i} className="flex items-center gap-2">
                <span>{item.icon}</span>
                <span>{item.text}</span>
              </li>
            ))}
          </ul>

          <div className="mt-6 rounded-xl bg-ink/5 px-4 py-3 text-xs text-ink/60">
            <strong className="text-ink/80">개인정보 안내</strong>
            <br />
            업로드된 사진은 분석 즉시 처리되며 저장되지 않습니다.
          </div>
        </div>
      </div>
    </div>
  )
}

"use client";

import { useRef, useState } from "react";
import { patchCreature } from "@/lib/api";
import { Toast } from "@/components/ui/Toast";

interface InlineEditableNameProps {
  creatureId: string;
  initialName: string;
  onSaved?: (newName: string) => void;
  /** 텍스트 색상 클래스 — 밝은 배경: "text-ink", 어두운 배경: "text-white" (기본값) */
  textColorClass?: string;
}

export default function InlineEditableName({
  creatureId,
  initialName,
  onSaved,
  textColorClass = "text-white",
}: InlineEditableNameProps) {
  const [name, setName] = useState(initialName);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(initialName);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function startEdit() {
    setDraft(name);
    setEditing(true);
    setError("");
    setTimeout(() => inputRef.current?.select(), 0);
  }

  function cancelEdit() {
    setEditing(false);
    setDraft(name);
    setError("");
  }

  async function save() {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === name) {
      cancelEdit();
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await patchCreature(creatureId, { name: trimmed });
      setName(updated.name);
      setEditing(false);
      onSaved?.(updated.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "이름 저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <button
        className="group flex items-center gap-1.5 text-left"
        onClick={startEdit}
        title="클릭하여 이름 편집"
      >
        <span className={`text-2xl font-black ${textColorClass} leading-tight`}>{name}</span>
        <span className={`${textColorClass} opacity-40 text-sm group-hover:opacity-70 transition`}>✎</span>
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void save();
            if (e.key === "Escape") cancelEdit();
          }}
          maxLength={40}
          disabled={saving}
          className="rounded-lg bg-white/10 px-3 py-1.5 text-xl font-black text-white
                     placeholder-white/40 outline-none ring-2 ring-white/40
                     focus:ring-white/80 disabled:opacity-60 w-full max-w-[220px]"
          autoFocus
        />
        <button
          onClick={() => void save()}
          disabled={saving}
          className="rounded-lg bg-white/20 px-3 py-1.5 text-sm font-semibold text-white
                     hover:bg-white/30 disabled:opacity-50 transition"
        >
          {saving ? "…" : "✓"}
        </button>
        <button
          onClick={cancelEdit}
          disabled={saving}
          className="rounded-lg px-3 py-1.5 text-sm font-semibold text-white/60
                     hover:text-white/90 disabled:opacity-50 transition"
        >
          ✕
        </button>
      </div>
      {error && <Toast message={error} type="error" onClose={() => setError("")} />}
    </div>
  );
}

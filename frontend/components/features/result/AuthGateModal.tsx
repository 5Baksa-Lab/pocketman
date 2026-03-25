"use client";

import { useRouter } from "next/navigation";
import Modal from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";

interface AuthGateModalProps {
  open: boolean;
  onClose: () => void;
  nextPath?: string; // 로그인 후 복귀 경로
}

export default function AuthGateModal({ open, onClose, nextPath }: AuthGateModalProps) {
  const router = useRouter();

  function goLogin() {
    const next = nextPath ? `?next=${encodeURIComponent(nextPath)}` : "";
    router.push(`/login${next}`);
  }

  function goSignup() {
    const next = nextPath ? `?next=${encodeURIComponent(nextPath)}` : "";
    router.push(`/signup${next}`);
  }

  return (
    <Modal open={open} onClose={onClose}>
      <div className="flex flex-col gap-5 p-6 text-center">
        <div className="text-4xl">🔒</div>
        <div>
          <h2 className="text-lg font-black text-ink">로그인이 필요해요</h2>
          <p className="mt-1.5 text-sm text-ink/60">
            저장하거나 광장에 공유하려면 계정이 있어야 해요.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Button className="w-full" onClick={goLogin}>
            로그인하기
          </Button>
          <Button variant="secondary" className="w-full" onClick={goSignup}>
            회원가입하기
          </Button>
        </div>
        <button
          onClick={onClose}
          className="text-xs text-ink/40 hover:text-ink/70 transition"
        >
          나중에 할게요
        </button>
      </div>
    </Modal>
  );
}

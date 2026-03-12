export default async function GeneratePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return (
    <div className="flex min-h-[calc(100vh-72px)] flex-col items-center justify-center px-4 text-center">
      <div className="text-5xl mb-4">⏳</div>
      <h1 className="text-2xl font-bold text-ink">크리처 생성 중</h1>
      <p className="mt-2 text-sm text-ink/60">F2 Stage에서 구현됩니다 — ID: {id}</p>
    </div>
  )
}

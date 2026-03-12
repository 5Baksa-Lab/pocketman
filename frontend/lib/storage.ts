import type { MatchResponse } from "./types"
import { SESSION_KEY_MATCH_RESULT } from "./constants"

export const MatchResultStorage = {
  save: (data: MatchResponse): void => {
    sessionStorage.setItem(SESSION_KEY_MATCH_RESULT, JSON.stringify(data))
  },
  load: (): MatchResponse | null => {
    if (typeof window === "undefined") return null
    const raw = sessionStorage.getItem(SESSION_KEY_MATCH_RESULT)
    return raw ? (JSON.parse(raw) as MatchResponse) : null
  },
  clear: (): void => {
    sessionStorage.removeItem(SESSION_KEY_MATCH_RESULT)
  },
}

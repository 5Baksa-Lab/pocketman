import type { AuthUser, MatchResponse } from "./types"
import {
  SESSION_KEY_ACCESS_TOKEN,
  SESSION_KEY_AUTH_USER,
  SESSION_KEY_MATCH_RESULT,
} from "./constants"

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

export const AuthStorage = {
  saveToken: (token: string): void => {
    if (typeof window === "undefined") return
    sessionStorage.setItem(SESSION_KEY_ACCESS_TOKEN, token)
  },
  loadToken: (): string | null => {
    if (typeof window === "undefined") return null
    return sessionStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
  },
  saveUser: (user: AuthUser): void => {
    if (typeof window === "undefined") return
    sessionStorage.setItem(SESSION_KEY_AUTH_USER, JSON.stringify(user))
  },
  loadUser: (): AuthUser | null => {
    if (typeof window === "undefined") return null
    const raw = sessionStorage.getItem(SESSION_KEY_AUTH_USER)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  },
  clear: (): void => {
    if (typeof window === "undefined") return
    sessionStorage.removeItem(SESSION_KEY_ACCESS_TOKEN)
    sessionStorage.removeItem(SESSION_KEY_AUTH_USER)
  },
  isLoggedIn: (): boolean => {
    if (typeof window === "undefined") return false
    return !!sessionStorage.getItem(SESSION_KEY_ACCESS_TOKEN)
  },
}

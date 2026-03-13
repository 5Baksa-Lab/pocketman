import {
  ApiEnvelope,
  AuthLoginPayload,
  AuthRegisterPayload,
  AuthResponse,
  AuthUser,
  Comment,
  CommentListResponse,
  Creature,
  CreatureCreatePayload,
  CreatureDetail,
  CreatureListResponse,
  CreaturePatchPayload,
  GenerationResponse,
  LikeResponse,
  MatchResponse,
  MyCreatureListResponse,
  NicknameAvailability,
  PasswordChangePayload,
  ReactionPayload,
  ReactionSummary,
  UserProfile,
  UserUpdatePayload,
  VeoJob
} from "@/lib/types";
import { AuthStorage } from "@/lib/storage";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit, withAuth = false): Promise<T> {
  const authHeaders: Record<string, string> = {};
  if (withAuth) {
    const token = AuthStorage.loadToken();
    if (token) authHeaders["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...authHeaders,
      ...(init?.headers || {})
    },
    cache: "no-store"
  });

  const body = (await parseJsonSafe(response)) as ApiEnvelope<T> | null;
  if (!response.ok) {
    const message = body?.message || `Request failed (${response.status})`;
    throw new ApiError(message, response.status, body?.error_code);
  }

  if (!body?.success) {
    const message = body?.message || "Unknown API error";
    throw new ApiError(message, response.status, body?.error_code);
  }

  return body.data;
}

export async function matchFace(file: File): Promise<MatchResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<MatchResponse>("/match", {
    method: "POST",
    body: formData
  });
}

export async function createCreature(payload: CreatureCreatePayload): Promise<Creature> {
  // withAuth=true: 로그인 상태면 user_id 저장, 비로그인이면 anonymous 크리처
  return request<Creature>(
    "/creatures",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    },
    true
  );
}

export async function getCreature(creatureId: string): Promise<Creature> {
  return request<Creature>(`/creatures/${creatureId}`);
}

export async function generateCreature(creatureId: string): Promise<GenerationResponse> {
  return request<GenerationResponse>(`/creatures/${creatureId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      regenerate_name_story: true,
      regenerate_image: true,
      trigger_video: true
    })
  });
}

export async function getVeoJob(jobId: string): Promise<VeoJob> {
  return request<VeoJob>(`/veo-jobs/${jobId}`);
}

export async function listPublicCreatures(limit: number, offset: number): Promise<CreatureListResponse> {
  return request<CreatureListResponse>(`/creatures/public?limit=${limit}&offset=${offset}`);
}

export async function createReaction(
  creatureId: string,
  payload: ReactionPayload
): Promise<{ id: string }> {
  return request<{ id: string }>(`/creatures/${creatureId}/reactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export async function getReactionSummary(creatureId: string): Promise<ReactionSummary> {
  return request<ReactionSummary>(`/creatures/${creatureId}/reactions/summary`);
}

export async function patchCreature(
  creatureId: string,
  payload: CreaturePatchPayload
): Promise<Creature> {
  return request<Creature>(
    `/creatures/${creatureId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    },
    true
  );
}

export async function getCreatureDetail(creatureId: string): Promise<CreatureDetail> {
  return request<CreatureDetail>(`/creatures/${creatureId}`, undefined, true);
}

export async function deleteCreature(creatureId: string): Promise<void> {
  return request<void>(`/creatures/${creatureId}`, { method: "DELETE" }, true);
}

export async function getMyCreatures(): Promise<MyCreatureListResponse> {
  return request<MyCreatureListResponse>("/creatures/my", undefined, true);
}

export async function getLikedCreatures(): Promise<MyCreatureListResponse> {
  return request<MyCreatureListResponse>("/creatures/liked", undefined, true);
}

export async function addLike(creatureId: string): Promise<LikeResponse> {
  return request<LikeResponse>(`/creatures/${creatureId}/like`, { method: "POST" }, true);
}

export async function removeLike(creatureId: string): Promise<LikeResponse> {
  return request<LikeResponse>(`/creatures/${creatureId}/like`, { method: "DELETE" }, true);
}

export async function listComments(creatureId: string, page = 1): Promise<CommentListResponse> {
  return request<CommentListResponse>(
    `/creatures/${creatureId}/comments?page=${page}&limit=20`,
    undefined,
    true
  );
}

export async function createComment(creatureId: string, content: string): Promise<Comment> {
  return request<Comment>(
    `/creatures/${creatureId}/comments`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    },
    true
  );
}

export async function deleteComment(creatureId: string, commentId: string): Promise<void> {
  return request<void>(
    `/creatures/${creatureId}/comments/${commentId}`,
    { method: "DELETE" },
    true
  );
}

// ── User Profile APIs ────────────────────────────────────────────────────────

export async function getMyProfile(): Promise<UserProfile> {
  return request<UserProfile>("/users/me", undefined, true);
}

export async function checkNickname(q: string): Promise<NicknameAvailability> {
  return request<NicknameAvailability>(`/users/check-nickname?q=${encodeURIComponent(q)}`, undefined, true);
}

export async function updateProfile(payload: UserUpdatePayload): Promise<UserProfile> {
  return request<UserProfile>(
    "/users/me",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    },
    true
  );
}

export async function changePassword(payload: PasswordChangePayload): Promise<void> {
  return request<void>(
    "/users/me/password",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    },
    true
  );
}

export async function deleteAccount(password?: string): Promise<void> {
  return request<void>(
    "/users/me",
    {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: password ?? null })
    },
    true
  );
}

// ── Auth APIs ────────────────────────────────────────────────────────────────

export async function register(payload: AuthRegisterPayload): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export async function login(payload: AuthLoginPayload): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export async function getMe(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me", undefined, true);
}

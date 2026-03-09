import {
  ApiEnvelope,
  Creature,
  CreatureCreatePayload,
  CreatureListResponse,
  GenerationResponse,
  MatchResponse,
  ReactionPayload,
  ReactionSummary,
  VeoJob
} from "@/lib/types";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
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
  return request<Creature>("/creatures", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
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

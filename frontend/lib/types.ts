export interface ApiEnvelope<T> {
  success: boolean;
  request_id?: string;
  duration_ms?: number;
  data: T;
  error_code?: string;
  message?: string;
}

export interface MatchReason {
  dimension: string;
  label: string;
  user_value: number;
  pokemon_value: number;
}

export interface PokemonMatchResult {
  rank: number;
  pokemon_id: number;
  name_kr: string;
  name_en: string;
  primary_type: string;
  secondary_type: string | null;
  sprite_url: string | null;
  similarity: number;
  reasons: MatchReason[];
}

export interface MatchResponse {
  top3: PokemonMatchResult[];
  user_vector: number[];
}

export interface Creature {
  id: string;
  matched_pokemon_id: number;
  match_rank: number;
  similarity_score: number;
  match_reasons: Record<string, unknown>[];
  name: string;
  story: string | null;
  image_url: string | null;
  video_url: string | null;
  is_public: boolean;
  created_at: string;
  matched_pokemon_name_kr?: string | null;
}

export interface CreatureListResponse {
  items: Creature[];
  limit: number;
  offset: number;
}

export interface CreatureCreatePayload {
  matched_pokemon_id: number;
  match_rank: number;
  similarity_score: number;
  match_reasons: Record<string, unknown>[];
  name: string;
  story: string | null;
  image_url: string | null;
  video_url: string | null;
  is_public: boolean;
}

export interface GenerationStepMeta {
  source: string;
  used_fallback: boolean;
  retries: number;
  message: string | null;
}

export interface VeoJob {
  id: string;
  creature_id: string;
  status: string;
  video_url: string | null;
  error_message: string | null;
  requested_at: string;
  updated_at: string;
}

export interface GenerationResponse {
  creature: Creature;
  veo_job: VeoJob | null;
  image: GenerationStepMeta;
  story: GenerationStepMeta;
  video: GenerationStepMeta;
}

export interface ReactionSummary {
  creature_id: string;
  counts: {
    emoji_type: string;
    count: number;
  }[];
  total: number;
}

export interface ReactionPayload {
  emoji_type: string;
}

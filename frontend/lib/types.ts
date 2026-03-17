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

export interface AuthUser {
  id: string;
  email: string;
  nickname: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface AuthRegisterPayload {
  email: string;
  password: string;
  nickname: string;
}

export interface AuthLoginPayload {
  email: string;
  password: string;
}

export interface CreaturePatchPayload {
  name?: string;
  is_public?: boolean;
}

// ── Creature Detail ──────────────────────────────────────────────────────────

export interface CreatureOwner {
  id: string;
  nickname: string;
}

export interface CreatureDetail extends Creature {
  primary_type?: string | null;
  secondary_type?: string | null;
  owner?: CreatureOwner | null;
  like_count: number;
  is_liked: boolean;
}

export interface LikeResponse {
  like_count: number;
}

// ── Comments ─────────────────────────────────────────────────────────────────

export interface CommentAuthor {
  id: string;
  nickname: string;
}

export interface Comment {
  id: string;
  content: string;
  author: CommentAuthor;
  created_at: string;
  is_mine: boolean;
}

export interface CommentListResponse {
  items: Comment[];
  total: number;
  page: number;
}

// ── My Page ───────────────────────────────────────────────────────────────────

export interface MyCreatureItem {
  id: string;
  name: string;
  is_public: boolean;
  image_url: string | null;
  created_at: string;
  matched_pokemon_name_kr?: string | null;
}

export interface MyCreatureListResponse {
  items: MyCreatureItem[];
  total: number;
}

export interface UserProfile {
  id: string;
  email: string;
  nickname: string;
  bio: string | null;
  avatar_url: string | null;
  avatar_creature_id: string | null;
  dark_mode: boolean;
  font_size: number;
  creature_count: number;
  like_received_count: number;
}

export interface UserUpdatePayload {
  name?: string;
  bio?: string;
  avatar_creature_id?: string | null;
  dark_mode?: boolean;
  font_size?: number;
}

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}

export interface NicknameAvailability {
  available: boolean;
}

// ── Plaza / Socket.io ─────────────────────────────────────────────────────────

export interface PlazaPlayer {
  sid: string;
  user_id: string;
  nickname: string;
  image_url: string | null;
  x: number;
  y: number;
}

export interface DMIncoming {
  from_sid: string;
  from_nickname: string;
  from_image_url: string | null;
}

export interface DMMessage {
  room_id: string;
  from_sid: string;
  message: string;
}

export interface DMRoom {
  room_id: string;
  peer_sid: string;
  peer_nickname: string;
  peer_image_url: string | null;
  messages: DMMessage[];
}

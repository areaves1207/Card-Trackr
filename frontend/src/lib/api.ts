/**
 * Thin fetch wrapper that automatically attaches the JWT from localStorage
 * and throws on non-2xx responses so callers don't have to check status.
 */

const BASE = "/api";

function getToken(): string | null {
  return localStorage.getItem("token");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }

  // 204 No Content has no body
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
}

export const auth = {
  register: (email: string, username: string, password: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/auth/me"),
};

// ─── Cards ───────────────────────────────────────────────────────────────────

export interface PokemonCard {
  id: number;
  api_id: string;
  name: string;
  set_name: string;
  set_id: string;
  collector_number: string;
  rarity: string | null;
  image_small: string | null;
  image_large: string | null;
}

export interface CardSearchResult {
  api_id: string;
  name: string;
  set_name: string;
  collector_number: string;
  rarity: string | null;
  image_small: string | null;
}

export const cards = {
  search: (q: string) =>
    request<CardSearchResult[]>(`/cards/search?q=${encodeURIComponent(q)}`),
};

// ─── Scan ────────────────────────────────────────────────────────────────────

export interface ScanResult {
  id: number;
  confidence: number | null;
  frame_timestamp: number | null;
  raw_ocr_name: string | null;
  raw_ocr_number: string | null;
  auto_added: boolean;
  pokemon_card: PokemonCard | null;
  candidates: CardSearchResult[];
}

export interface ScanSession {
  id: number;
  status: "pending" | "processing" | "complete" | "failed";
  source_type: "image" | "video";
  created_at: string;
  results: ScanResult[];
}

export const scan = {
  uploadImages: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<ScanSession>("/scan/images", { method: "POST", body: form });
  },

  uploadVideo: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ScanSession>("/scan/video", { method: "POST", body: form });
  },

  getSession: (id: number) => request<ScanSession>(`/scan/${id}`),

  confirm: (scan_result_id: number, pokemon_card_api_id: string, add_to_collection_id?: number) =>
    request("/scan/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scan_result_id, pokemon_card_api_id, add_to_collection_id }),
    }),
};

// ─── Collection ──────────────────────────────────────────────────────────────

export interface Collection {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface CollectionCard {
  id: number;
  quantity: number;
  condition: string | null;
  notes: string | null;
  added_at: string;
  pokemon_card: PokemonCard;
}

export const collection = {
  list: () => request<Collection[]>("/collection"),

  create: (name: string, description?: string) =>
    request<Collection>("/collection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    }),

  listCards: (collectionId: number) =>
    request<CollectionCard[]>(`/collection/${collectionId}/cards`),

  addCard: (collectionId: number, pokemon_card_api_id: string, quantity = 1, condition?: string) =>
    request<CollectionCard>("/collection/cards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection_id: collectionId, pokemon_card_api_id, quantity, condition }),
    }),

  updateCard: (entryId: number, data: { quantity?: number; condition?: string; notes?: string }) =>
    request<CollectionCard>(`/collection/cards/${entryId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  removeCard: (entryId: number) =>
    request<void>(`/collection/cards/${entryId}`, { method: "DELETE" }),
};

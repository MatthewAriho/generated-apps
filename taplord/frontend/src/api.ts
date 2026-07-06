import { getAuthHeaders, setToken } from "./auth";

const BASE = "/taplord/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  customHeaders?: Record<string, string>
): Promise<T> {
  const headers: Record<string, string> = {
    ...getAuthHeaders(),
    ...customHeaders,
  };
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ==================== Interfaces ====================

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface UserInfo {
  id: number;
  username: string;
  display_name: string;
  avatar_color: string;
  created_at: string;
  is_active: boolean;
}

export interface EventData {
  id: number;
  user_id: number;
  name: string;
  event_type: string;
  started_at: string;
  ended_at: string | null;
  is_active: boolean;
  blacked_out: boolean;
  vomited: boolean;
  venue_description: string | null;
  checkin_count?: number;
}

export interface CheckInData {
  id: number;
  event_id: number;
  user_id: number;
  beer_id: number | null;
  beer_name: string;
  beer_style: string | null;
  brewery: string | null;
  size_ml: number;
  rating: number | null;
  notes: string | null;
  photo_url: string | null;
  created_at: string;
}

export interface BeerData {
  id: number;
  name: string;
  brewery: string | null;
  style: string | null;
  abv: number | null;
  image_url: string | null;
  verified: boolean;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  display_name: string;
  avatar_color: string;
  value: number;
  label: string;
}

export interface ShameEntry {
  user_id: number;
  username: string;
  display_name: string;
  avatar_color: string;
  blackouts: number;
  vomits: number;
  total: number;
}

// ==================== Auth ====================

export const auth = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const form = new URLSearchParams({ username, password });
    const res = await fetch(`${BASE}/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, err.detail ?? "Login failed");
    }
    const data: TokenResponse = await res.json();
    setToken(data.access_token);
    return data;
  },

  async register(username: string, password: string, displayName?: string): Promise<TokenResponse> {
    const body: Record<string, string> = { username, password };
    if (displayName) body.display_name = displayName;
    const data = await request<TokenResponse>("POST", "/users/register", body);
    setToken(data.access_token);
    return data;
  },

  me(): Promise<UserInfo> {
    return request("GET", "/users/me");
  },
};

// ==================== Events ====================

export const events = {
  list(): Promise<EventData[]> {
    return request("GET", "/events");
  },

  active(): Promise<EventData | null> {
    return request<EventData | null>("GET", "/events/active").catch(() => null);
  },

  get(id: number): Promise<EventData> {
    return request("GET", `/events/${id}`);
  },

  start(name: string, eventType: string, venue?: string): Promise<EventData> {
    return request("POST", "/events", { name, event_type: eventType, venue_description: venue });
  },

  end(id: number): Promise<EventData> {
    return request("POST", `/events/${id}/end`);
  },

  update(id: number, data: Partial<{
    name: string;
    event_type: string;
    venue_description: string;
    blacked_out: boolean;
    vomited: boolean;
  }>): Promise<EventData> {
    return request("PATCH", `/events/${id}`, data);
  },

  delete(id: number): Promise<void> {
    return request("DELETE", `/events/${id}`);
  },
};

// ==================== Check-ins ====================

export const checkins = {
  list(eventId: number): Promise<CheckInData[]> {
    return request("GET", `/events/${eventId}/checkins`);
  },

  add(eventId: number, data: {
    beer_name: string;
    size_ml: number;
    beer_id?: number;
    beer_style?: string;
    brewery?: string;
    rating?: number;
    notes?: string;
  }): Promise<CheckInData> {
    return request("POST", `/events/${eventId}/checkins`, data);
  },

  repeat(eventId: number, checkinId: number): Promise<CheckInData> {
    return request("POST", `/events/${eventId}/checkins/${checkinId}/repeat`);
  },

  delete(checkinId: number): Promise<void> {
    return request("DELETE", `/checkins/${checkinId}`);
  },
};

// ==================== Beers ====================

export const beers = {
  search(query: string): Promise<BeerData[]> {
    return request("GET", `/beers/search?q=${encodeURIComponent(query)}`);
  },

  get(id: number): Promise<BeerData> {
    return request("GET", `/beers/${id}`);
  },

  create(data: { name: string; brewery?: string; style?: string; abv?: number }): Promise<BeerData> {
    return request("POST", "/beers", data);
  },
};

// ==================== Leaderboard ====================

export const leaderboard = {
  get(period: string = "week", category: string = "total_beers"): Promise<LeaderboardEntry[]> {
    return request("GET", `/leaderboard?period=${encodeURIComponent(period)}&category=${encodeURIComponent(category)}`);
  },

  shame(): Promise<ShameEntry[]> {
    return request("GET", "/leaderboard/shame");
  },
};

import { getAuthHeaders, setToken } from "./auth";

const BASE = "/api";

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

// ---- Auth ----

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  created_at: string;
  is_active: boolean;
}

export const auth = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const form = new URLSearchParams({ username, password });
    const res = await fetch(`${BASE}/auth/login`, {
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

  register(username: string, password: string): Promise<UserInfo> {
    return request("POST", "/auth/register", { username, password });
  },

  me(): Promise<UserInfo> {
    return request("GET", "/users/me");
  },
};

// ---- Books ----

export interface Book {
  id: number;
  title: string;
  author: string | null;
  isbn: string | null;
  cover_url: string | null;
  file_type: "epub" | "pdf";
  total_pages: number | null;
  total_words: number | null;
  genres: string[];
  added_at: string;
  shelf_status: "backlog" | "reading" | "read" | null;
  progress_percentage: number | null;
}

export const books = {
  list(): Promise<Book[]> {
    return request("GET", "/books");
  },
  get(id: number): Promise<Book> {
    return request("GET", `/books/${id}`);
  },
  upload(file: File): Promise<Book> {
    const form = new FormData();
    form.append("file", file);
    return request("POST", "/books/upload", form);
  },
  update(id: number, data: { title?: string; author?: string; genres?: string[] }): Promise<Book> {
    return request("PATCH", `/books/${id}`, data);
  },
  updateShelf(id: number, status: "backlog" | "reading" | "read", rating?: number): Promise<Book> {
    return request("POST", `/books/${id}/shelf`, { status, rating });
  },
  delete(id: number): Promise<void> {
    return request("DELETE", `/books/${id}`);
  },
};

// ---- Reader ----

export const reader = {
  getFileUrl(id: number): string {
    const token = localStorage.getItem("bookworm_token") ?? "";
    return `${BASE}/reader/${id}/file?token=${encodeURIComponent(token)}`;
  },
};

// ---- Progress ----

export interface Progress {
  book_id: number;
  position: string | null;
  percentage: number;
  updated_at: string;
}

export const progress = {
  get(id: number): Promise<Progress> {
    return request("GET", `/progress/${id}`);
  },
  update(
    id: number,
    position: string,
    percentage: number,
    words_read: number,
    pages_read: number,
    sessionStart: string | null,
    sessionEnd: string | null
  ): Promise<Progress> {
    return request("POST", `/progress/${id}`, {
      position,
      percentage,
      words_read,
      pages_read,
      session_start: sessionStart,
      session_end: sessionEnd,
    });
  },
};

// ---- Search ----

export interface SearchResult {
  guid: string;
  title: string;
  indexer: string;
  indexer_id: number;
  size: number;
  seeders: number;
  leechers: number;
  download_url: string | null;
  info_url: string | null;
  publish_date: string | null;
}

export const search = {
  prowlarr(q: string): Promise<{ results: SearchResult[] }> {
    return request("GET", `/search/prowlarr?q=${encodeURIComponent(q)}`);
  },
  download(guid: string, indexerId: number): Promise<unknown> {
    return request("POST", "/search/download", { guid, indexer_id: indexerId });
  },
};

// ---- Analytics ----

export interface AnalyticsOverview {
  total_books: number;
  books_read: number;
  books_reading: number;
  books_backlog: number;
  total_hours_read: number;
  total_words_read: number;
  avg_wpm: number;
  books_this_month: number;
}

export interface StreakData {
  current_streak: number;
  longest_streak: number;
  today_active: boolean;
  heatmap: { date: string; active: boolean }[];
}

export const analytics = {
  overview(): Promise<AnalyticsOverview> {
    return request("GET", "/analytics/overview");
  },
  speed(): Promise<{ week: string; wpm: number; hours: number }[]> {
    return request("GET", "/analytics/speed");
  },
  genres(): Promise<{ genre: string; count: number; percentage: number }[]> {
    return request("GET", "/analytics/genres");
  },
  sessions(): Promise<unknown[]> {
    return request("GET", "/analytics/sessions");
  },
  streak(): Promise<StreakData> {
    return request("GET", "/analytics/streak");
  },
};

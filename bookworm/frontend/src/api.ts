import { getAuthHeaders, setToken } from "./auth";

const BASE = "/bookworm/api";

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

export interface ReadingProfile {
  top_genres: { genre: string; count: number }[];
  books_finished: number;
  avg_days_per_book: number;
  total_hours_read: number;
  recommendations: {
    book_id: number;
    title: string;
    author: string | null;
    cover_url: string | null;
    reason: string;
  }[];
  search_suggestions: string[];
}

// ---- Social ----

export interface SocialUser {
  id: number;
  username: string;
}

export interface FriendshipData {
  id: number;
  user: SocialUser;
  status: string;
  created_at: string;
}

export interface ReadingGroupData {
  id: number;
  name: string;
  book_id: number;
  book_title: string;
  creator: string;
  member_count: number;
  members: SocialUser[];
  created_at: string;
}

export interface SharedHighlightData {
  id: number;
  user: SocialUser;
  book_id: number;
  cfi_range: string;
  text: string;
  note: string | null;
  color: string;
  created_at: string;
  comment_count: number;
}

export interface CommentData {
  id: number;
  user: SocialUser;
  text: string;
  created_at: string;
}

export interface ClubData {
  id: number;
  name: string;
  description: string | null;
  book_id: number | null;
  book_title: string | null;
  target_date: string | null;
  creator: string;
  member_count: number;
  members: SocialUser[];
  created_at: string;
}

export interface DiscussionData {
  id: number;
  user: SocialUser;
  title: string;
  body: string | null;
  reply_count: number;
  created_at: string;
}

export interface ReplyData {
  id: number;
  user: SocialUser;
  body: string;
  created_at: string;
}

export interface NotificationData {
  id: number;
  type: string;
  message: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface FeedItem {
  type: string;
  user: SocialUser;
  book_title?: string;
  book_id?: number;
  cover_url?: string | null;
  text?: string;
  timestamp: string;
}

export const social = {
  // Friends
  friends(): Promise<FriendshipData[]> { return request("GET", "/social/friends"); },
  friendRequests(): Promise<FriendshipData[]> { return request("GET", "/social/friends/requests"); },
  sendFriendRequest(username: string): Promise<FriendshipData> { return request("POST", "/social/friends/request", { username }); },
  acceptFriend(id: number): Promise<void> { return request("POST", `/social/friends/${id}/accept`); },
  removeFriend(id: number): Promise<void> { return request("DELETE", `/social/friends/${id}`); },
  viewFriendShelf(userId: number): Promise<any[]> { return request("GET", `/social/friends/${userId}/shelf`); },

  // Groups
  groups(): Promise<ReadingGroupData[]> { return request("GET", "/social/groups"); },
  createGroup(name: string, bookId: number): Promise<ReadingGroupData> { return request("POST", "/social/groups", { name, book_id: bookId }); },
  joinGroup(id: number): Promise<void> { return request("POST", `/social/groups/${id}/join`); },
  leaveGroup(id: number): Promise<void> { return request("POST", `/social/groups/${id}/leave`); },
  groupProgress(id: number): Promise<{ user: SocialUser; percentage: number }[]> { return request("GET", `/social/groups/${id}/progress`); },

  // Highlights
  shareHighlight(data: { book_id: number; cfi_range: string; text: string; note?: string; color?: string }): Promise<SharedHighlightData> {
    return request("POST", "/social/highlights", data);
  },
  bookHighlights(bookId: number): Promise<SharedHighlightData[]> { return request("GET", `/social/highlights/book/${bookId}`); },
  deleteHighlight(id: number): Promise<void> { return request("DELETE", `/social/highlights/${id}`); },
  highlightComments(id: number): Promise<CommentData[]> { return request("GET", `/social/highlights/${id}/comments`); },
  addComment(highlightId: number, text: string): Promise<CommentData> { return request("POST", `/social/highlights/${highlightId}/comments`, { text }); },

  // Clubs
  clubs(): Promise<ClubData[]> { return request("GET", "/social/clubs"); },
  discoverClubs(): Promise<ClubData[]> { return request("GET", "/social/clubs/discover"); },
  createClub(data: { name: string; description?: string; book_id?: number; target_date?: string }): Promise<ClubData> {
    return request("POST", "/social/clubs", data);
  },
  joinClub(id: number): Promise<void> { return request("POST", `/social/clubs/${id}/join`); },
  leaveClub(id: number): Promise<void> { return request("POST", `/social/clubs/${id}/leave`); },
  deleteClub(id: number): Promise<void> { return request("DELETE", `/social/clubs/${id}`); },

  // Discussions
  clubDiscussions(clubId: number): Promise<DiscussionData[]> { return request("GET", `/social/clubs/${clubId}/discussions`); },
  createDiscussion(clubId: number, title: string, body?: string): Promise<DiscussionData> {
    return request("POST", `/social/clubs/${clubId}/discussions`, { title, body });
  },
  discussionReplies(id: number): Promise<ReplyData[]> { return request("GET", `/social/discussions/${id}/replies`); },
  addReply(discussionId: number, body: string): Promise<ReplyData> {
    return request("POST", `/social/discussions/${discussionId}/replies`, { body });
  },

  // Notifications
  notifications(): Promise<NotificationData[]> { return request("GET", "/social/notifications"); },
  unreadCount(): Promise<{ count: number }> { return request("GET", "/social/notifications/unread-count"); },
  markAllRead(): Promise<void> { return request("POST", "/social/notifications/read-all"); },
  markRead(id: number): Promise<void> { return request("POST", `/social/notifications/${id}/read`); },

  // Feed & search
  feed(): Promise<FeedItem[]> { return request("GET", "/social/feed"); },
  searchUsers(q: string): Promise<SocialUser[]> { return request("GET", `/social/users/search?q=${encodeURIComponent(q)}`); },
};

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
  profile(): Promise<ReadingProfile> {
    return request("GET", "/analytics/profile");
  },
};

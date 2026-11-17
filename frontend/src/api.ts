export type Me = {
  id: number;
  username: string;
  role: "teacher" | "student";
  class_id: number;
  class_name: string;
  csrf_token: string;
};

export type MaterialItem = {
  id: number;
  title: string;
  created_at: string;
};

export type MaterialDetail = MaterialItem & {
  class_id: number;
  body: string;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string) {
    super(code);
    this.status = status;
    this.code = code;
  }
}

let csrfToken = "";

export function getCSRFToken() {
  return csrfToken;
}

export function setCSRFToken(token: string) {
  csrfToken = token;
}

export function clearCSRFToken() {
  csrfToken = "";
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const method = (init?.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrfToken && !headers.has("X-CSRF-Token")) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const res = await fetch(path, { ...init, headers, credentials: "include" });
  if (res.status === 401) {
    clearCSRFToken();
  }
  const text = await res.text();
  if (!res.ok) {
    let code = "request_failed";
    try {
      const parsed = JSON.parse(text) as { error?: string };
      if (parsed.error) code = parsed.error;
    } catch {
      code = "request_failed";
    }
    throw new ApiError(res.status, code);
  }
  return (text ? JSON.parse(text) : undefined) as T;
}

export type SearchHit = {
  material_id: number;
  title: string;
  chunk_index: number;
  start: number;
  end: number;
  excerpt: string;
  score?: number;
  rank?: number;
};

export type SearchResult = {
  mode: "keyword" | "vector" | "hybrid";
  message?: string;
  hits: SearchHit[];
};

export type AskResult = {
  answer: string;
  citations: SearchHit[];
};

export async function getMe() {
  const me = await api<Me>("/api/me");
  if (me.csrf_token) setCSRFToken(me.csrf_token);
  return me;
}

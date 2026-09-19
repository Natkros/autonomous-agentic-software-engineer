const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Repository {
  id: string;
  name: string;
  url: string;
  description: string | null;
  owner_id: string;
  created_at: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
  };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | { detail: string } | null;
    const message =
      body && "error" in body ? body.error.message : body && "detail" in body ? body.detail : response.statusText;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getHealth() {
  return request<{ status: string }>("/api/health");
}

export function register(email: string, password: string) {
  return request<{ id: string; email: string }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!response.ok) {
    throw new Error("Invalid email or password");
  }
  const data = (await response.json()) as { access_token: string };
  return data.access_token;
}

export function listRepositories(token: string) {
  return request<Repository[]>("/api/repositories", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createRepository(token: string, name: string, url: string, description?: string) {
  return request<Repository>("/api/repositories", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name, url, description }),
  });
}

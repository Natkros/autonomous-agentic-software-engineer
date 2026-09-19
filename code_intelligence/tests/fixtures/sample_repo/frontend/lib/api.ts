import { fetchJson } from "./http";

export interface LoginResponse {
  token: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return fetchJson("/auth/login", { email, password });
}

export class ApiClient {
  baseUrl: string;
}

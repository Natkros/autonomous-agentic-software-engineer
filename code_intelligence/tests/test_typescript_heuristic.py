from code_intelligence.ast_tools.typescript_heuristic import extract_symbols

SOURCE = '''
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
'''


def test_extracts_function_class_and_interface():
    symbols, _ = extract_symbols(SOURCE, "api.ts")
    kinds = {s.kind for s in symbols}
    names = {s.name for s in symbols}
    assert "function" in kinds and "login" in names
    assert "class" in kinds and "ApiClient" in names
    assert "interface" in kinds and "LoginResponse" in names


def test_extracts_import():
    _, imports = extract_symbols(SOURCE, "api.ts")
    assert len(imports) == 1
    assert imports[0].module == "./http"
    assert imports[0].names == ["fetchJson"]

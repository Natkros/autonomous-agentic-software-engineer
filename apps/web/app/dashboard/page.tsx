"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createRepository, listRepositories, Repository } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/");
      return;
    }
    listRepositories(token)
      .then(setRepositories)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load repositories"))
      .finally(() => setIsLoading(false));
  }, [router]);

  async function handleAddRepository(event: React.FormEvent) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    try {
      const repository = await createRepository(token, name, url);
      setRepositories((prev) => [...prev, repository]);
      setName("");
      setUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add repository");
    }
  }

  function handleSignOut() {
    clearToken();
    router.push("/");
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Repositories</h1>
        <button onClick={handleSignOut} className="text-sm text-gray-400 hover:text-gray-200">
          Sign out
        </button>
      </div>

      <form onSubmit={handleAddRepository} className="mt-6 flex gap-2 rounded-lg border border-border bg-surface p-4">
        <input
          placeholder="Repository name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-white outline-none focus:border-accent"
        />
        <input
          placeholder="Git URL"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-white outline-none focus:border-accent"
        />
        <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90">
          Add
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-6 space-y-2">
        {isLoading && <p className="text-sm text-gray-400">Loading...</p>}
        {!isLoading && repositories.length === 0 && (
          <p className="text-sm text-gray-400">No repositories yet. Add one above to get started.</p>
        )}
        {repositories.map((repo) => (
          <div key={repo.id} className="rounded-lg border border-border bg-surface p-4">
            <p className="font-medium text-white">{repo.name}</p>
            <p className="text-sm text-gray-400">{repo.url}</p>
          </div>
        ))}
      </div>
    </main>
  );
}

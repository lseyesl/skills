export async function fetchWithRetry(
  url: string,
  maxAttempts = 4,
  baseDelayMs = 200,
): Promise<Response> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const response = await fetch(url);
    if (response.ok || response.status < 500 && response.status !== 429) {
      return response;
    }

    const retryAfter = response.headers.get("Retry-After");
    const serverDelayMs = retryAfter ? Number(retryAfter) * 1000 : 0;
    const exponentialCap = baseDelayMs * 2 ** attempt;
    const fullJitterMs = Math.random() * exponentialCap;
    await new Promise((resolve) =>
      setTimeout(resolve, Math.max(serverDelayMs, fullJitterMs)),
    );
  }

  throw new Error(`request failed after ${maxAttempts} attempts`);
}

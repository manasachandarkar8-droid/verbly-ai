const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  endpoint: string,
  body: unknown,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();

  const timeout = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(
      `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
        cache: "no-store",
      },
    );

    const responseBody = await response.json().catch(() => null);

    if (!response.ok) {
      const detail =
        responseBody?.detail ??
        responseBody?.message ??
        `Backend request failed (${response.status})`;

      const message =
        typeof detail === "string"
          ? detail
          : "The backend rejected the request.";

      throw new ApiError(message, response.status, responseBody);
    }

    return responseBody as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("The backend request timed out.");
    }

    throw new Error(
      "Unable to communicate with the Verbly AI backend. Check that the backend server is running.",
    );
  } finally {
    clearTimeout(timeout);
  }
}
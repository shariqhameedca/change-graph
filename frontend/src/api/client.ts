const BASE_URL = "/api";

// A client-side backstop on top of the backend's own ~100s Bedrock timeout,
// so a genuinely stuck request (a stalled dev-server proxy, a backend that
// never responds at all) fails with a clear message instead of the UI
// spinning forever with no feedback. Compile no longer runs inline on the
// request -- POST .../compile returns a job id almost instantly, chunked
// LLM extraction happens in the background -- so this large timeout now
// mainly matters for other still-synchronous endpoints. Job-status polls
// use POLL_TIMEOUT_MS instead, since a poll that hangs should fail fast.
const DEFAULT_TIMEOUT_MS = 130_000;
const POLL_TIMEOUT_MS = 10_000;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function withTimeout(options: RequestInit, timeoutMs: number): { options: RequestInit; cancel: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return {
    options: { ...options, signal: controller.signal },
    cancel: () => clearTimeout(timer),
  };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // ignore body parse failures
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const { options: opts, cancel } = withTimeout(
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    },
    timeoutMs
  );

  try {
    const response = await fetch(`${BASE_URL}${path}`, opts);
    return await handleResponse<T>(response);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        408,
        `Request timed out after ${Math.round(timeoutMs / 1000)}s. The server may still be processing it in the background -- try again shortly.`
      );
    }
    throw err;
  } finally {
    cancel();
  }
}

async function requestForm<T>(path: string, formData: FormData, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  // No Content-Type header here on purpose: the browser sets
  // multipart/form-data with the correct boundary itself.
  const { options, cancel } = withTimeout({ method: "POST", body: formData }, timeoutMs);

  try {
    const response = await fetch(`${BASE_URL}${path}`, options);
    return await handleResponse<T>(response);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        408,
        `Request timed out after ${Math.round(timeoutMs / 1000)}s. The server may still be processing it in the background -- try again shortly.`
      );
    }
    throw err;
  } finally {
    cancel();
  }
}

export const api = {
  get: <T>(path: string, timeoutMs?: number) => request<T>(path, {}, timeoutMs),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  postForm: <T>(path: string, formData: FormData) => requestForm<T>(path, formData),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export { POLL_TIMEOUT_MS };

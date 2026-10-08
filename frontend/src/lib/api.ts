/**
 * Standard API client configured for Cyber Eco backend.
 * Uses credentials: 'include' for secure HttpOnly cookie session management.
 * Automatically fetches and includes CSRF token for state-changing requests.
 */

let cachedCsrfToken: string | null = null;

export async function getCsrfToken(): Promise<string> {
  if (cachedCsrfToken) return cachedCsrfToken;

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  try {
    const res = await fetch(`${baseUrl}/api/v1/auth/csrf/`, {
      method: 'GET',
      credentials: 'include',
    });
    const data = await res.json();
    cachedCsrfToken = data.csrfToken || '';
    return cachedCsrfToken || '';
  } catch {
    return '';
  }
}

export async function apiClient(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers: Record<string, string> = {
    'Accept': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const method = (options.method || 'GET').toUpperCase();
  const isMutation = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

  if (isMutation) {
    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    const token = await getCsrfToken();
    if (token) {
      headers['X-CSRFToken'] = token;
    }
  }

  let res = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  // If CSRF verification failed (e.g. cookie expired or changed), refresh token and retry once
  if (res.status === 403 && isMutation) {
    const clone = res.clone();
    try {
      const errorData = await clone.json();
      if (
        typeof errorData.detail === 'string' &&
        errorData.detail.toLowerCase().includes('csrf')
      ) {
        cachedCsrfToken = null;
        const freshToken = await getCsrfToken();
        if (freshToken) {
          headers['X-CSRFToken'] = freshToken;
          res = await fetch(url, {
            ...options,
            headers,
            credentials: 'include',
          });
        }
      }
    } catch {
      // Not JSON or cannot parse, proceed with initial response
    }
  }

  return res;
}

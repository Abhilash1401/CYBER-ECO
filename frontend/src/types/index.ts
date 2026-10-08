/**
 * Shared TypeScript types for the Cyber Eco frontend.
 * Types will be expanded as API endpoints are implemented.
 */

/** Standard API health check response. */
export interface HealthResponse {
  status: string;
}

/** Standard paginated API response wrapper. */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

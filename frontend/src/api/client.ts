/**
 * Humark API Client.
 *
 * Automatically manages session state in localStorage and attaches
 * the X-Session-ID header on all benchmark requests.
 */

import {
  AttemptReceipt,
  GameSessionResponse,
  NextChallengeResponse,
  RoundAdvanceResponse,
  ScorecardResponse,
  VerificationStatusResponse,
} from './types';

const SESSION_STORAGE_KEY = 'humark_session_id';

export class ApiError extends Error {
  public status: number;
  public statusText: string;
  public detail: string | unknown;

  constructor(status: number, statusText: string, detail: string | unknown) {
    const message = typeof detail === 'string' ? detail : `API Error ${status}: ${statusText}`;
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.detail = detail;
  }
}

class HumarkApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    // Empty baseUrl defaults to Vite proxy (/api)
    this.baseUrl = baseUrl;
  }

  /**
   * Retrieve active session identifier from localStorage.
   */
  public getSessionId(): string | null {
    try {
      return localStorage.getItem(SESSION_STORAGE_KEY);
    } catch {
      return null;
    }
  }

  /**
   * Persist session identifier to localStorage.
   */
  public setSessionId(id: string): void {
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, id);
    } catch (e) {
      console.warn('Unable to persist session ID to localStorage:', e);
    }
  }

  /**
   * Clear active session identifier from localStorage.
   */
  public clearSession(): void {
    try {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch (e) {
      console.warn('Unable to remove session ID from localStorage:', e);
    }
  }

  /**
   * Base fetch handler attaching headers and intercepting session ID.
   */
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = new Headers(options.headers || {});

    // Ensure JSON accept header
    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }

    // Attach Content-Type if payload present and not already provided
    if (options.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    // Attach X-Session-ID header if available
    const sessionId = this.getSessionId();
    if (sessionId && !headers.has('X-Session-ID')) {
      headers.set('X-Session-ID', sessionId);
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Check if the server sent an updated/created X-Session-ID
    const returnedSessionId = response.headers.get('X-Session-ID');
    if (returnedSessionId) {
      this.setSessionId(returnedSessionId);
    }

    if (!response.ok) {
      let errorDetail: unknown = response.statusText;
      try {
        const json = await response.json();
        errorDetail = json.detail || json.message || json;
      } catch {
        // Response is non-JSON or empty
      }
      throw new ApiError(response.status, response.statusText, errorDetail);
    }

    // For 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  }

  /**
   * Initialize or retrieve guest session (POST /api/sessions).
   */
  public async initSession(): Promise<GameSessionResponse> {
    const data = await this.request<GameSessionResponse>('/api/sessions', {
      method: 'POST',
    });
    if (data.id) {
      this.setSessionId(data.id);
    }
    return data;
  }

  /**
   * Retrieve active session state (GET /api/sessions/current).
   */
  public async getCurrentSession(): Promise<GameSessionResponse> {
    return this.request<GameSessionResponse>('/api/sessions/current', {
      method: 'GET',
    });
  }

  /**
   * Retrieve next unseen challenge in session (GET /api/challenges/next).
   */
  public async getNextChallenge(): Promise<NextChallengeResponse> {
    return this.request<NextChallengeResponse>('/api/challenges/next', {
      method: 'GET',
    });
  }

  /**
   * Submit attempt on challenge (POST /api/challenges/{challengeId}/attempt).
   */
  public async submitAttempt(
    challengeId: string,
    selectedVariant: 'A' | 'B',
    timeTakenMs: number
  ): Promise<AttemptReceipt> {
    return this.request<AttemptReceipt>(`/api/challenges/${challengeId}/attempt`, {
      method: 'POST',
      body: JSON.stringify({
        selected_variant: selectedVariant,
        time_taken_ms: Math.max(0, Math.round(timeTakenMs)),
      }),
    });
  }

  /**
   * Advance session to next round (POST /api/sessions/advance-round).
   */
  public async advanceRound(sessionId?: string): Promise<RoundAdvanceResponse> {
    const targetSessionId = sessionId || this.getSessionId();
    return this.request<RoundAdvanceResponse>('/api/sessions/advance-round', {
      method: 'POST',
      body: JSON.stringify({
        session_id: targetSessionId,
      }),
    });
  }

  /**
   * Retrieve benchmark scorecard (GET /api/scorecard or /api/scorecard/{sessionId}).
   */
  public async getScorecard(sessionId?: string): Promise<ScorecardResponse> {
    const targetSessionId = sessionId || this.getSessionId();
    const endpoint = targetSessionId ? `/api/scorecard/${targetSessionId}` : '/api/scorecard';
    return this.request<ScorecardResponse>(endpoint, {
      method: 'GET',
    });
  }

  /**
   * Retrieve verification track progress (GET /api/sessions/verification).
   */
  public async getVerificationStatus(sessionId?: string): Promise<VerificationStatusResponse> {
    const targetSessionId = sessionId || this.getSessionId();
    const query = targetSessionId ? `?session_id=${encodeURIComponent(targetSessionId)}` : '';
    return this.request<VerificationStatusResponse>(`/api/sessions/verification${query}`, {
      method: 'GET',
    });
  }

  /**
   * Clear session and force creation of a brand new run via POST /api/sessions/reset.
   */
  public async resetSession(): Promise<GameSessionResponse> {
    if (typeof document !== 'undefined') {
      document.cookie = 'humark_session_id=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
    this.clearSession();
    const data = await this.request<GameSessionResponse>('/api/sessions/reset', {
      method: 'POST',
    });
    if (data.id) {
      this.setSessionId(data.id);
    }
    return data;
  }
}

export const apiClient = new HumarkApiClient();
export default apiClient;

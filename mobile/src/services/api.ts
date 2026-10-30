/**
 * API Service for QUAN AI BRAIN Backend
 * Handles all HTTP requests and WebSocket connections
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  KnowledgeUnit,
  SearchParams,
  SearchResult,
  APIResponse,
  PaginatedResponse,
  AuthToken,
  User,
  SyncResult,
  LocalChange,
  Notification,
  WebSocketMessage,
} from '../types';

class APIService {
  private client: AxiosInstance;
  private wsUrl: string;
  private ws: WebSocket | null = null;
  private wsCallbacks: Map<string, Set<(msg: WebSocketMessage) => void>> = new Map();
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor(baseURL: string, wsBaseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.wsUrl = wsBaseURL;

    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.handleAuthError();
        }
        return Promise.reject(this.mapError(error));
      }
    );
  }

  // ==================== Authentication ====================

  async login(username: string, password: string): Promise<AuthToken> {
    const response = await this.client.post<APIResponse<AuthToken>>('/v1/auth/login', {
      username,
      password,
    });

    if (response.data.success && response.data.data) {
      this.storeTokens(response.data.data);
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Login failed');
  }

  async refreshToken(): Promise<AuthToken> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.client.post<APIResponse<AuthToken>>('/v1/auth/refresh', {
      refresh_token: refreshToken,
    });

    if (response.data.success && response.data.data) {
      this.storeTokens(response.data.data);
      return response.data.data;
    }

    throw new Error('Token refresh failed');
  }

  async logout(): Promise<void> {
    await this.client.post('/v1/auth/logout');
    this.clearTokens();
    this.closeWebSocket();
  }

  // ==================== Knowledge Units ====================

  async searchKnowledge(params: SearchParams): Promise<SearchResult> {
    const { query, filters, limit, offset, context } = params;

    const response = await this.client.post<APIResponse<SearchResult>>('/v1/memory/search', {
      q: query,
      ...filters,
      limit,
      offset,
      context,
    });

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Search failed');
  }

  async getKnowledgeUnit(id: string): Promise<KnowledgeUnit> {
    const response = await this.client.get<APIResponse<KnowledgeUnit>>(
      `/v1/memory/read/${id}`
    );

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Knowledge unit not found');
  }

  async createKnowledgeUnit(data: Partial<KnowledgeUnit>): Promise<KnowledgeUnit> {
    const response = await this.client.post<APIResponse<KnowledgeUnit>>(
      '/v1/memory/write',
      data
    );

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Failed to create knowledge unit');
  }

  async updateKnowledgeUnit(id: string, data: Partial<KnowledgeUnit>): Promise<KnowledgeUnit> {
    const response = await this.client.put<APIResponse<KnowledgeUnit>>(
      `/v1/memory/update/${id}`,
      data
    );

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Failed to update knowledge unit');
  }

  async deleteKnowledgeUnit(id: string): Promise<void> {
    const response = await this.client.delete<APIResponse<void>>(
      `/v1/memory/delete/${id}`
    );

    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to delete knowledge unit');
    }
  }

  async getKnowledgeStats(): Promise<any> {
    const response = await this.client.get<APIResponse<any>>('/v1/memory/stats');

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Failed to get stats');
  }

  // ==================== Context Management ====================

  async setContext(context: { project?: string; task?: string; user?: string }): Promise<void> {
    const response = await this.client.post<APIResponse<void>>('/v1/memory/context/set', {
      context,
    });

    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to set context');
    }
  }

  async getContext(): Promise<any> {
    const response = await this.client.get<APIResponse<any>>('/v1/memory/context/current');

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Failed to get context');
  }

  // ==================== Sync & Offline ====================

  async uploadChanges(changes: LocalChange[]): Promise<SyncResult> {
    const response = await this.client.post<APIResponse<SyncResult>>('/v1/sync/upload', {
      changes,
    });

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Sync upload failed');
  }

  async downloadChanges(since: string): Promise<LocalChange[]> {
    const response = await this.client.get<APIResponse<LocalChange[]>>(
      `/v1/sync/download?since=${since}`
    );

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Sync download failed');
  }

  async resolveConflict(conflictId: string, resolution: 'keep_local' | 'keep_remote' | 'merge'): Promise<void> {
    const response = await this.client.post<APIResponse<void>>('/v1/sync/resolve', {
      conflict_id: conflictId,
      resolution,
    });

    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Conflict resolution failed');
    }
  }

  // ==================== Notifications ====================

  async getNotifications(limit: number = 50): Promise<Notification[]> {
    const response = await this.client.get<APIResponse<Notification[]>>(
      `/v1/notifications?limit=${limit}`
    );

    if (response.data.success && response.data.data) {
      return response.data.data;
    }

    throw new Error(response.data.error?.message || 'Failed to get notifications');
  }

  async markNotificationRead(id: string): Promise<void> {
    const response = await this.client.post<APIResponse<void>>(
      `/v1/notifications/${id}/read`
    );

    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to mark notification as read');
    }
  }

  async markAllNotificationsRead(): Promise<void> {
    const response = await this.client.post<APIResponse<void>>('/v1/notifications/read-all');

    if (!response.data.success) {
      throw new Error(response.data.error?.message || 'Failed to mark all notifications as read');
    }
  }

  // ==================== WebSocket ====================

  connectWebSocket(onMessage: (msg: WebSocketMessage) => void): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    const token = this.getAccessToken();
    this.ws = new WebSocket(`${this.wsUrl}?token=${token}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        onMessage(message);
        this.notifyCallbacks(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      this.reconnect();
    };
  }

  disconnectWebSocket(): void {
    this.closeWebSocket();
  }

  subscribe(eventType: string, callback: (msg: WebSocketMessage) => void): void {
    if (!this.wsCallbacks.has(eventType)) {
      this.wsCallbacks.set(eventType, new Set());
    }
    this.wsCallbacks.get(eventType)!.add(callback);
  }

  unsubscribe(eventType: string, callback: (msg: WebSocketMessage) => void): void {
    const callbacks = this.wsCallbacks.get(eventType);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  private closeWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private reconnect(): void {
    if (this.reconnectTimer) return;

    this.reconnectTimer = setTimeout(() => {
      this.connectWebSocket((msg) => {
        // Re-register callbacks
        this.wsCallbacks.forEach((callbacks, type) => {
          callbacks.forEach((cb) => cb(msg));
        });
      });
    }, 5000);
  }

  private notifyCallbacks(message: WebSocketMessage): void {
    const callbacks = this.wsCallbacks.get(message.type);
    if (callbacks) {
      callbacks.forEach((cb) => cb(message));
    }
  }

  // ==================== Helper Methods ====================

  private getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  private storeTokens(token: AuthToken): void {
    localStorage.setItem('access_token', token.access_token);
    localStorage.setItem('refresh_token', token.refresh_token);
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  private handleAuthError(): void {
    // Clear tokens and redirect to login
    this.clearTokens();
    window.location.href = '/login';
  }

  private mapError(error: AxiosError): Error {
    if (error.response) {
      return new Error(error.response.data?.error?.message || 'Server error');
    } else if (error.request) {
      return new Error('Network error. Please check your connection.');
    } else {
      return new Error(error.message);
    }
  }
}

// Singleton instance
let apiService: APIService | null = null;

export function getAPIService(): APIService {
  if (!apiService) {
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8080';
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8080/ws';
    apiService = new APIService(apiUrl, wsUrl);
  }
  return apiService;
}

export default getAPIService;
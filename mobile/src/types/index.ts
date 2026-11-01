/**
 * Type definitions for QUAN AI BRAIN Mobile App
 */

// Knowledge Unit Types
export interface KnowledgeUnit {
  knowledge_id: string;
  knowledge_type: 'FACT' | 'QUESTION' | 'ANSWER' | 'EVENT' | 'LESSON_LEARNED' | 'BEST_PRACTICE' | 'DOCUMENT' | 'SUMMARY';
  subject: string;
  predicate: string;
  object: string;
  statement: string;
  scope: string;
  status: 'PENDING' | 'VERIFIED' | 'OBSOLETE' | 'CONFLICTED';
  confidence: number;
  valid_from?: string;
  valid_until?: string;
  created_at_utc: string;
  updated_at_utc: string;
  verification_status?: 'UNVERIFIED' | 'VERIFIED' | 'REJECTED';
  version?: number;
  superseded_by?: string;
  extraction_meta?: Record<string, any>;
  emotional_weight?: number;
  sentiment?: string;
  tags?: string[];
}

// Search & Filter Types
export interface SearchFilters {
  knowledge_type?: string[];
  scope?: string[];
  status?: string[];
  confidence_min?: number;
  confidence_max?: number;
  date_from?: string;
  date_to?: string;
  tags?: string[];
}

export interface SearchParams {
  query: string;
  filters: SearchFilters;
  limit: number;
  offset: number;
  context?: {
    project?: string;
    task?: string;
    user?: string;
  };
}

export interface SearchResult {
  results: KnowledgeUnit[];
  total: number;
  has_more: boolean;
  query_time_ms: number;
}

// User & Auth Types
export interface User {
  user_id: string;
  username: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  role: 'USER' | 'ADMIN' | 'MODERATOR';
  preferences: UserPreferences;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: 'en' | 'vi';
  notifications_enabled: boolean;
  offline_mode: boolean;
  sync_interval_minutes: number;
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
  scope: string;
}

// Sync & Offline Types
export interface SyncStatus {
  is_syncing: boolean;
  last_sync_time?: string;
  pending_changes: number;
  sync_error?: string;
  network_connected: boolean;
}

export interface LocalChange {
  change_id: string;
  entity_type: 'knowledge_unit' | 'relation' | 'user_preference';
  entity_id: string;
  operation: 'CREATE' | 'UPDATE' | 'DELETE';
  data: any;
  timestamp: string;
  synced: boolean;
}

export interface SyncResult {
  success: boolean;
  uploaded: number;
  downloaded: number;
  conflicts: number;
  errors: string[];
}

// Notification Types
export interface Notification {
  notification_id: string;
  type: 'NEW_KNOWLEDGE' | 'REVIEW_REMINDER' | 'SYNC_COMPLETED' | 'SYSTEM_ALERT' | 'CUSTOM';
  title: string;
  message: string;
  data?: Record<string, any>;
  priority: 'low' | 'normal' | 'high';
  read: boolean;
  created_at: string;
  action_url?: string;
}

export interface NotificationRule {
  rule_id: string;
  name: string;
  trigger_type: 'NEW_KNOWLEDGE' | 'TIME_BASED' | 'EVENT_BASED';
  conditions: Record<string, any>;
  notification_template: string;
  enabled: boolean;
  frequency_limit?: number; // per hour
  quiet_hours?: {
    start: string; // "22:00"
    end: string;   // "07:00"
  };
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'KNOWLEDGE_UPDATED' | 'KNOWLEDGE_CREATED' | 'SYNC_STATUS' | 'NOTIFICATION' | 'ERROR';
  payload: any;
  timestamp: string;
}

// API Response Types
export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    request_id: string;
    timestamp: string;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Form Types
export interface CreateKnowledgeForm {
  knowledge_type: KnowledgeUnit['knowledge_type'];
  subject: string;
  predicate: string;
  object: string;
  statement: string;
  scope: string;
  tags: string[];
}

export interface UpdateKnowledgeForm {
  knowledge_id: string;
  subject?: string;
  predicate?: string;
  object?: string;
  statement?: string;
  status?: KnowledgeUnit['status'];
  confidence?: number;
  tags?: string[];
}

// Stats & Analytics Types
export interface KnowledgeStats {
  total_knowledge_units: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  by_scope: Record<string, number>;
  avg_confidence: number;
  recent_24h: number;
  recent_7d: number;
  recent_30d: number;
}

export interface ActivityLog {
  log_id: string;
  user_id: string;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'SEARCH' | 'VIEW' | 'SYNC';
  entity_type: string;
  entity_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  retryable?: boolean;
}

export enum ErrorCode {
  NETWORK_ERROR = 'NETWORK_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  SYNC_ERROR = 'SYNC_ERROR',
  OFFLINE_ERROR = 'OFFLINE_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
}
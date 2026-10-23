// Shared, cross-domain types. Anticipates FastAPI response shapes so the
// service layer swap in Phase 2 requires no type changes.

export type Severity = 'low' | 'medium' | 'high';

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export type EvidenceStatus = 'pending' | 'available' | 'failed' | 'expired';
export type CloudUploadStatus = 'pending' | 'uploading' | 'uploaded' | 'failed' | 'not_applicable';

export interface Evidence {
  id: string;
  incidentId: string;
  safetyEventId?: string;
  driverId: string;
  vehicleId?: string;
  tripId?: string;
  fileType: string;
  fileSizeBytes: number;
  durationSeconds?: number;
  preEventSeconds: number;
  postEventSeconds: number;
  retentionDays: number;
  isProtected: boolean;
  status: EvidenceStatus;
  errorMessage?: string;
  sha256Hash?: string;
  cloudUploadStatus: CloudUploadStatus;
  createdAt: string;
  eventTimestamp?: string;
  downloadUrl: string;
  streamUrl?: string;
  snapshotUrl?: string;
}

export interface EvidenceHashVerifyResult {
  evidenceId: string;
  matches: boolean;
  storedHash: string | null;
  computedHash: string | null;
  details: string;
}

export interface EvidenceStorageStats {
  usedBytes: number;
  maxBytes: number;
  usedMb: number;
  maxMb: number;
  reservedMb: number;
  activeRecordings: number;
  quotaPercentage: number;
  isQuotaExceeded: boolean;
  retentionDays: number;
}

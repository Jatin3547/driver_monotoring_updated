import type { Evidence, EvidenceHashVerifyResult, EvidenceStorageStats } from '@/types';
import { API_BASE_URL, USE_MOCK_DATA, mockDelay } from '../config';
import { apiClient } from './client';
import { getStoredToken } from './authService';

export async function getEvidence(evidenceId: string): Promise<Evidence> {
  if (USE_MOCK_DATA) {
    return mockDelay({
      id: evidenceId,
      incidentId: 'INC-MOCK',
      driverId: 'DRV-001',
      fileType: 'video/mp4',
      fileSizeBytes: 2450000,
      durationSeconds: 15.0,
      preEventSeconds: 5.0,
      postEventSeconds: 10.0,
      retentionDays: 7,
      isProtected: false,
      status: 'available',
      cloudUploadStatus: 'pending',
      createdAt: new Date().toISOString(),
      downloadUrl: `/api/evidence/${evidenceId}/download`,
      streamUrl: `/api/evidence/${evidenceId}/stream`,
    });
  }
  return apiClient.get<Evidence>(`/evidence/${evidenceId}`);
}

export async function getEvidenceByIncident(incidentId: string): Promise<Evidence | null> {
  if (USE_MOCK_DATA) {
    return null;
  }
  try {
    return await apiClient.get<Evidence>(`/evidence/incident/${incidentId}`);
  } catch {
    return null;
  }
}

export async function uploadIncidentEvidence(
  incidentId: string,
  videoBlob: Blob,
  snapshotBlob?: Blob,
  preEventSeconds = 5.0,
  postEventSeconds = 10.0,
  eventTimestamp?: string
): Promise<Evidence> {
  const formData = new FormData();
  formData.append('video', videoBlob, 'recording.webm');
  if (snapshotBlob) {
    formData.append('snapshot', snapshotBlob, 'snapshot.jpg');
  }
  formData.append('pre_event_seconds', preEventSeconds.toString());
  formData.append('post_event_seconds', postEventSeconds.toString());
  if (eventTimestamp) {
    formData.append('event_timestamp', eventTimestamp);
  }

  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/evidence/upload/${incidentId}`, {
    method: 'POST',
    body: formData,
    headers,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errorBody}`);
  }

  return res.json() as Promise<Evidence>;
}

export async function verifyEvidenceHash(evidenceId: string): Promise<EvidenceHashVerifyResult> {
  if (USE_MOCK_DATA) {
    return mockDelay({
      evidenceId,
      matches: true,
      storedHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      computedHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      details: 'Mock hash verified successfully',
    });
  }
  return apiClient.get<EvidenceHashVerifyResult>(`/evidence/${evidenceId}/verify-hash`);
}

export async function toggleEvidenceProtection(
  evidenceId: string,
  isProtected: boolean
): Promise<Evidence> {
  if (USE_MOCK_DATA) {
    return mockDelay({
      id: evidenceId,
      incidentId: 'INC-MOCK',
      driverId: 'DRV-001',
      fileType: 'video/mp4',
      fileSizeBytes: 2450000,
      durationSeconds: 15.0,
      preEventSeconds: 5.0,
      postEventSeconds: 10.0,
      retentionDays: 7,
      isProtected,
      status: 'available',
      cloudUploadStatus: 'pending',
      createdAt: new Date().toISOString(),
      downloadUrl: `/api/evidence/${evidenceId}/download`,
    });
  }
  return apiClient.patch<Evidence>(`/evidence/${evidenceId}/protect`, { isProtected });
}

export async function getEvidenceStorageStats(): Promise<EvidenceStorageStats> {
  if (USE_MOCK_DATA) {
    return mockDelay({
      usedBytes: 42000000,
      maxBytes: 524288000,
      usedMb: 40.05,
      maxMb: 500,
      reservedMb: 25.0,
      activeRecordings: 0,
      quotaPercentage: 8.0,
      isQuotaExceeded: false,
      retentionDays: 7,
    });
  }
  return apiClient.get<EvidenceStorageStats>('/evidence/storage-stats');
}

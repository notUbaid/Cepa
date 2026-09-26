import { Platform } from 'react-native';
import { getApiBaseUrl } from '../config';
import {
  InspectionDetail,
  InspectionSummary,
  OnionInstanceDetail,
  ReportDetail,
  SampleDetail,
} from '../types';

export class ApiClient {
  private static async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          Accept: 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errJson = await response.json();
          errorDetail = errJson.detail || JSON.stringify(errJson);
        } catch {
          // Keep response.statusText
        }
        throw new Error(`HTTP ${response.status}: ${errorDetail}`);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      console.warn(`[ApiClient] Request to ${url} failed:`, err.message);
      throw err;
    }
  }

  static async checkHealth(): Promise<{ status: string; service: string }> {
    return this.request<{ status: string; service: string }>('/api/v1/health');
  }

  static async checkCvHealth(): Promise<{
    status: string;
    seg_provider: string;
    defect_classifier: string;
    active_policy: string;
    warning?: string;
  }> {
    return this.request('/api/v1/health/cv');
  }

  static async listInspections(): Promise<InspectionSummary[]> {
    return this.request<InspectionSummary[]>('/api/v1/inspections');
  }

  static async createInspection(data: {
    lot_id?: string;
    procurement_centre?: string;
    officer_name?: string;
    officer_id?: string;
    notes?: string;
    geo_lat?: number;
    geo_lon?: number;
    location_accuracy?: number;
  }): Promise<InspectionDetail> {
    return this.request<InspectionDetail>('/api/v1/inspections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  static async getInspection(id: string): Promise<InspectionDetail> {
    return this.request<InspectionDetail>(`/api/v1/inspections/${id}`);
  }

  static getDemoSampleUrl(): string {
    return `${getApiBaseUrl()}/api/v1/demo/sample-image`;
  }

  static getPrintableBoardUrl(): string {
    return `${getApiBaseUrl()}/ui/charuco_board_7x5_40mm_A4_printable.pdf`;
  }

  static async uploadSample(
    inspectionId: string,
    fileUri: string,
    location?: { lat?: number; lon?: number; accuracy?: number }
  ): Promise<SampleDetail> {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}/api/v1/inspections/${inspectionId}/samples`;

    const formData = new FormData();
    const rawFilename = fileUri.split('/').pop()?.split('?')[0] || 'sample.jpg';
    const filename = rawFilename.includes('.') ? rawFilename : `${rawFilename}.jpg`;
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1].toLowerCase()}` : 'image/jpeg';

    if (Platform.OS === 'web') {
      try {
        const fileRes = await fetch(fileUri);
        const blob = await fileRes.blob();
        formData.append('file', blob, filename);
      } catch (blobErr) {
        console.warn('Direct blob fetch failed, checking base64 fallback:', blobErr);
        const base64Match = fileUri.match(/^data:([^;]+);base64,(.+)$/);
        if (base64Match) {
          const byteCharacters = atob(base64Match[2]);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], { type: base64Match[1] });
          formData.append('file', blob, filename);
        } else {
          formData.append('file', fileUri);
        }
      }
    } else {
      formData.append('file', {
        uri: fileUri,
        name: filename,
        type,
      } as any);
    }

    if (location?.lat !== undefined) formData.append('geo_lat', location.lat.toString());
    if (location?.lon !== undefined) formData.append('geo_lon', location.lon.toString());
    if (location?.accuracy !== undefined) {
      formData.append('location_accuracy', location.accuracy.toString());
    }

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const errText = await response.text();
      let humanMsg = `Upload failed (${response.status})`;
      try {
        const parsed = JSON.parse(errText);
        if (parsed.detail) {
          if (typeof parsed.detail === 'string') {
            humanMsg = parsed.detail;
          } else if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) {
            humanMsg = parsed.detail[0].msg;
          }
        }
      } catch {
        // use default
      }
      throw new Error(humanMsg);
    }

    return (await response.json()) as SampleDetail;
  }

  static async getSample(inspectionId: string, sampleId: string): Promise<SampleDetail> {
    return this.request<SampleDetail>(`/api/v1/inspections/${inspectionId}/samples/${sampleId}`);
  }

  static async getOnionDetail(
    inspectionId: string,
    onionId: string
  ): Promise<OnionInstanceDetail> {
    return this.request<OnionInstanceDetail>(
      `/api/v1/inspections/${inspectionId}/onions/${onionId}`
    );
  }

  static async correctOnion(
    inspectionId: string,
    onionId: string,
    correction: {
      damaged_prob: number;
      rotten_prob: number;
      sprouted_prob: number;
      corrected_by: string;
      notes?: string;
    }
  ): Promise<OnionInstanceDetail> {
    return this.request<OnionInstanceDetail>(
      `/api/v1/inspections/${inspectionId}/onions/${onionId}/correct`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(correction),
      }
    );
  }

  static async finalizeInspection(inspectionId: string): Promise<InspectionDetail> {
    return this.request<InspectionDetail>(`/api/v1/inspections/${inspectionId}/finalize`, {
      method: 'POST',
    });
  }

  static async generateReport(inspectionId: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/api/v1/inspections/${inspectionId}/reports`, {
      method: 'POST',
    });
  }

  static async getReport(inspectionId: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/api/v1/inspections/${inspectionId}/reports`);
  }
}

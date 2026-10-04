import { Platform } from 'react-native';
import { getApiBaseUrl, getOfficerToken } from '../config';
import {
  InspectionDetail,
  InspectionSummary,
  OnionInstanceDetail,
  ReportDetail,
  SampleDetail,
  VideoScanResult,
} from '../types';

export class ApiClient {
  private static async request<T>(
    endpoint: string,
    options?: RequestInit & { timeoutMs?: number; retryCount?: number }
  ): Promise<T> {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}${endpoint}`;
    const officerToken = getOfficerToken();
    const isHeavyEndpoint = endpoint.includes('/samples') || endpoint.includes('/video');
    const timeoutMs = options?.timeoutMs ?? (isHeavyEndpoint ? 120000 : 45000);
    const maxRetries = options?.retryCount ?? (options?.method && options.method !== 'GET' ? 0 : 1);

    let lastError: any = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const response = await fetch(url, {
          ...options,
          signal: options?.signal || controller.signal,
          headers: {
            Accept: 'application/json',
            ...(officerToken ? { 'X-Officer-Token': officerToken } : {}),
            ...options?.headers,
          },
        });

        clearTimeout(timer);

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
        clearTimeout(timer);
        lastError = err;
        const isAbort = err.name === 'AbortError' || err.message?.includes('aborted');
        const isNetwork = isAbort || err.message?.includes('Network request failed');

        if (attempt < maxRetries && isNetwork) {
          console.warn(
            `[ApiClient] Request to ${url} failed or timed out (attempt ${attempt + 1}/${maxRetries + 1}). Retrying in 1.5s...`
          );
          await new Promise((res) => setTimeout(res, 1500));
          continue;
        }

        if (isAbort) {
          throw new Error(
            `Request to ${endpoint} timed out after ${Math.round(
              timeoutMs / 1000
            )}s. The backend server may be waking up from cold-start. Please try again.`
          );
        }
        console.warn(`[ApiClient] Request to ${url} failed:`, err.message);
        throw err;
      }
    }

    throw lastError;
  }

  public static resolveMediaUrl(url: string | null | undefined): string | undefined {
    if (!url) return undefined;
    const baseUrl = getApiBaseUrl();
    if (url.startsWith('/')) {
      return `${baseUrl}${url}`;
    }
    const storageIdx = url.indexOf('/api/v1/storage/');
    if (storageIdx !== -1) {
      return `${baseUrl}${url.substring(storageIdx)}`;
    }
    return url;
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
    farmer_name?: string;
    farmer_id?: string;
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

  static getDemoSampleVideoUrl(): string {
    return `${getApiBaseUrl()}/api/v1/demo/sample-video`;
  }

  static getPrintableBoardUrl(): string {
    return `${getApiBaseUrl()}/ui/charuco_board_7x5_40mm_A4_printable.pdf`;
  }

  public static async uriToBlob(fileUri: string, defaultType: string = 'image/jpeg'): Promise<Blob> {
    // 1. Removed manual base64 parsing (it crashes on massive video strings).
    // Native fetch().blob() handles data: URIs much faster in C++.
    // 2. Modern WinterCG fetch(fileUri).blob() (handles http, https, and many local URIs in Expo)
    try {
      const response = await fetch(fileUri);
      const blob = await response.blob();
      if (blob && blob.size > 0) {
        return blob;
      }
    } catch (fetchErr) {
      console.warn('[ApiClient] fetch(fileUri).blob() failed, trying XHR fallback:', fetchErr);
    }

    // 3. React Native XMLHttpRequest blob reader (robust fallback for local file:// and content:// on Android/iOS)
    return new Promise<Blob>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.onload = () => {
        if (xhr.response) {
          resolve(xhr.response as Blob);
        } else {
          reject(new Error('XMLHttpRequest returned empty response for file URI'));
        }
      };
      xhr.onerror = (e) => {
        reject(new Error(`XMLHttpRequest failed to load file URI: ${e}`));
      };
      xhr.responseType = 'blob';
      xhr.open('GET', fileUri, true);
      xhr.send(null);
    });
  }

  static async uploadSample(
    inspectionId: string,
    fileUri: string,
    location?: { lat?: number; lon?: number; accuracy?: number }
  ): Promise<SampleDetail> {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}/api/v1/inspections/${inspectionId}/samples`;

    let rawFilename = fileUri.split('/').pop()?.split('?')[0] || 'sample.jpg';
    if (fileUri.startsWith('data:') || rawFilename.length > 50) {
      rawFilename = `sample_${Date.now()}.jpg`;
    }
    const filename = rawFilename.includes('.') ? rawFilename : `${rawFilename}.jpg`;
    const match = /\.(\w+)$/.exec(filename);
    const ext = match ? match[1].toLowerCase() : 'jpg';
    let type = 'image/jpeg';
    if (ext === 'png') type = 'image/png';
    else if (ext === 'webp') type = 'image/webp';
    else if (ext === 'heic') type = 'image/heic';
    else if (ext === 'heif') type = 'image/heif';
    else if (ext === 'bmp') type = 'image/bmp';
    else if (ext === 'tif' || ext === 'tiff') type = 'image/tiff';
    else if (ext === 'avif') type = 'image/avif';
    else if (ext === 'gif') type = 'image/gif';

    const blob = await this.uriToBlob(fileUri, type);

    const formData = new FormData();
    formData.append('file', blob, filename);

    if (location?.lat !== undefined) formData.append('geo_lat', location.lat.toString());
    if (location?.lon !== undefined) formData.append('geo_lon', location.lon.toString());
    if (location?.accuracy !== undefined) {
      formData.append('location_accuracy', location.accuracy.toString());
    }

    const officerToken = getOfficerToken();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    let response: Response;
    try {
      response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(officerToken ? { 'X-Officer-Token': officerToken } : {}),
        },
      });
    } catch (fetchErr: any) {
      clearTimeout(timeout);
      if (fetchErr.name === 'AbortError' || fetchErr.message?.includes('aborted')) {
        throw new Error('Sample upload timed out after 120s. Server may be under heavy CV load. Please retry.');
      }
      throw fetchErr;
    } finally {
      clearTimeout(timeout);
    }

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

  static async uploadVideo(
    inspectionId: string,
    fileUri: string
  ): Promise<VideoScanResult> {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}/api/v1/inspections/${inspectionId}/video`;

    let rawFilename = fileUri.split('/').pop()?.split('?')[0] || 'sweep.mp4';
    if (fileUri.startsWith('data:') || rawFilename.length > 50) {
      rawFilename = `sweep_${Date.now()}.mp4`;
    }
    const filename = rawFilename.includes('.') ? rawFilename : `${rawFilename}.mp4`;
    const match = /\.(\w+)$/.exec(filename);
    const ext = match ? match[1].toLowerCase() : 'mp4';
    const type = ext === 'mov' ? 'video/quicktime' : ext === 'webm' ? 'video/webm' : 'video/mp4';

    const blob = await this.uriToBlob(fileUri, type);

    const formData = new FormData();
    formData.append('file', blob, filename);

    const officerToken = getOfficerToken();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 180000);

    let response: Response;
    try {
      response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(officerToken ? { 'X-Officer-Token': officerToken } : {}),
        },
      });
    } catch (fetchErr: any) {
      clearTimeout(timeout);
      if (fetchErr.name === 'AbortError' || fetchErr.message?.includes('aborted')) {
        throw new Error('Video scan timed out after 180s. Keyframe CV sweep took too long. Please retry.');
      }
      throw fetchErr;
    } finally {
      clearTimeout(timeout);
    }

    if (!response.ok) {
      const errText = await response.text();
      let humanMsg = `Video upload failed (${response.status})`;
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

    return (await response.json()) as VideoScanResult;
  }

  static async askAiAgronomist(
    inspectionId: string,
    question: string
  ): Promise<{ answer: string; inspection_id: string; powered_by?: string; is_fallback?: boolean }> {
    return this.request<{ answer: string; inspection_id: string; powered_by?: string; is_fallback?: boolean }>(
      `/api/v1/inspections/${inspectionId}/ask-ai`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      }
    );
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

  static async exportEnam(
    inspectionId: string,
    format: 'json' | 'xml' = 'json',
    lotWeightKg = 1000.0
  ): Promise<any> {
    return this.request(`/api/v1/inspections/${inspectionId}/enam?format=${format}&lot_weight_kg=${lotWeightKg}`);
  }

  static async getMandiAnnouncement(
    inspectionId: string,
    language?: string
  ): Promise<{
    inspection_id: string;
    language: string;
    announcement_text: string;
    lot_recommendation: string;
    grade_a_pct: number;
    urs_pct: number;
    rejected_pct: number;
    audio_available: boolean;
    audio_base64?: string;
    audio_content_type?: string;
    is_mock: boolean;
    tts_status?: string;
  }> {
    const langParam = language ? `?language=${language}` : '';
    return this.request(`/api/v1/inspections/${inspectionId}/announce${langParam}`);
  }
}

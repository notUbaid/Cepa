export type InspectionStatus = 'DRAFT' | 'PROCESSING' | 'REVIEW' | 'FINALIZED';
export type ClassificationGrade = 'GRADE_A' | 'URS' | 'REJECTED' | 'NEEDS_REVIEW';
export type ConfidenceTier = 'HIGH' | 'NEEDS_REVIEW' | 'UNUSABLE';

export interface InspectionSummary {
  id: string;
  lot_id: string | null;
  procurement_centre: string | null;
  officer_name: string | null;
  status: InspectionStatus;
  created_at: string;
  finalized_at: string | null;
  sample_count: number;
}

export interface InspectionDetail extends InspectionSummary {
  officer_id: string | null;
  notes: string | null;
  geo_lat: number | null;
  geo_lon: number | null;
  location_accuracy: number | null;
  location_note: string | null;
  updated_at: string;
  total_bulbs: number;
  grade_a_count: number;
  urs_count: number;
  rejected_count: number;
  review_count: number;
  grade_a_pct: number;
  urs_pct: number;
  rejected_pct: number;
  sample_ids: string[];
  has_report: boolean;
  report_id: string | null;
}

export interface OnionInstanceSummary {
  id: string;
  instance_index: number;
  display_number: number;
  bbox_x: number;
  bbox_y: number;
  bbox_w: number;
  bbox_h: number;
  segmentation_conf: number;
  touches_border: boolean;
  equivalent_diameter_mm: number | null;
  equatorial_diameter_mm?: number | null;
  polar_length_mm?: number | null;
  shape_class?: string | null;
  estimated_weight_grams?: number | null;
  mandi_size_grade?: string | null;
  damaged_prob: number | null;
  rotten_prob: number | null;
  sprouted_prob: number | null;
  is_mock_defect: boolean;
  grade: ClassificationGrade | null;
  confidence_tier: ConfidenceTier | null;
  crop_url: string | null;
  mask_url: string | null;
}

export interface OnionInstanceDetail extends OnionInstanceSummary {
  defect_model_version: string | null;
  has_human_correction: boolean;
  corrected_by: string | null;
  major_axis_mm: number | null;
  minor_axis_mm: number | null;
  shape_index?: number | null;
  mask_area_px: number | null;
  scale_mm_per_px: number | null;
  projection_note: string | null;
  uncertainty_flag: boolean;
  rejection_reasons: string[];
  ruleset_version: string | null;
  explanation: Record<string, string>;
  morphology?: Record<string, any>;
}

export interface SampleDetail {
  id: string;
  inspection_id: string;
  sample_index: number;
  image_path: string | null;
  processed_image_path: string | null;
  original_image_url: string | null;
  processed_image_url: string | null;
  image_width_px: number | null;
  image_height_px: number | null;
  marker_detected: boolean;
  scale_mm_per_px: number | null;
  perspective_valid: boolean;
  quality_passed: boolean;
  quality_flags: string[];
  processing_status: 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED';
  processing_error: string | null;
  processing_started_at: string | null;
  processing_finished_at: string | null;
  model_version: string | null;
  geo_lat: number | null;
  geo_lon: number | null;
  location_accuracy_m: number | null;
  created_at: string;
  onion_count: number;
  onion_instances: OnionInstanceSummary[];
}

export interface ReportDetail {
  id: string;
  report_id: string;
  share_token: string;
  inspection_id: string;
  lot_id: string | null;
  procurement_centre: string | null;
  officer_name: string | null;
  officer_id: string | null;
  officer_notes: string | null;
  sample_count: number;
  sampling_note: string;
  total_bulbs: number;
  grade_a_count: number;
  urs_count: number;
  rejected_count: number;
  review_count: number;
  edge_cutoff_count: number;
  grade_a_pct: number;
  urs_pct: number;
  rejected_pct: number;
  defect_counts: Record<string, number>;
  ruleset_version: string;
  model_version: string;
  geo_lat: number | null;
  geo_lon: number | null;
  location_note: string | null;
  created_at: string;
  finalized_at: string | null;
  pdf_url: string | null;
  share_url: string | null;
  limitations_note: string;
}

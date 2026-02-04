/**
 * Core type definitions for Argus AI Dashboard
 */

export interface User {
  id: string
  email: string
  role: 'admin' | 'customer'
  name?: string
}

export interface DetectionResult {
  is_injection: boolean
  confidence: number
  attack_type?: string
  layer_detected?: number
  latency_ms: number
  layers: LayerResult[]
}

export interface LayerResult {
  layer: 1 | 2 | 3
  name: string
  passed: boolean
  latency_ms: number
  confidence?: number
  skipped?: boolean
  status?: 'pass' | 'detected' | 'skipped'
}

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  rate_limit: number
  status: 'active' | 'revoked'
  created_at: string
}

// Analytics types
export interface DetectionStats {
  total_requests: number
  injections_detected: number
  detection_rate: number
  avg_latency_ms: number
  layer_breakdown: {
    layer_1: number
    layer_2: number
    layer_3: number
  }
}

export interface TimeSeriesDataPoint {
  timestamp: string
  requests: number
  detections: number
  avg_latency: number
}

// Attack type distribution
export interface AttackTypeCount {
  attack_type: string
  count: number
  percentage: number
}

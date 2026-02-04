import { useState, useCallback } from 'react'
import { detectInjection, ApiError } from '@/lib/api'
import type { DetectionResult } from '@/types'

interface UseDetectionReturn {
  result: DetectionResult | null
  loading: boolean
  error: string | null
  detect: (text: string, apiKey: string, skipLayer3?: boolean) => Promise<void>
  reset: () => void
}

/**
 * Detection API hook for running prompt injection detection
 *
 * @example
 * const { result, loading, error, detect, reset } = useDetection()
 *
 * // Run detection
 * await detect('Ignore previous instructions', apiKey)
 *
 * // Check result
 * if (result?.is_injection) {
 *   console.log(`Detected at layer ${result.layer_detected}`)
 * }
 *
 * // Clear state
 * reset()
 */
export function useDetection(): UseDetectionReturn {
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const detect = useCallback(
    async (text: string, apiKey: string, skipLayer3 = false) => {
      try {
        setError(null)
        setLoading(true)
        setResult(null)

        const detectionResult = await detectInjection(text, apiKey, skipLayer3)
        setResult(detectionResult)
      } catch (err) {
        if (err instanceof ApiError) {
          // Provide user-friendly error messages
          if (err.status === 401) {
            setError('Invalid API key')
          } else if (err.status === 429) {
            setError('Rate limit exceeded. Please try again later.')
          } else if (err.code === 'TIMEOUT') {
            setError('Request timed out. Please try again.')
          } else if (err.code === 'NETWORK_ERROR') {
            setError('Network error. Please check your connection.')
          } else {
            setError(err.message || 'Detection failed')
          }
        } else {
          setError('An unexpected error occurred')
        }

        // Re-throw for caller to handle if needed
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    setLoading(false)
  }, [])

  return {
    result,
    loading,
    error,
    detect,
    reset,
  }
}

import { useState, useCallback, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import type { ApiKey } from '@/types'

interface UseApiKeysReturn {
  keys: ApiKey[]
  loading: boolean
  error: string | null
  createKey: (name: string, rateLimit: number) => Promise<string | null>
  revokeKey: (id: string) => Promise<void>
  refresh: () => Promise<void>
}

/**
 * API key management hook
 *
 * Automatically fetches keys on mount. Admin users see all keys,
 * customer users only see their own keys.
 *
 * @example
 * const { keys, loading, createKey, revokeKey } = useApiKeys()
 *
 * // Create new key
 * const fullKey = await createKey('Production API', 1000)
 * if (fullKey) {
 *   // Show fullKey to user (only time they'll see it)
 *   console.log('Save this key:', fullKey)
 * }
 *
 * // Revoke key
 * await revokeKey(keyId)
 */
export function useApiKeys(): UseApiKeysReturn {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchKeys = useCallback(async () => {
    try {
      setError(null)
      setLoading(true)

      // Get current user
      const {
        data: { user },
      } = await supabase.auth.getUser()

      if (!user) {
        throw new Error('Not authenticated')
      }

      const isAdmin = user.user_metadata?.role === 'admin'

      // Build query - daily_limit is the rate limit column in DB
      let query = supabase
        .from('api_keys')
        .select('id, name, key_prefix, daily_limit, status, created_at')
        .order('created_at', { ascending: false })

      // Filter by user_id if not admin
      if (!isAdmin) {
        query = query.eq('user_id', user.id)
      }

      const { data, error: fetchError } = await query

      if (fetchError) {
        console.error('Supabase fetch error:', fetchError)
        throw fetchError
      }

      // Map daily_limit to rate_limit for frontend compatibility
      const mappedKeys = (data || []).map((key: Record<string, unknown>) => ({
        id: key.id as string,
        name: key.name as string,
        key_prefix: key.key_prefix as string,
        rate_limit: key.daily_limit as number,
        status: key.status as 'active' | 'revoked',
        created_at: key.created_at as string,
      }))
      setKeys(mappedKeys)
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch API keys'
      setError(errorMessage)
      console.error('Error fetching API keys:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchKeys()
  }, [fetchKeys])

  const createKey = useCallback(
    async (name: string, rateLimit: number): Promise<string | null> => {
      try {
        setError(null)

        // Get current user
        const {
          data: { user },
        } = await supabase.auth.getUser()

        if (!user) {
          throw new Error('Not authenticated')
        }

        // Call the create_api_key RPC function
        const { data, error: createError } = await supabase.rpc('create_api_key', {
          p_name: name,
          p_rate_limit: rateLimit,
        })

        if (createError) throw createError

        // Refresh the keys list
        await fetchKeys()

        // Return the full key (only time user will see it)
        return data as string
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to create API key'
        setError(errorMessage)
        console.error('Error creating API key:', err)
        return null
      }
    },
    [fetchKeys]
  )

  const revokeKey = useCallback(
    async (id: string): Promise<void> => {
      try {
        setError(null)

        const { error: updateError } = await supabase
          .from('api_keys')
          .update({ status: 'revoked', is_active: false })
          .eq('id', id)

        if (updateError) throw updateError

        // Update local state
        setKeys((prevKeys) =>
          prevKeys.map((key) =>
            key.id === id ? { ...key, status: 'revoked' as const } : key
          )
        )
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to revoke API key'
        setError(errorMessage)
        console.error('Error revoking API key:', err)
        throw err
      }
    },
    []
  )

  return {
    keys,
    loading,
    error,
    createKey,
    revokeKey,
    refresh: fetchKeys,
  }
}

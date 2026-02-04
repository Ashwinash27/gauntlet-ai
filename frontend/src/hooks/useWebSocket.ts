import { useState, useEffect, useCallback, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import type { RealtimeChannel } from '@supabase/supabase-js'

interface Activity {
  id: string
  timestamp: string
  text_hash: string
  is_injection: boolean
  confidence: number
  attack_type?: string
  layer_detected?: number
  latency_ms: number
  user_id?: string
  api_key_id: string
}

interface UseWebSocketReturn {
  activities: Activity[]
  isConnected: boolean
}

const MAX_ACTIVITIES = 50
const BATCH_DELAY = 100 // ms

/**
 * Real-time activity feed hook
 *
 * Subscribes to request_logs table changes via Supabase Realtime.
 * Keeps last 50 activities and batches updates to prevent UI thrashing.
 *
 * @example
 * const { activities, isConnected } = useWebSocket()
 *
 * // Display activities in real-time
 * activities.map(activity => (
 *   <div key={activity.id}>
 *     {activity.is_injection ? 'THREAT' : 'SAFE'} - {activity.confidence}%
 *   </div>
 * ))
 */
export function useWebSocket(): UseWebSocketReturn {
  const [activities, setActivities] = useState<Activity[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const channelRef = useRef<RealtimeChannel | null>(null)
  const batchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingActivitiesRef = useRef<Activity[]>([])

  // Batch updates to prevent UI thrashing
  const flushPendingActivities = useCallback(() => {
    if (pendingActivitiesRef.current.length === 0) return

    setActivities((prev) => {
      const combined = [...pendingActivitiesRef.current, ...prev]
      pendingActivitiesRef.current = []
      return combined.slice(0, MAX_ACTIVITIES)
    })
  }, [])

  const addActivity = useCallback(
    (activity: Activity) => {
      pendingActivitiesRef.current.push(activity)

      // Clear existing timer
      if (batchTimerRef.current) {
        clearTimeout(batchTimerRef.current)
      }

      // Schedule flush
      batchTimerRef.current = setTimeout(flushPendingActivities, BATCH_DELAY)
    },
    [flushPendingActivities]
  )

  useEffect(() => {
    // Subscribe to request_logs inserts
    const channel = supabase
      .channel('request_logs_changes')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'request_logs',
        },
        (payload) => {
          const newActivity = payload.new as Activity
          addActivity(newActivity)
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          setIsConnected(true)
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          setIsConnected(false)
        }
      })

    channelRef.current = channel

    // Fetch initial activities
    const fetchInitialActivities = async () => {
      try {
        const { data, error } = await supabase
          .from('request_logs')
          .select('*')
          .order('timestamp', { ascending: false })
          .limit(MAX_ACTIVITIES)

        if (error) throw error

        if (data) {
          setActivities(data)
        }
      } catch (err) {
        console.error('Error fetching initial activities:', err)
      }
    }

    fetchInitialActivities()

    // Cleanup
    return () => {
      if (batchTimerRef.current) {
        clearTimeout(batchTimerRef.current)
        flushPendingActivities() // Flush any pending updates
      }
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
      }
    }
  }, [addActivity, flushPendingActivities])

  return {
    activities,
    isConnected,
  }
}

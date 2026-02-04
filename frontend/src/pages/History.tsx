import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Filter,
  Clock,
  Zap,
  Database,
} from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { TypewriterText, ScrollReveal, StaggerChildren } from '@/components/animations';
import { NeonButton } from '@/components/ui/NeonButton';
import { NeonCard } from '@/components/ui/NeonCard';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { GridBackground } from '@/components/backgrounds';
import { cn } from '@/lib/utils';

interface RequestLog {
  id: string;
  created_at: string;
  is_injection: boolean;
  layer_detected: number | null;
  latency_ms: number;
  input_hash: string;
}

type FilterType = 'all' | 'threats' | 'safe';

const PAGE_SIZE = 20;

/**
 * History page - Cyberpunk Request Logs
 * - Staggered row animations
 * - Filter row with glow states
 * - Skeleton loading with shimmer
 */
export const History: React.FC = () => {
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [filter, setFilter] = useState<FilterType>('all');

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      // Build query with filter
      let countQuery = supabase.from('request_logs').select('*', { count: 'exact', head: true });
      let dataQuery = supabase
        .from('request_logs')
        .select('id, created_at, is_injection, layer_detected, latency_ms, input_hash')
        .order('created_at', { ascending: false });

      if (filter === 'threats') {
        countQuery = countQuery.eq('is_injection', true);
        dataQuery = dataQuery.eq('is_injection', true);
      } else if (filter === 'safe') {
        countQuery = countQuery.eq('is_injection', false);
        dataQuery = dataQuery.eq('is_injection', false);
      }

      const { count, error: countError } = await countQuery;
      if (countError) throw countError;
      setTotalCount(count || 0);

      const { data, error } = await dataQuery.range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);
      if (error) throw error;
      setLogs(data || []);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Reset to page 1 when filter changes
  useEffect(() => {
    setPage(1);
  }, [filter]);

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();

    if (isToday) {
      return formatTime(dateStr);
    }
    return (
      date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' + formatTime(dateStr)
    );
  };

  const getLayerBadge = (layer: number | null) => {
    if (!layer) return <span className="text-text-tertiary">--</span>;
    const variants: Record<number, 'layer1' | 'layer2' | 'layer3'> = {
      1: 'layer1',
      2: 'layer2',
      3: 'layer3',
    };
    return <NeonBadge variant={variants[layer]}>L{layer}</NeonBadge>;
  };

  return (
    <div className="p-8 ml-[240px] min-h-screen bg-void-deep relative">
      <GridBackground opacity={0.02} />

      <div className="max-w-6xl mx-auto relative z-10">
        {/* Header */}
        <ScrollReveal direction="down">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-display text-2xl text-neon-cyan tracking-wider mb-2">
                <TypewriterText text="REQUEST HISTORY" speed={40} />
              </h1>
              <p className="text-text-tertiary text-sm flex items-center gap-2">
                <Database className="w-4 h-4" />
                {totalCount.toLocaleString()} records
              </p>
            </div>
            <NeonButton
              onClick={fetchLogs}
              disabled={loading}
              variant="ghost"
              size="sm"
            >
              <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
              Refresh
            </NeonButton>
          </div>
        </ScrollReveal>

        {/* Filters */}
        <ScrollReveal direction="up" delay={0.1}>
          <NeonCard className="p-4 mb-6">
            <div className="flex items-center gap-4">
              <Filter className="w-4 h-4 text-text-tertiary" />
              <div className="flex gap-2">
                {(['all', 'threats', 'safe'] as FilterType[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={cn(
                      'px-4 py-2 text-xs uppercase tracking-wider border transition-all duration-300',
                      filter === f
                        ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan shadow-neon-cyan'
                        : 'border-neon-cyan/20 text-text-secondary hover:border-neon-cyan/40 hover:text-text-primary'
                    )}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          </NeonCard>
        </ScrollReveal>

        {/* Table */}
        <ScrollReveal direction="up" delay={0.2}>
          <NeonCard className="overflow-hidden">
            {/* Table Header */}
            <div className="bg-void-surface border-b border-neon-cyan/10 p-4">
              <div className="grid grid-cols-12 gap-4 text-xs text-text-tertiary uppercase tracking-wider">
                <div className="col-span-3 flex items-center gap-2">
                  <Clock className="w-3 h-3" />
                  Time
                </div>
                <div className="col-span-2">Result</div>
                <div className="col-span-1">Layer</div>
                <div className="col-span-2 flex items-center gap-2">
                  <Zap className="w-3 h-3" />
                  Latency
                </div>
                <div className="col-span-4">Input Hash</div>
              </div>
            </div>

            {/* Table Body */}
            <div className="divide-y divide-neon-cyan/5">
              {loading ? (
                // Skeleton loading
                [...Array(10)].map((_, i) => (
                  <div
                    key={i}
                    className="grid grid-cols-12 gap-4 p-4"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <div className="col-span-3 h-4 bg-void-surface rounded animate-pulse" />
                    <div className="col-span-2 h-4 bg-void-surface rounded animate-pulse" />
                    <div className="col-span-1 h-4 bg-void-surface rounded animate-pulse" />
                    <div className="col-span-2 h-4 bg-void-surface rounded animate-pulse" />
                    <div className="col-span-4 h-4 bg-void-surface rounded animate-pulse" />
                  </div>
                ))
              ) : logs.length === 0 ? (
                <div className="py-16 text-center text-text-tertiary">
                  <Database className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p>No request logs found</p>
                </div>
              ) : (
                <AnimatePresence>
                  <StaggerChildren staggerDelay={0.03} direction="left">
                    {logs.map((log) => (
                      <motion.div
                        key={log.id}
                        whileHover={{ backgroundColor: 'rgba(0, 240, 255, 0.02)' }}
                        className="grid grid-cols-12 gap-4 p-4 items-center transition-colors"
                      >
                        <div className="col-span-3 text-text-secondary text-sm font-mono">
                          {formatDate(log.created_at)}
                        </div>
                        <div className="col-span-2">
                          <NeonBadge variant={log.is_injection ? 'danger' : 'safe'}>
                            {log.is_injection ? 'THREAT' : 'SAFE'}
                          </NeonBadge>
                        </div>
                        <div className="col-span-1">{getLayerBadge(log.layer_detected)}</div>
                        <div className="col-span-2 text-text-tertiary text-sm">
                          {log.latency_ms}ms
                        </div>
                        <div className="col-span-4 text-text-tertiary text-xs font-mono truncate opacity-50">
                          {log.input_hash}
                        </div>
                      </motion.div>
                    ))}
                  </StaggerChildren>
                </AnimatePresence>
              )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-void-surface border-t border-neon-cyan/10 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-text-tertiary">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <NeonButton
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || loading}
                      variant="ghost"
                      size="sm"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Prev
                    </NeonButton>
                    <NeonButton
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages || loading}
                      variant="ghost"
                      size="sm"
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </NeonButton>
                  </div>
                </div>
              </div>
            )}
          </NeonCard>
        </ScrollReveal>
      </div>
    </div>
  );
};

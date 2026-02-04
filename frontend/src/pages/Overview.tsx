import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  ShieldAlert,
  TrendingUp,
  FlaskConical,
  History,
  Clock,
  Zap,
} from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { TypewriterText, ScrollReveal, StaggerChildren } from '@/components/animations';
import { DataPanel } from '@/components/ui/DataPanel';
import { NeonCard } from '@/components/ui/NeonCard';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { GridBackground } from '@/components/backgrounds';

interface Stats {
  totalRequests: number;
  threatsBlocked: number;
  blockRate: number;
}

interface RecentLog {
  id: string;
  created_at: string;
  is_injection: boolean;
  latency_ms: number;
  input_preview: string;
  layer_detected: number | null;
}

/**
 * Overview page - Cyberpunk Command Center Dashboard
 * - Animated stat cards with count-up
 * - Real-time activity feed with typing animation
 * - Scroll reveal animations
 */
export const Overview: React.FC = () => {
  const [stats, setStats] = useState<Stats>({ totalRequests: 0, threatsBlocked: 0, blockRate: 0 });
  const [recentLogs, setRecentLogs] = useState<RecentLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(true);

  // Fetch stats from database
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const { data, error } = await supabase
          .from('request_logs')
          .select('is_injection')
          .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString());

        if (error) throw error;

        const total = data?.length || 0;
        const threats = data?.filter((r) => r.is_injection).length || 0;
        const rate = total > 0 ? Math.round((threats / total) * 1000) / 10 : 0;

        setStats({
          totalRequests: total,
          threatsBlocked: threats,
          blockRate: rate,
        });
        setIsOnline(true);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
        setIsOnline(false);
      }
    };

    const fetchRecentLogs = async () => {
      try {
        const { data, error } = await supabase
          .from('request_logs')
          .select('id, created_at, is_injection, latency_ms, input_hash, layer_detected')
          .order('created_at', { ascending: false })
          .limit(5);

        if (error) throw error;

        setRecentLogs(
          (data || []).map((log) => ({
            id: log.id,
            created_at: log.created_at,
            is_injection: log.is_injection,
            latency_ms: log.latency_ms,
            input_preview: log.input_hash?.substring(0, 12) + '...',
            layer_detected: log.layer_detected,
          }))
        );
      } catch (err) {
        console.error('Failed to fetch recent logs:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    fetchRecentLogs();

    const interval = setInterval(() => {
      fetchStats();
      fetchRecentLogs();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getLayerBadge = (layer: number | null) => {
    if (!layer) return null;
    const variants: Record<number, 'layer1' | 'layer2' | 'layer3'> = {
      1: 'layer1',
      2: 'layer2',
      3: 'layer3',
    };
    return <NeonBadge variant={variants[layer]}>L{layer}</NeonBadge>;
  };

  return (
    <div className="p-8 ml-[240px] min-h-screen bg-void-deep relative">
      {/* Subtle grid background */}
      <GridBackground opacity={0.02} />

      <div className="max-w-5xl mx-auto relative z-10">
        {/* Header */}
        <ScrollReveal direction="down">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="font-display text-2xl text-neon-cyan tracking-wider">
                <TypewriterText text="SYSTEM OVERVIEW" speed={40} />
              </h1>
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className={`w-2 h-2 rounded-full ${isOnline ? 'bg-status-safe' : 'bg-status-danger'}`}
                />
                <span className={`text-xs ${isOnline ? 'text-status-safe' : 'text-status-danger'}`}>
                  {isOnline ? 'CONNECTED' : 'OFFLINE'}
                </span>
              </div>
            </div>
            <p className="text-text-tertiary text-sm">Real-time detection metrics (24h window)</p>
          </div>
        </ScrollReveal>

        {/* Stats Cards */}
        <ScrollReveal direction="up" delay={0.2}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <DataPanel
              label="Total Requests"
              value={loading ? 0 : stats.totalRequests}
              variant="cyan"
              icon={<Activity className="w-5 h-5 text-neon-cyan" />}
            />
            <DataPanel
              label="Threats Blocked"
              value={loading ? 0 : stats.threatsBlocked}
              variant="danger"
              icon={<ShieldAlert className="w-5 h-5 text-status-danger" />}
            />
            <DataPanel
              label="Block Rate"
              value={loading ? 0 : stats.blockRate}
              suffix="%"
              decimals={1}
              variant="warning"
              icon={<TrendingUp className="w-5 h-5 text-status-warning" />}
            />
          </div>
        </ScrollReveal>

        {/* Recent Activity */}
        <ScrollReveal direction="up" delay={0.4}>
          <NeonCard className="p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg text-text-primary tracking-wide">
                RECENT ACTIVITY
              </h2>
              <div className="flex items-center gap-2 text-text-tertiary text-xs">
                <Clock className="w-3 h-3" />
                <span>Auto-refresh: 30s</span>
              </div>
            </div>

            {loading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="h-10 bg-void-surface animate-pulse rounded"
                    style={{ animationDelay: `${i * 100}ms` }}
                  />
                ))}
              </div>
            ) : recentLogs.length === 0 ? (
              <div className="py-8 text-center text-text-tertiary">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No recent activity</p>
              </div>
            ) : (
              <StaggerChildren staggerDelay={0.1} direction="left">
                {recentLogs.map((log) => (
                  <motion.div
                    key={log.id}
                    whileHover={{ x: 4, backgroundColor: 'rgba(0, 240, 255, 0.02)' }}
                    className="flex items-center justify-between py-3 px-4 border-b border-neon-cyan/5 last:border-0 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-text-tertiary text-xs font-mono w-20">
                        {formatTime(log.created_at)}
                      </span>
                      <NeonBadge variant={log.is_injection ? 'danger' : 'safe'}>
                        {log.is_injection ? 'THREAT' : 'SAFE'}
                      </NeonBadge>
                      {log.is_injection && getLayerBadge(log.layer_detected)}
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-text-tertiary text-xs flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {log.latency_ms}ms
                      </span>
                      <span className="text-text-tertiary text-xs font-mono opacity-50">
                        {log.input_preview}
                      </span>
                    </div>
                  </motion.div>
                ))}
              </StaggerChildren>
            )}
          </NeonCard>
        </ScrollReveal>

        {/* Quick Actions */}
        <ScrollReveal direction="up" delay={0.6}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Link to="/playground">
              <NeonCard className="p-6 group cursor-pointer" variant="cyan">
                <div className="flex items-start gap-4">
                  <div className="p-3 border border-neon-cyan/30 group-hover:border-neon-cyan/50 transition-colors">
                    <FlaskConical className="w-6 h-6 text-neon-cyan" />
                  </div>
                  <div>
                    <h3 className="font-display text-lg text-text-primary mb-1 group-hover:text-neon-cyan transition-colors">
                      PLAYGROUND
                    </h3>
                    <p className="text-text-secondary text-sm">
                      Test detection in real-time with live feedback
                    </p>
                  </div>
                </div>
              </NeonCard>
            </Link>

            <Link to="/history">
              <NeonCard className="p-6 group cursor-pointer" variant="cyan">
                <div className="flex items-start gap-4">
                  <div className="p-3 border border-neon-cyan/30 group-hover:border-neon-cyan/50 transition-colors">
                    <History className="w-6 h-6 text-neon-cyan" />
                  </div>
                  <div>
                    <h3 className="font-display text-lg text-text-primary mb-1 group-hover:text-neon-cyan transition-colors">
                      HISTORY
                    </h3>
                    <p className="text-text-secondary text-sm">
                      Browse all detection requests and results
                    </p>
                  </div>
                </div>
              </NeonCard>
            </Link>
          </div>
        </ScrollReveal>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-8 text-center text-text-tertiary text-xs"
        >
          Last updated: {new Date().toLocaleTimeString()}
        </motion.div>
      </div>
    </div>
  );
};

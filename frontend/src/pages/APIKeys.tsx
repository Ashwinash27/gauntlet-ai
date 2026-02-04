import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Key,
  Copy,
  Check,
  AlertTriangle,
  Trash2,
  X,
  CheckCircle,
  Shield,
} from 'lucide-react';
import { useApiKeys } from '@/hooks/useApiKeys';
import type { ApiKey } from '@/types';
import { TypewriterText, ScrollReveal, StaggerChildren } from '@/components/animations';
import { NeonButton } from '@/components/ui/NeonButton';
import { NeonInput } from '@/components/ui/NeonInput';
import { NeonCard } from '@/components/ui/NeonCard';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { GridBackground } from '@/components/backgrounds';
import { cn } from '@/lib/utils';

/**
 * API Keys page - Cyberpunk Key Management
 * - Card layout for keys
 * - Animated modals with slide-in
 * - Success animation with checkmark
 */
export const APIKeys: React.FC = () => {
  const { keys, loading, error, createKey, revokeKey } = useApiKeys();

  // Create key modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyRateLimit, setNewKeyRateLimit] = useState('1000');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Success modal state
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Revoke confirmation
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKey | null>(null);
  const [revoking, setRevoking] = useState(false);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      setCreateError('Key name is required');
      return;
    }

    const rateLimit = parseInt(newKeyRateLimit, 10);
    if (isNaN(rateLimit) || rateLimit <= 0) {
      setCreateError('Invalid rate limit');
      return;
    }

    try {
      setCreating(true);
      setCreateError(null);

      const fullKey = await createKey(newKeyName.trim(), rateLimit);

      if (fullKey) {
        setCreatedKey(fullKey);
        setShowCreateModal(false);
        setShowSuccessModal(true);
        setNewKeyName('');
        setNewKeyRateLimit('1000');
      } else {
        setCreateError('Failed to create key');
      }
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setCreating(false);
    }
  };

  const handleRevokeConfirm = async () => {
    if (!keyToRevoke) return;

    try {
      setRevoking(true);
      await revokeKey(keyToRevoke.id);
      setKeyToRevoke(null);
    } catch (err) {
      console.error('Failed to revoke key:', err);
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="p-8 ml-[240px] min-h-screen bg-void-deep relative">
      <GridBackground opacity={0.02} />

      <div className="max-w-4xl mx-auto relative z-10">
        {/* Header */}
        <ScrollReveal direction="down">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-display text-2xl text-neon-cyan tracking-wider mb-2">
                <TypewriterText text="API KEYS" speed={40} />
              </h1>
              <p className="text-text-tertiary text-sm">
                Manage your API authentication keys
              </p>
            </div>
            <NeonButton onClick={() => setShowCreateModal(true)} variant="cyan" glow>
              <Plus className="w-4 h-4" />
              New Key
            </NeonButton>
          </div>
        </ScrollReveal>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-6 flex items-center gap-2 p-4 bg-status-danger/10 border border-status-danger/30 text-status-danger"
            >
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Keys Grid */}
        <ScrollReveal direction="up" delay={0.2}>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-32 bg-void-elevated border border-neon-cyan/10 animate-pulse"
                  style={{ animationDelay: `${i * 100}ms` }}
                />
              ))}
            </div>
          ) : keys.length === 0 ? (
            <NeonCard className="p-12 text-center">
              <Key className="w-12 h-12 text-text-tertiary mx-auto mb-4 opacity-30" />
              <p className="text-text-secondary mb-2">No API keys yet</p>
              <p className="text-text-tertiary text-sm mb-6">
                Create your first key to start using the API
              </p>
              <NeonButton onClick={() => setShowCreateModal(true)} variant="cyan">
                <Plus className="w-4 h-4" />
                Create First Key
              </NeonButton>
            </NeonCard>
          ) : (
            <StaggerChildren staggerDelay={0.1} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {keys.map((key) => (
                <NeonCard
                  key={key.id}
                  className="p-5"
                  variant={key.status === 'active' ? 'default' : 'default'}
                  hover={key.status === 'active'}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'w-10 h-10 flex items-center justify-center border',
                          key.status === 'active'
                            ? 'border-neon-cyan/30 bg-neon-cyan/5'
                            : 'border-status-danger/30 bg-status-danger/5'
                        )}
                      >
                        <Key
                          className={cn(
                            'w-5 h-5',
                            key.status === 'active' ? 'text-neon-cyan' : 'text-status-danger'
                          )}
                        />
                      </div>
                      <div>
                        <h3 className="text-text-primary font-medium">{key.name}</h3>
                        <p className="text-text-tertiary text-xs font-mono">{key.key_prefix}...</p>
                      </div>
                    </div>
                    <NeonBadge variant={key.status === 'active' ? 'safe' : 'danger'}>
                      {key.status === 'active' ? 'ACTIVE' : 'REVOKED'}
                    </NeonBadge>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-tertiary">
                      Rate limit: <span className="text-text-secondary">{key.rate_limit}/min</span>
                    </span>
                    {key.status === 'active' && (
                      <NeonButton
                        variant="danger"
                        size="sm"
                        onClick={() => setKeyToRevoke(key)}
                      >
                        <Trash2 className="w-3 h-3" />
                        Revoke
                      </NeonButton>
                    )}
                  </div>
                </NeonCard>
              ))}
            </StaggerChildren>
          )}
        </ScrollReveal>

        {/* Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 flex items-center gap-2 text-text-tertiary text-xs"
        >
          <Shield className="w-4 h-4" />
          <span>API keys are shown only once at creation. Store them securely.</span>
        </motion.div>
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-void-deep/90 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={() => !creating && setShowCreateModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md"
            >
              <NeonCard className="overflow-hidden" borderScan>
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-neon-cyan/10">
                  <h2 className="font-display text-lg text-neon-cyan">CREATE API KEY</h2>
                  <button
                    onClick={() => !creating && setShowCreateModal(false)}
                    className="text-text-tertiary hover:text-text-primary transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-5">
                  <NeonInput
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    disabled={creating}
                    placeholder="Production API Key"
                    label="KEY NAME"
                  />

                  <NeonInput
                    type="number"
                    value={newKeyRateLimit}
                    onChange={(e) => setNewKeyRateLimit(e.target.value)}
                    disabled={creating}
                    label="RATE LIMIT (req/min)"
                  />

                  {createError && (
                    <div className="flex items-center gap-2 p-3 bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm">
                      <AlertTriangle className="w-4 h-4" />
                      <span>{createError}</span>
                    </div>
                  )}

                  <div className="flex items-center gap-2 p-3 bg-status-warning/10 border border-status-warning/30 text-status-warning text-sm">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>The key will only be shown once. Save it immediately!</span>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <NeonButton
                      variant="ghost"
                      onClick={() => {
                        setShowCreateModal(false);
                        setNewKeyName('');
                        setNewKeyRateLimit('1000');
                        setCreateError(null);
                      }}
                      disabled={creating}
                      className="flex-1"
                    >
                      Cancel
                    </NeonButton>
                    <NeonButton
                      variant="cyan"
                      onClick={handleCreateKey}
                      disabled={creating}
                      loading={creating}
                      glow
                      className="flex-1"
                    >
                      Create Key
                    </NeonButton>
                  </div>
                </div>
              </NeonCard>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Success Modal */}
      <AnimatePresence>
        {showSuccessModal && createdKey && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-void-deep/90 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-lg"
            >
              <NeonCard className="overflow-hidden" variant="cyan">
                {/* Header */}
                <div className="p-4 border-b border-status-safe/20 bg-status-safe/5">
                  <div className="flex items-center gap-3">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2, type: 'spring' }}
                      className="w-10 h-10 rounded-full bg-status-safe/20 border border-status-safe/30 flex items-center justify-center"
                    >
                      <CheckCircle className="w-5 h-5 text-status-safe" />
                    </motion.div>
                    <h2 className="font-display text-lg text-status-safe">KEY CREATED</h2>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-4">
                  <div>
                    <p className="text-text-tertiary text-xs mb-2 uppercase tracking-wider">
                      Your API Key
                    </p>
                    <div className="p-4 bg-void-base border border-neon-cyan/20 font-mono text-sm text-neon-cyan break-all">
                      {createdKey}
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <NeonButton
                      variant="cyan"
                      onClick={() => copyToClipboard(createdKey)}
                      className="flex-1"
                    >
                      {copied ? (
                        <>
                          <Check className="w-4 h-4" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Copy Key
                        </>
                      )}
                    </NeonButton>
                    <NeonButton
                      variant="ghost"
                      onClick={() => {
                        setShowSuccessModal(false);
                        setCreatedKey(null);
                        setCopied(false);
                      }}
                      className="flex-1"
                    >
                      Done
                    </NeonButton>
                  </div>
                </div>
              </NeonCard>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Revoke Confirmation Modal */}
      <AnimatePresence>
        {keyToRevoke && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-void-deep/90 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={() => !revoking && setKeyToRevoke(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md"
            >
              <NeonCard className="overflow-hidden border-status-danger/30">
                {/* Header */}
                <div className="p-4 border-b border-status-danger/20 bg-status-danger/5">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-status-danger/20 border border-status-danger/30 flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-status-danger" />
                    </div>
                    <h2 className="font-display text-lg text-status-danger">REVOKE KEY</h2>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-4">
                  <p className="text-text-secondary">
                    Are you sure you want to revoke this API key? This action cannot be undone.
                  </p>

                  <div className="p-4 bg-void-base border border-status-danger/20">
                    <p className="text-text-primary font-medium">{keyToRevoke.name}</p>
                    <p className="text-text-tertiary text-sm font-mono">{keyToRevoke.key_prefix}...</p>
                  </div>

                  <div className="flex gap-3">
                    <NeonButton
                      variant="ghost"
                      onClick={() => setKeyToRevoke(null)}
                      disabled={revoking}
                      className="flex-1"
                    >
                      Cancel
                    </NeonButton>
                    <NeonButton
                      variant="danger"
                      onClick={handleRevokeConfirm}
                      disabled={revoking}
                      loading={revoking}
                      className="flex-1"
                    >
                      Revoke Key
                    </NeonButton>
                  </div>
                </div>
              </NeonCard>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

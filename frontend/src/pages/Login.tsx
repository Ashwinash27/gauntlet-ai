import React, { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { BackgroundComposite } from '@/components/backgrounds';
import { TypewriterText, GlitchText } from '@/components/animations';
import { NeonButton } from '@/components/ui/NeonButton';
import { NeonInput } from '@/components/ui/NeonInput';

/**
 * Login page - Cyberpunk/Neon Command Center aesthetic
 * - Full-screen immersive background with grid + particles
 * - Floating terminal card with border scan animation
 * - Typewriter effects and glow focus states
 */
export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { user, loading: authLoading, signIn } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const [showForm, setShowForm] = useState(false);

  // Entry sequence animation
  useEffect(() => {
    const timer1 = setTimeout(() => setShowContent(true), 500);
    const timer2 = setTimeout(() => setShowForm(true), 1500);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  // Redirect if already logged in
  useEffect(() => {
    if (user && !authLoading) {
      navigate('/overview');
    }
  }, [user, authLoading, navigate]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('ERROR: Missing credentials');
      return;
    }

    try {
      setIsSubmitting(true);
      await signIn(email, password);
    } catch (err) {
      setError(`${err instanceof Error ? err.message : 'Authentication failed'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-void-deep flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="w-8 h-8 border-2 border-neon-cyan border-t-transparent rounded-full"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Immersive Background */}
      <BackgroundComposite
        showParticles={true}
        showGrid={true}
        showScanLines={true}
        perspectiveGrid={true}
        particleCount={60}
      />

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Floating Terminal Card */}
          <div className="relative">
            {/* Border scan effect */}
            <div className="absolute inset-0 border-scan pointer-events-none" />

            {/* Card */}
            <div className="bg-void-base/90 backdrop-blur-sm border border-neon-cyan/20 overflow-hidden">
              {/* Terminal Header */}
              <div className="flex items-center gap-2 px-4 py-3 bg-void-elevated border-b border-neon-cyan/20">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-status-danger/80" />
                  <div className="w-3 h-3 rounded-full bg-status-warning/80" />
                  <div className="w-3 h-3 rounded-full bg-status-safe/80" />
                </div>
                <span className="ml-2 text-xs text-text-tertiary font-mono">
                  argus-auth.exe
                </span>
                <div className="ml-auto flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-neon-cyan animate-glow-pulse" />
                  <span className="text-xs text-neon-cyan">SECURE</span>
                </div>
              </div>

              {/* Terminal Content */}
              <div className="p-8">
                {/* Logo & Title */}
                <AnimatePresence>
                  {showContent && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-center mb-8"
                    >
                      {/* Shield Icon */}
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                        className="inline-flex items-center justify-center w-16 h-16 border border-neon-cyan/30 mb-4"
                      >
                        <Shield className="w-8 h-8 text-neon-cyan" />
                      </motion.div>

                      {/* Title with glitch effect on hover */}
                      <h1 className="font-display text-3xl text-neon-cyan mb-2 tracking-wider">
                        <GlitchText text="ARGUS AI" glitchOnHover intensity="low" />
                      </h1>

                      {/* Subtitle with typewriter */}
                      <div className="text-text-secondary text-sm">
                        <TypewriterText
                          text="Prompt Injection Detection System"
                          speed={30}
                          delay={800}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Form */}
                <AnimatePresence>
                  {showForm && (
                    <motion.form
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      onSubmit={handleSubmit}
                      className="space-y-5"
                    >
                      {/* Email Input */}
                      <NeonInput
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={isSubmitting}
                        autoComplete="email"
                        required
                        label="IDENTITY"
                        placeholder="user@domain.com"
                      />

                      {/* Password Input */}
                      <div className="relative">
                        <NeonInput
                          type={showPassword ? 'text' : 'password'}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          disabled={isSubmitting}
                          autoComplete="current-password"
                          required
                          label="CIPHER"
                          placeholder="Enter passphrase"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-[34px] text-text-tertiary hover:text-neon-cyan transition-colors"
                        >
                          {showPassword ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      {/* Error Message */}
                      <AnimatePresence>
                        {error && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="flex items-center gap-2 p-3 bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm"
                          >
                            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                            <span>{error}</span>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Submit Button */}
                      <NeonButton
                        type="submit"
                        disabled={isSubmitting}
                        loading={isSubmitting}
                        variant="cyan"
                        glow
                        className="w-full py-3"
                      >
                        {isSubmitting ? 'AUTHENTICATING' : 'INITIALIZE SESSION'}
                      </NeonButton>
                    </motion.form>
                  )}
                </AnimatePresence>

                {/* Footer */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 2 }}
                  className="mt-8 pt-6 border-t border-neon-cyan/10"
                >
                  <div className="flex items-center justify-between text-xs text-text-tertiary">
                    <span>SECURE AUTH v2.0</span>
                    <span className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-status-safe animate-pulse" />
                      ENCRYPTED
                    </span>
                  </div>
                </motion.div>
              </div>
            </div>

            {/* Decorative corner brackets */}
            <div className="absolute -top-2 -left-2 w-4 h-4 border-t-2 border-l-2 border-neon-cyan/50" />
            <div className="absolute -top-2 -right-2 w-4 h-4 border-t-2 border-r-2 border-neon-cyan/50" />
            <div className="absolute -bottom-2 -left-2 w-4 h-4 border-b-2 border-l-2 border-neon-cyan/50" />
            <div className="absolute -bottom-2 -right-2 w-4 h-4 border-b-2 border-r-2 border-neon-cyan/50" />
          </div>
        </motion.div>
      </div>
    </div>
  );
};

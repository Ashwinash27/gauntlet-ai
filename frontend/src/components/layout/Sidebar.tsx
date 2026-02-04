import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  FlaskConical,
  History,
  Key,
  BookOpen,
  LogOut,
  Activity,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { User } from '@/types';

export interface SidebarProps {
  user: User;
  onLogout?: () => void;
  className?: string;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: 'Overview', path: '/overview', icon: LayoutDashboard },
  { label: 'Playground', path: '/playground', icon: FlaskConical },
  { label: 'History', path: '/history', icon: History },
  { label: 'API Keys', path: '/api-keys', icon: Key },
  { label: 'Docs', path: '/docs', icon: BookOpen },
];

/**
 * Cyberpunk Neon Sidebar
 * - Orbitron font for branding
 * - Icons with glow effects
 * - System status indicator
 * - Mini stats section
 */
export const Sidebar: React.FC<SidebarProps> = ({ user, onLogout, className }) => {
  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen w-[240px] flex flex-col',
        'bg-void-base border-r border-neon-cyan/10',
        className
      )}
    >
      {/* Gradient scan line on right border */}
      <motion.div
        className="absolute right-0 top-0 w-px h-20 bg-gradient-to-b from-transparent via-neon-cyan to-transparent"
        animate={{ y: ['0vh', '80vh'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
      />

      {/* Logo & Branding */}
      <div className="p-5 border-b border-neon-cyan/10">
        <h1 className="font-display text-2xl text-neon-cyan tracking-wider text-center">
          ARGUS AI
        </h1>

        {/* System Status */}
        <div className="mt-4 flex items-center gap-2 px-3 py-2 bg-void-elevated border border-neon-cyan/10">
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-2 h-2 rounded-full bg-status-safe"
          />
          <span className="text-xs text-status-safe uppercase">System Online</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3">
        <p className="px-3 mb-2 text-[10px] text-text-tertiary uppercase tracking-widest">
          Navigation
        </p>
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 py-2.5 px-3 text-sm transition-all duration-300',
                    'border-l-2 border-transparent',
                    isActive
                      ? 'text-neon-cyan bg-neon-cyan/5 border-l-neon-cyan shadow-[inset_0_0_20px_rgba(0,240,255,0.05)]'
                      : 'text-text-secondary hover:text-text-primary hover:bg-void-elevated hover:border-l-neon-cyan/30'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <motion.div
                      whileHover={{ scale: 1.1 }}
                      className={cn(
                        'transition-colors duration-300',
                        isActive ? 'text-neon-cyan' : 'text-text-tertiary group-hover:text-neon-cyan/50'
                      )}
                    >
                      <item.icon className="w-4 h-4" />
                    </motion.div>
                    <span className="font-mono text-sm">{item.label}</span>
                    {isActive && (
                      <motion.div
                        layoutId="activeIndicator"
                        className="ml-auto w-1.5 h-1.5 rounded-full bg-neon-cyan"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ duration: 0.2 }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Mini Stats */}
      <div className="px-3 py-4 border-t border-neon-cyan/10">
        <p className="px-3 mb-3 text-[10px] text-text-tertiary uppercase tracking-widest">
          System Status
        </p>
        <div className="space-y-2 px-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-3 h-3 text-neon-cyan" />
              <span className="text-xs text-text-secondary">API</span>
            </div>
            <span className="text-xs text-status-safe">ACTIVE</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-3 h-3 text-status-warning" />
              <span className="text-xs text-text-secondary">Threats</span>
            </div>
            <span className="text-xs text-status-warning">24h</span>
          </div>
        </div>
        {/* Detection System Label */}
        <p className="mt-4 px-3 text-[10px] text-text-tertiary uppercase tracking-widest text-center">
          Detection System
        </p>
      </div>

      {/* User Section */}
      <div className="border-t border-neon-cyan/10 p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 bg-void-elevated border border-neon-cyan/20 flex items-center justify-center">
            <span className="text-xs text-neon-cyan uppercase">
              {user.email?.charAt(0) || 'U'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-text-primary truncate">{user.email}</p>
            <p className="text-[10px] text-text-tertiary uppercase">
              {user.role || 'User'}
            </p>
          </div>
        </div>

        {/* Logout Button */}
        {onLogout && (
          <motion.button
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.98 }}
            onClick={onLogout}
            className="w-full flex items-center gap-2 py-2 px-3 text-sm text-text-tertiary hover:text-status-danger hover:bg-status-danger/5 border border-transparent hover:border-status-danger/20 transition-all duration-300"
          >
            <LogOut className="w-4 h-4" />
            <span>Disconnect</span>
          </motion.button>
        )}
      </div>
    </aside>
  );
};

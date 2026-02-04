import { ParticleField } from './ParticleField';
import { GridBackground } from './GridBackground';
import { ScanLines } from './ScanLines';

interface BackgroundCompositeProps {
  showParticles?: boolean;
  showGrid?: boolean;
  showScanLines?: boolean;
  perspectiveGrid?: boolean;
  particleCount?: number;
  className?: string;
}

/**
 * Combines all background effects into a single component.
 * Use this for immersive full-screen backgrounds like the login page.
 */
export function BackgroundComposite({
  showParticles = true,
  showGrid = true,
  showScanLines = true,
  perspectiveGrid = false,
  particleCount = 50,
  className = '',
}: BackgroundCompositeProps) {
  return (
    <div className={`fixed inset-0 overflow-hidden ${className}`} style={{ zIndex: -1 }}>
      {/* Base void gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse at center, #0a0e14 0%, #05070a 100%)
          `,
        }}
      />

      {/* Grid */}
      {showGrid && <GridBackground perspective={perspectiveGrid} />}

      {/* Particles */}
      {showParticles && <ParticleField particleCount={particleCount} />}

      {/* Vignette */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at center, transparent 40%, rgba(0, 0, 0, 0.6) 100%)`,
        }}
      />

      {/* Scan lines */}
      {showScanLines && <ScanLines />}
    </div>
  );
}

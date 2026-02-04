import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Copy, Check, ExternalLink, ChevronRight } from 'lucide-react';
import { TypewriterText, ScrollReveal } from '@/components/animations';
import { NeonCard } from '@/components/ui/NeonCard';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { GridBackground } from '@/components/backgrounds';
import { cn } from '@/lib/utils';

type Language = 'curl' | 'python' | 'javascript' | 'go';

const codeExamples: Record<Language, string> = {
  curl: `curl -X POST https://api.argusai.com/v1/detect \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{"text": "User input to analyze"}'`,

  python: `import requests

response = requests.post(
    "https://api.argusai.com/v1/detect",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        "text": "User input to analyze",
        "skip_layer_3": False  # Optional: skip LLM judge
    }
)

result = response.json()

if result["is_injection"]:
    print(f"Blocked: {result['attack_type']}")
else:
    print("Safe to process")`,

  javascript: `const response = await fetch("https://api.argusai.com/v1/detect", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "YOUR_API_KEY"
  },
  body: JSON.stringify({
    text: "User input to analyze",
    skip_layer_3: false  // Optional: skip LLM judge
  })
});

const result = await response.json();

if (result.is_injection) {
  console.log(\`Blocked: \${result.attack_type}\`);
} else {
  console.log("Safe to process");
}`,

  go: `package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

func checkInjection(text string, apiKey string) (bool, error) {
    payload, _ := json.Marshal(map[string]interface{}{
        "text": text,
    })

    req, _ := http.NewRequest("POST",
        "https://api.argusai.com/v1/detect",
        bytes.NewBuffer(payload))

    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("X-API-Key", apiKey)

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return false, err
    }
    defer resp.Body.Close()

    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)

    return result["is_injection"].(bool), nil
}`,
};

const sections = [
  { id: 'quick-start', label: 'Quick Start' },
  { id: 'endpoint', label: 'Endpoint' },
  { id: 'examples', label: 'Code Examples' },
  { id: 'response', label: 'Response' },
  { id: 'layers', label: 'Detection Layers' },
  { id: 'errors', label: 'Error Codes' },
  { id: 'integration', label: 'Integration' },
];

/**
 * API Documentation page - Cyberpunk styled
 * - Sticky sidebar navigation
 * - Scroll progress indicator
 * - Syntax-highlighted code blocks
 */
export function Docs() {
  const [selectedLang, setSelectedLang] = useState<Language>('python');
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState('quick-start');
  const [scrollProgress, setScrollProgress] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return;

      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress((scrollTop / docHeight) * 100);

      // Update active section based on scroll position
      const sectionElements = sections.map((s) => document.getElementById(s.id));
      for (let i = sectionElements.length - 1; i >= 0; i--) {
        const element = sectionElements[i];
        if (element && element.getBoundingClientRect().top <= 150) {
          setActiveSection(sections[i].id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="min-h-screen bg-void-deep p-8 ml-[240px] relative" ref={containerRef}>
      <GridBackground opacity={0.02} />

      {/* Scroll progress bar */}
      <motion.div
        className="fixed top-0 left-[240px] right-0 h-0.5 bg-neon-cyan/30 z-50"
        style={{ transformOrigin: 'left' }}
      >
        <motion.div
          className="h-full bg-neon-cyan"
          style={{ width: `${scrollProgress}%` }}
        />
      </motion.div>

      <div className="max-w-6xl mx-auto relative z-10">
        <div className="flex gap-8">
          {/* Main Content */}
          <div className="flex-1 space-y-8">
            {/* Header */}
            <ScrollReveal direction="down">
              <div className="mb-8">
                <h1 className="font-display text-2xl text-neon-cyan tracking-wider mb-2">
                  <TypewriterText text="API DOCUMENTATION" speed={40} />
                </h1>
                <p className="text-text-tertiary text-sm">
                  Integrate prompt injection detection into your application
                </p>
              </div>
            </ScrollReveal>

            {/* Quick Start */}
            <section id="quick-start">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">QUICK START</h2>
                  <div className="space-y-4">
                    {[
                      { step: 1, text: 'Get your API key from the', link: '/api-keys', linkText: 'API Keys' },
                      { step: 2, text: 'Send POST requests to', code: '/v1/detect' },
                      { step: 3, text: 'Check', code: 'is_injection', suffix: 'in the response' },
                    ].map((item) => (
                      <div key={item.step} className="flex items-start gap-4">
                        <div className="w-8 h-8 flex items-center justify-center border border-neon-cyan/30 bg-neon-cyan/5">
                          <span className="text-neon-cyan font-display">{item.step}</span>
                        </div>
                        <p className="text-text-secondary flex items-center gap-2 flex-wrap pt-1">
                          {item.text}
                          {item.link && (
                            <Link to={item.link} className="text-neon-cyan hover:underline">
                              {item.linkText}
                            </Link>
                          )}
                          {item.code && (
                            <code className="px-2 py-0.5 bg-status-warning/10 text-status-warning text-sm">
                              {item.code}
                            </code>
                          )}
                          {item.suffix && <span>{item.suffix}</span>}
                        </p>
                      </div>
                    ))}
                  </div>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Endpoint */}
            <section id="endpoint">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">ENDPOINT</h2>

                  <div className="p-4 bg-void-base border border-neon-cyan/20 mb-6">
                    <code className="text-lg">
                      <span className="text-status-warning">POST</span>{' '}
                      <span className="text-neon-cyan">/v1/detect</span>
                    </code>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <h3 className="text-text-primary font-medium mb-3">Headers</h3>
                      <div className="space-y-2">
                        <div className="flex items-center gap-4 p-3 bg-void-base border border-neon-cyan/10">
                          <code className="text-neon-cyan">X-API-Key</code>
                          <NeonBadge variant="danger">required</NeonBadge>
                          <span className="text-text-tertiary text-sm">Your API key (sk-argus-...)</span>
                        </div>
                        <div className="flex items-center gap-4 p-3 bg-void-base border border-neon-cyan/10">
                          <code className="text-neon-cyan">Content-Type</code>
                          <NeonBadge variant="danger">required</NeonBadge>
                          <span className="text-text-tertiary text-sm">application/json</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-text-primary font-medium mb-3">Request Body</h3>
                      <div className="space-y-2">
                        <div className="grid grid-cols-4 gap-4 p-3 bg-void-base border border-neon-cyan/10">
                          <code className="text-neon-cyan">text</code>
                          <NeonBadge variant="danger">required</NeonBadge>
                          <span className="text-text-tertiary text-sm">string</span>
                          <span className="text-text-tertiary text-sm">User input to analyze</span>
                        </div>
                        <div className="grid grid-cols-4 gap-4 p-3 bg-void-base border border-neon-cyan/10">
                          <code className="text-neon-cyan">skip_layer_3</code>
                          <span className="text-text-tertiary text-xs">optional</span>
                          <span className="text-text-tertiary text-sm">boolean</span>
                          <span className="text-text-tertiary text-sm">Skip LLM judge (faster)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Code Examples */}
            <section id="examples">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">CODE EXAMPLES</h2>

                  {/* Language Tabs */}
                  <div className="flex gap-2 mb-4">
                    {(['curl', 'python', 'javascript', 'go'] as Language[]).map((lang) => (
                      <button
                        key={lang}
                        onClick={() => setSelectedLang(lang)}
                        className={cn(
                          'px-4 py-2 text-sm uppercase tracking-wider border transition-all duration-300',
                          selectedLang === lang
                            ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan shadow-neon-cyan'
                            : 'border-neon-cyan/20 text-text-secondary hover:border-neon-cyan/40'
                        )}
                      >
                        {lang}
                      </button>
                    ))}
                  </div>

                  {/* Code Block */}
                  <div className="relative group">
                    <pre className="p-4 bg-void-base border border-neon-cyan/20 overflow-x-auto">
                      <code className="text-text-secondary text-sm whitespace-pre">
                        {codeExamples[selectedLang]}
                      </code>
                    </pre>
                    <button
                      onClick={() => copyCode(codeExamples[selectedLang])}
                      className="absolute top-3 right-3 p-2 border border-neon-cyan/20 bg-void-elevated text-text-tertiary hover:text-neon-cyan hover:border-neon-cyan/40 transition-all opacity-0 group-hover:opacity-100"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Response */}
            <section id="response">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">RESPONSE</h2>

                  <div className="mb-6">
                    <h3 className="text-text-primary font-medium mb-3 flex items-center gap-2">
                      Success <NeonBadge variant="safe">200</NeonBadge>
                    </h3>
                    <pre className="p-4 bg-void-base border border-neon-cyan/20 overflow-x-auto">
                      <code className="text-text-secondary text-sm">{`{
  "is_injection": true,
  "confidence": 0.85,
  "attack_type": "jailbreak",
  "detected_by_layer": 2,
  "layer_results": [
    { "layer": 1, "is_injection": false, "latency_ms": 0.2 },
    { "layer": 2, "is_injection": true, "confidence": 0.85, "latency_ms": 620 }
  ],
  "latency_ms": 621.0
}`}</code>
                    </pre>
                  </div>

                  <h3 className="text-text-primary font-medium mb-3">Response Fields</h3>
                  <div className="space-y-2">
                    {[
                      { field: 'is_injection', type: 'boolean', desc: 'True if prompt injection detected' },
                      { field: 'confidence', type: 'float', desc: 'Detection confidence (0.0 - 1.0)' },
                      { field: 'attack_type', type: 'string | null', desc: 'Category: jailbreak, instruction_override, etc.' },
                      { field: 'detected_by_layer', type: 'int | null', desc: 'Which layer caught it (1, 2, or 3)' },
                      { field: 'latency_ms', type: 'float', desc: 'Total processing time in milliseconds' },
                    ].map((item) => (
                      <div key={item.field} className="grid grid-cols-3 gap-4 p-3 bg-void-base border border-neon-cyan/10">
                        <code className="text-neon-cyan">{item.field}</code>
                        <span className="text-text-tertiary text-sm">{item.type}</span>
                        <span className="text-text-tertiary text-sm">{item.desc}</span>
                      </div>
                    ))}
                  </div>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Detection Layers */}
            <section id="layers">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">DETECTION LAYERS</h2>

                  <div className="space-y-4">
                    {[
                      {
                        layer: 1,
                        name: 'Rules',
                        latency: '< 1ms',
                        desc: 'Regex patterns for known injection attacks. Catches obvious patterns like "ignore previous instructions", DAN jailbreaks, etc.',
                      },
                      {
                        layer: 2,
                        name: 'Embeddings',
                        latency: '~500ms',
                        desc: 'Semantic similarity search against 200+ known attack embeddings using OpenAI embeddings + pgvector. Catches paraphrased attacks.',
                      },
                      {
                        layer: 3,
                        name: 'LLM Judge',
                        latency: '~800ms',
                        desc: 'Claude Haiku analyzes intent and context. Catches novel attacks. Can be skipped with skip_layer_3=true.',
                      },
                    ].map((item) => (
                      <div
                        key={item.layer}
                        className={cn(
                          'p-4 border',
                          item.layer === 1 && 'border-layer-1/30 bg-layer-1/5',
                          item.layer === 2 && 'border-layer-2/30 bg-layer-2/5',
                          item.layer === 3 && 'border-layer-3/30 bg-layer-3/5'
                        )}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <NeonBadge variant={`layer${item.layer}` as 'layer1' | 'layer2' | 'layer3'}>
                              L{item.layer}
                            </NeonBadge>
                            <span className="text-text-primary font-medium">{item.name}</span>
                          </div>
                          <span className="text-text-tertiary text-sm">{item.latency}</span>
                        </div>
                        <p className="text-text-tertiary text-sm">{item.desc}</p>
                      </div>
                    ))}
                  </div>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Error Codes */}
            <section id="errors">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">ERROR CODES</h2>

                  <div className="space-y-2">
                    {[
                      { code: 401, desc: 'Invalid or missing API key' },
                      { code: 422, desc: 'Invalid request body (missing text field)' },
                      { code: 429, desc: 'Rate limit exceeded' },
                      { code: 500, desc: 'Internal server error' },
                    ].map((item) => (
                      <div key={item.code} className="flex items-center gap-4 p-3 bg-void-base border border-neon-cyan/10">
                        <NeonBadge variant="warning">{item.code}</NeonBadge>
                        <span className="text-text-tertiary text-sm">{item.desc}</span>
                      </div>
                    ))}
                  </div>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Integration Example */}
            <section id="integration">
              <ScrollReveal direction="up">
                <NeonCard className="p-6">
                  <h2 className="font-display text-lg text-neon-cyan mb-4">INTEGRATION EXAMPLE</h2>

                  <pre className="p-4 bg-void-base border border-neon-cyan/20 overflow-x-auto">
                    <code className="text-text-secondary text-sm">{`# Protect your LLM application

def process_user_message(user_input: str) -> str:
    # Step 1: Check for injection
    check = requests.post(
        "https://api.argusai.com/v1/detect",
        headers={"X-API-Key": API_KEY},
        json={"text": user_input}
    ).json()

    # Step 2: Block if injection detected
    if check["is_injection"]:
        log_blocked_request(user_input, check["attack_type"])
        return "I cannot process that request."

    # Step 3: Safe to send to your LLM
    return call_your_llm(user_input)`}</code>
                  </pre>
                </NeonCard>
              </ScrollReveal>
            </section>

            {/* Footer */}
            <div className="text-center py-8">
              <p className="text-text-tertiary text-sm">
                Need help? Test your prompts in the{' '}
                <Link to="/playground" className="text-neon-cyan hover:underline inline-flex items-center gap-1">
                  Playground <ExternalLink className="w-3 h-3" />
                </Link>
              </p>
            </div>
          </div>

          {/* Sticky Sidebar */}
          <div className="hidden lg:block w-48 flex-shrink-0">
            <div className="sticky top-24">
              <p className="text-text-tertiary text-xs uppercase tracking-wider mb-4">On this page</p>
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => scrollToSection(section.id)}
                    className={cn(
                      'w-full flex items-center gap-2 py-2 px-3 text-sm text-left transition-all duration-300 border-l-2',
                      activeSection === section.id
                        ? 'text-neon-cyan border-neon-cyan bg-neon-cyan/5'
                        : 'text-text-tertiary border-transparent hover:text-text-primary hover:border-neon-cyan/30'
                    )}
                  >
                    {activeSection === section.id && <ChevronRight className="w-3 h-3" />}
                    {section.label}
                  </button>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

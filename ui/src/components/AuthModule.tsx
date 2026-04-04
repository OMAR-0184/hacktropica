import React, { useState, useRef, useEffect } from 'react';
import { LoginForm }  from './LoginForm';
import { SignupForm } from './SignupForm';

export type AuthMode = 'login' | 'signup';

/* ── Subtle hexagon / network brand icon ─────────────────── */
function BrandIcon() {
  return (
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      {/* Outer hex ring */}
      <polygon
        points="20,2 35,10.5 35,29.5 20,38 5,29.5 5,10.5"
        stroke="rgba(14,165,233,0.5)" strokeWidth="1.2" fill="none"
      />
      {/* Inner hub */}
      <circle cx="20" cy="20" r="4" fill="#0ea5e9" opacity="0.9" />
      {/* Edges radiating */}
      <line x1="20" y1="20" x2="20" y2="5"  stroke="rgba(14,165,233,0.4)" strokeWidth="1"/>
      <line x1="20" y1="20" x2="33" y2="12" stroke="rgba(14,165,233,0.4)" strokeWidth="1"/>
      <line x1="20" y1="20" x2="33" y2="28" stroke="rgba(14,165,233,0.4)" strokeWidth="1"/>
      <line x1="20" y1="20" x2="20" y2="35" stroke="rgba(14,165,233,0.4)" strokeWidth="1"/>
      <line x1="20" y1="20" x2="7"  y2="28" stroke="rgba(14,165,233,0.4)" strokeWidth="1"/>
      <line x1="20" y1="20" x2="7"  y2="12" stroke="rgba(14,165,233,0.4)" strokeWidth="1"/>
      {/* Outer node dots */}
      <circle cx="20" cy="5"  r="2" fill="rgba(14,165,233,0.7)"/>
      <circle cx="33" cy="12" r="2" fill="rgba(14,165,233,0.7)"/>
      <circle cx="33" cy="28" r="2" fill="rgba(139,92,246,0.7)"/>
      <circle cx="20" cy="35" r="2" fill="rgba(14,165,233,0.7)"/>
      <circle cx="7"  cy="28" r="2" fill="rgba(139,92,246,0.7)"/>
      <circle cx="7"  cy="12" r="2" fill="rgba(14,165,233,0.7)"/>
    </svg>
  );
}

export function AuthModule() {
  const [mode, setMode]             = useState<AuthMode>('login');
  const [animDir, setAnimDir]       = useState<'left' | 'right'>('right');
  const [rendering, setRendering]   = useState<AuthMode>('login');
  const [isAnimating, setAnimating] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const switchTo = (next: AuthMode) => {
    if (next === mode || isAnimating) return;
    const dir = next === 'signup' ? 'right' : 'left';
    setAnimDir(dir);
    setAnimating(true);

    // Instantly swap the underlying form after a short fade
    timeoutRef.current = setTimeout(() => {
      setMode(next);
      setRendering(next);
      setAnimating(false);
    }, 200);
  };

  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  /* ── Indicator pill position ─────────────────────────────── */
  const indicatorLeft = mode === 'login' ? '4px' : 'calc(50% + 4px)';

  return (
    <div className="auth-card p-1 w-full animate-fade-up" role="main" aria-label="Authentication panel">

      {/* ─── Top accent bar ───────────────────────────── */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{
          background: 'linear-gradient(90deg, transparent 0%, rgba(14,165,233,0.6) 40%, rgba(139,92,246,0.4) 70%, transparent 100%)'
        }}
        aria-hidden="true"
      />

      <div className="px-6 pt-7 pb-6 md:px-8 md:pt-8">

        {/* ─── Header ───────────────────────────────────── */}
        <div className="flex items-center gap-4 mb-7">
          {/* Brand icon */}
          <div
            className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              background: 'rgba(14,165,233,0.06)',
              border: '1px solid rgba(14,165,233,0.2)',
              boxShadow: '0 0 16px rgba(14,165,233,0.1)'
            }}
            aria-hidden="true"
          >
            <BrandIcon />
          </div>

          <div>
            <h1 className="text-lg font-semibold text-white leading-tight">Hacktropica</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              {mode === 'login'
                ? 'Welcome back. Continue your frontier.'
                : 'Map your learning graph. Start now.'}
            </p>
          </div>
        </div>

        {/* ─── Tab switcher ────────────────────────────── */}
        <div
          className="relative flex gap-1 p-1 mb-6 rounded-xl"
          style={{ background: 'rgba(22,27,34,0.6)', border: '1px solid rgba(33,38,45,0.8)' }}
          role="tablist"
          aria-label="Authentication mode"
        >
          {/* Sliding indicator */}
          <div
            className="absolute top-1 bottom-1 rounded-lg transition-all duration-300 ease-out"
            style={{
              left:  indicatorLeft,
              width: 'calc(50% - 8px)',
              background: 'rgba(14,165,233,0.1)',
              border: '1px solid rgba(14,165,233,0.25)',
              boxShadow: '0 0 12px rgba(14,165,233,0.08)',
            }}
            aria-hidden="true"
          />

          <button
            id="tab-login"
            role="tab"
            aria-selected={mode === 'login'}
            aria-controls="panel-auth"
            onClick={() => switchTo('login')}
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
          >
            Sign In
          </button>
          <button
            id="tab-signup"
            role="tab"
            aria-selected={mode === 'signup'}
            aria-controls="panel-auth"
            onClick={() => switchTo('signup')}
            className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
          >
            Sign Up
          </button>
        </div>

        {/* ─── Form panel ──────────────────────────────── */}
        <div
          id="panel-auth"
          role="tabpanel"
          aria-labelledby={mode === 'login' ? 'tab-login' : 'tab-signup'}
          className={`transition-all duration-200 ${
            isAnimating
              ? `opacity-0 ${animDir === 'right' ? 'translate-x-2' : '-translate-x-2'} pointer-events-none`
              : 'opacity-100 translate-x-0'
          }`}
          style={{ transform: isAnimating
            ? `translateX(${animDir === 'right' ? '8px' : '-8px'})`
            : 'translateX(0)' }}
        >
          {rendering === 'login'  && <LoginForm  />}
          {rendering === 'signup' && <SignupForm />}
        </div>

        {/* ─── Mode toggle hint at bottom ──────────────── */}
        <p className="mt-5 text-center text-xs text-gray-600">
          {mode === 'login' ? (
            <>
              New to Hacktropica?{' '}
              <button
                onClick={() => switchTo('signup')}
                className="text-primary-400 hover:text-primary-300 transition-colors
                           underline underline-offset-2 font-medium focus:outline-none
                           focus-visible:ring-1 focus-visible:ring-primary-500 rounded"
              >
                Create an account
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                onClick={() => switchTo('login')}
                className="text-primary-400 hover:text-primary-300 transition-colors
                           underline underline-offset-2 font-medium focus:outline-none
                           focus-visible:ring-1 focus-visible:ring-primary-500 rounded"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

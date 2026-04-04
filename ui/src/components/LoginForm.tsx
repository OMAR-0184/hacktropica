import React, { useState, useId } from 'react';
import { Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

/* ── Google colour SVG ───────────────────────────────────── */
function GoogleIcon() {
  return (
    <svg role="img" aria-label="Google" viewBox="0 0 24 24" className="w-4.5 h-4.5 shrink-0" xmlns="http://www.w3.org/2000/svg" width="18" height="18">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  );
}

interface FieldError { email?: string; password?: string; }

export function LoginForm() {
  const id = useId();
  const emailId    = `${id}-email`;
  const passwordId = `${id}-password`;
  const rememberMeId = `${id}-remember`;

  const [email,       setEmail]       = useState('');
  const [password,    setPassword]    = useState('');
  const [showPass,    setShowPass]    = useState(false);
  const [rememberMe,  setRememberMe]  = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldError>({});
  const [globalError, setGlobalError] = useState('');
  const [success,     setSuccess]     = useState(false);

  /* ── Validation ─────────────────────────────────── */
  const validate = (): boolean => {
    const errs: FieldError = {};
    if (!email.trim())                              errs.email    = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = 'Enter a valid email address.';
    if (!password)                                  errs.password = 'Password is required.';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  /* ── Google OAuth ───────────────────────────────── */
  const handleGoogleLogin = async () => {
    setLoading(true);
    setGlobalError('');
    try {
      const res = await fetch('http://localhost:8000/auth/oauth/google');
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        const token = data.access_token || data.token;
        if (token) localStorage.setItem('hacktropica_token', token);
        window.location.href = '/dashboard';
      } else {
        throw new Error('Google login is currently unavailable.');
      }
    } catch (err: any) {
      setGlobalError(err.message || 'Could not complete Google sign-in.');
    } finally {
      setLoading(false);
    }
  };

  /* ── Email / Password login ─────────────────────── */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setGlobalError('');
    setSuccess(false);

    try {
      const res = await fetch('/auth/login/json', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email: email.trim(), password }),
      });

      if (res.status === 422) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        if (Array.isArray(detail)) {
          const errs: FieldError = {};
          detail.forEach((d: any) => {
            const loc = d.loc?.[d.loc.length - 1];
            if (loc === 'email')    errs.email    = d.msg;
            if (loc === 'password') errs.password = d.msg;
          });
          setFieldErrors(errs);
        } else {
          setGlobalError(typeof detail === 'string' ? detail : 'Validation failed. Please check your inputs.');
        }
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || 'Invalid email or password.');
      }

      const data = await res.json();
      const token = data.access_token || data.token;
      if (token) {
        if (rememberMe) {
          localStorage.setItem('hacktropica_token', token);
        } else {
          sessionStorage.setItem('hacktropica_token', token);
          localStorage.removeItem('hacktropica_token');
        }
      }
      setSuccess(true);
      setTimeout(() => { window.location.href = '/dashboard'; }, 600);
    } catch (err: any) {
      setGlobalError(err.message || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4"
      noValidate
      aria-label="Login form"
    >
      {/* Global error banner */}
      {globalError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 px-3.5 py-3 rounded-xl text-sm
                     bg-error/8 border border-error/20 text-red-400 animate-fade-up"
        >
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" aria-hidden="true" />
          <span>{globalError}</span>
        </div>
      )}

      {/* Success banner */}
      {success && (
        <div
          role="status"
          className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl text-sm
                     bg-success/8 border border-success/20 text-green-400 animate-fade-up"
        >
          <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>Login successful — redirecting…</span>
        </div>
      )}

      {/* ── Email ─────────────────────────────────── */}
      <div>
        <label htmlFor={emailId} className="input-label">Email</label>
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
            <Mail
              className={`w-4 h-4 transition-colors ${fieldErrors.email ? 'text-red-400' : 'text-gray-600'}`}
              aria-hidden="true"
            />
          </span>
          <input
            id={emailId}
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (fieldErrors.email) setFieldErrors(p => ({ ...p, email: undefined }));
              setGlobalError('');
            }}
            className={`input-field pl-10 ${fieldErrors.email ? 'input-field-error' : ''}`}
            placeholder="you@example.com"
            disabled={loading}
            aria-invalid={!!fieldErrors.email}
            aria-describedby={fieldErrors.email ? `${emailId}-error` : undefined}
          />
        </div>
        {fieldErrors.email && (
          <p id={`${emailId}-error`} role="alert" className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" aria-hidden="true" />
            {fieldErrors.email}
          </p>
        )}
      </div>

      {/* ── Password ──────────────────────────────── */}
      <div>
        <label htmlFor={passwordId} className="input-label">Password</label>
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
            <Lock
              className={`w-4 h-4 transition-colors ${fieldErrors.password ? 'text-red-400' : 'text-gray-600'}`}
              aria-hidden="true"
            />
          </span>
          <input
            id={passwordId}
            type={showPass ? 'text' : 'password'}
            autoComplete="current-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password) setFieldErrors(p => ({ ...p, password: undefined }));
              setGlobalError('');
            }}
            className={`input-field pl-10 pr-11 ${fieldErrors.password ? 'input-field-error' : ''}`}
            placeholder="••••••••••••"
            disabled={loading}
            aria-invalid={!!fieldErrors.password}
            aria-describedby={fieldErrors.password ? `${passwordId}-error` : undefined}
          />
          <button
            type="button"
            onClick={() => setShowPass(p => !p)}
            className="absolute inset-y-0 right-0 pr-3.5 flex items-center
                       text-gray-600 hover:text-gray-300 transition-colors
                       focus:outline-none focus-visible:text-primary-400"
            aria-label={showPass ? 'Hide password' : 'Show password'}
            tabIndex={0}
          >
            {showPass
              ? <EyeOff className="w-4 h-4" aria-hidden="true" />
              : <Eye    className="w-4 h-4" aria-hidden="true" />}
          </button>
        </div>
        {fieldErrors.password && (
          <p id={`${passwordId}-error`} role="alert" className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" aria-hidden="true" />
            {fieldErrors.password}
          </p>
        )}
      </div>

      {/* ── Remember Me + Forgot Password ─────────── */}
      <div className="flex items-center justify-between pt-1">
        {/* Custom Toggle */}
        <label
          className="flex items-center gap-2.5 cursor-pointer group select-none"
          htmlFor={rememberMeId}
        >
          <div className="relative">
            <input
              id={rememberMeId}
              type="checkbox"
              className="sr-only"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={loading}
              aria-label="Remember me"
            />
            {/* Track */}
            <div
              className={`toggle-track ${rememberMe ? 'checked' : ''}`}
              aria-hidden="true"
              onClick={() => !loading && setRememberMe(p => !p)}
            />
            {/* Thumb */}
            <div
              className={`toggle-thumb ${rememberMe ? 'checked' : ''}`}
              aria-hidden="true"
            />
          </div>
          <span className="text-xs text-gray-500 group-hover:text-gray-300 transition-colors">
            Remember me
          </span>
        </label>

        <a
          href="#forgot"
          className="text-xs text-gray-500 hover:text-primary-400 transition-colors
                     focus:outline-none focus-visible:underline focus-visible:text-primary-400"
          onClick={(e) => e.preventDefault()}
        >
          Forgot password?
        </a>
      </div>

      {/* ── Submit ────────────────────────────────── */}
      <button
        id="login-submit-btn"
        type="submit"
        disabled={loading || success}
        className="btn-primary mt-2"
        aria-label="Sign in to your account"
      >
        {loading && !success && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
        {success  && <CheckCircle2 className="w-4 h-4" aria-hidden="true" />}
        {loading && !success ? 'Authenticating…' : success ? 'Redirecting…' : 'Sign In'}
      </button>

      {/* ── Divider ───────────────────────────────── */}
      <div className="divider" aria-hidden="true">
        <span>or continue with</span>
      </div>

      {/* ── Google OAuth ──────────────────────────── */}
      <button
        id="login-google-btn"
        type="button"
        disabled={loading}
        onClick={handleGoogleLogin}
        className="btn-social"
        aria-label="Sign in with Google"
      >
        <GoogleIcon />
        <span>Continue with Google</span>
      </button>
    </form>
  );
}

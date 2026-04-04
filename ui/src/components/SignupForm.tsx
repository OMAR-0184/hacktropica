import React, { useState, useId } from 'react';
import {
  Mail, Lock, User, Eye, EyeOff,
  Info, Loader2, AlertCircle, CheckCircle2
} from 'lucide-react';



/* ── Password strength logic ─────────────────────────────── */
type Strength = 0 | 1 | 2 | 3 | 4;

function getStrength(pass: string): Strength {
  if (!pass) return 0;
  let s = 0;
  if (pass.length >= 8)            s++;
  if (pass.length >= 14)           s++;
  if (/[A-Z]/.test(pass) && /[a-z]/.test(pass)) s++;
  if (/[0-9]/.test(pass))          s++;
  if (/[^A-Za-z0-9]/.test(pass))  s++;
  return Math.min(4, s) as Strength;
}

const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong'];
const STRENGTH_COLORS = ['', 'weak', 'fair', 'good', 'strong'];

/* ── Field error shape ───────────────────────────────────── */
interface FieldError { email?: string; password?: string; username?: string; }

export function SignupForm() {
  const id = useId();
  const emailId    = `${id}-email`;
  const passwordId = `${id}-password`;
  const usernameId = `${id}-username`;

  const [email,        setEmail]       = useState('');
  const [password,     setPassword]    = useState('');
  const [username,     setUsername]    = useState('');
  const [showPass,     setShowPass]    = useState(false);
  const [loading,      setLoading]     = useState(false);
  const [fieldErrors,  setFieldErrors] = useState<FieldError>({});
  const [globalError,  setGlobalError] = useState('');
  const [success,      setSuccess]     = useState(false);

  const strength = getStrength(password);

  /* ── Validation ─────────────────────────────────── */
  const validate = (): boolean => {
    const errs: FieldError = {};
    if (!email.trim())
      errs.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      errs.email = 'Enter a valid email address.';
    if (!password)
      errs.password = 'Password is required.';
    else if (password.length < 8)
      errs.password = 'Password must be at least 8 characters.';
    if (username && username.length < 3)
      errs.username = 'Username must be at least 3 characters.';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };



  /* ── Email / Password register ──────────────────── */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setGlobalError('');
    setSuccess(false);

    try {
      const body: Record<string, string> = { email: email.trim(), password };
      if (username.trim()) body.username = username.trim();

      const res = await fetch('/auth/register', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });

      if (res.status === 422) {
        const data = await res.json().catch(() => ({}));
        const detail = data?.detail;
        if (Array.isArray(detail)) {
          const errs: FieldError = {};
          detail.forEach((d: any) => {
            const loc = d.loc?.[d.loc.length - 1];
            if (loc === 'email')    errs.email    = d.msg;
            if (loc === 'password') errs.password = d.msg;
            if (loc === 'username') errs.username = d.msg;
          });
          setFieldErrors(errs);
        } else {
          setGlobalError(typeof detail === 'string' ? detail : 'Validation failed.');
        }
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || 'Could not create account. This email may already be in use.');
      }

      const data = await res.json();
      const token = data.access_token || data.token;
      if (token) {
        localStorage.setItem('hacktropica_token', token);
        setSuccess(true);
        setTimeout(() => { window.location.href = '/dashboard'; }, 700);
      } else {
        setSuccess(true);
        // No token → prompt them to log in
        setTimeout(() => { window.location.reload(); }, 1200);
      }
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
      aria-label="Sign up form"
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
          <span>Account created! Redirecting…</span>
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

      {/* ── Username (optional) ───────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label htmlFor={usernameId} className="input-label mb-0">
            Username
            <span className="ml-1.5 font-normal text-gray-600 normal-case tracking-normal">(optional)</span>
          </label>

          {/* Tooltip */}
          <div className="tooltip-wrap" tabIndex={0} aria-label="Username hint">
            <Info className="w-3.5 h-3.5 text-gray-600 cursor-help hover:text-primary-400 transition-colors" aria-hidden="true" />
            <div className="tooltip-content" role="tooltip">
              <span className="font-medium text-white block mb-0.5">Auto-generated username</span>
              If left blank, a unique username will be generated for you based on the graph topology of your learning path.
            </div>
          </div>
        </div>

        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
            <User
              className={`w-4 h-4 transition-colors ${fieldErrors.username ? 'text-red-400' : 'text-gray-600'}`}
              aria-hidden="true"
            />
          </span>
          <input
            id={usernameId}
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              if (fieldErrors.username) setFieldErrors(p => ({ ...p, username: undefined }));
            }}
            className={`input-field pl-10 font-mono ${fieldErrors.username ? 'input-field-error' : ''}`}
            placeholder="anon_node_∞"
            disabled={loading}
            aria-invalid={!!fieldErrors.username}
            aria-describedby={fieldErrors.username ? `${usernameId}-error` : `${usernameId}-hint`}
          />
        </div>
        {fieldErrors.username ? (
          <p id={`${usernameId}-error`} role="alert" className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" aria-hidden="true" />
            {fieldErrors.username}
          </p>
        ) : (
          <p id={`${usernameId}-hint`} className="mt-1.5 text-xs text-gray-600">
            Leave blank — we'll generate one from your learning graph.
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
            autoComplete="new-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password) setFieldErrors(p => ({ ...p, password: undefined }));
              setGlobalError('');
            }}
            className={`input-field pl-10 pr-11 ${fieldErrors.password ? 'input-field-error' : ''}`}
            placeholder="Use a strong passphrase"
            disabled={loading}
            aria-invalid={!!fieldErrors.password}
            aria-describedby={`${passwordId}-strength ${fieldErrors.password ? `${passwordId}-error` : ''}`}
          />
          <button
            type="button"
            onClick={() => setShowPass(p => !p)}
            className="absolute inset-y-0 right-0 pr-3.5 flex items-center
                       text-gray-600 hover:text-gray-300 transition-colors
                       focus:outline-none focus-visible:text-primary-400"
            aria-label={showPass ? 'Hide password' : 'Show password'}
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

        {/* Strength bar */}
        {password.length > 0 && (
          <div className="mt-2.5 space-y-1.5">
            <div className="flex gap-1.5" role="meter" aria-label="Password strength" aria-valuenow={strength} aria-valuemin={0} aria-valuemax={4}>
              {[1, 2, 3, 4].map(i => (
                <div
                  key={i}
                  id={i === 1 ? `${passwordId}-strength` : undefined}
                  className={`strength-bar ${i <= strength ? STRENGTH_COLORS[strength] : ''}`}
                  aria-hidden="true"
                />
              ))}
            </div>
            {strength > 0 && (
              <p className={`text-xs font-medium ${
                strength === 1 ? 'text-red-400'
                : strength === 2 ? 'text-yellow-400'
                : strength === 3 ? 'text-green-400'
                : 'text-primary-400'
              }`}>
                {STRENGTH_LABELS[strength]}
                {strength < 3 && (
                  <span className="text-gray-600 font-normal ml-1">
                    — {strength === 1 ? 'try adding uppercase & numbers'
                      : 'try adding a symbol or more length'}
                  </span>
                )}
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Submit ────────────────────────────────── */}
      <button
        id="signup-submit-btn"
        type="submit"
        disabled={loading || success}
        className="btn-primary mt-2"
        aria-label="Create your account"
      >
        {loading && !success && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
        {success  && <CheckCircle2 className="w-4 h-4" aria-hidden="true" />}
        {loading && !success ? 'Creating account…' : success ? 'Account created!' : 'Create Account'}
      </button>


    </form>
  );
}

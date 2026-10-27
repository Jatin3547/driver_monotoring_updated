import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, AlertCircle, Sparkles, Car, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { APP_NAME } from '@/utils/constants';
import { USE_MOCK_DATA, API_BASE_URL } from '@/services/config';
import { useAuth } from '@/hooks/useAuth';
import { isDriverRole, isManagerRole, homePathForRole } from '@/utils/roles';
import type { LoginPortal } from '@/services/api/authService';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loginAsDemo, loading, error } = useAuth();
  const [portal, setPortal] = useState<LoginPortal>('manager');
  const [email, setEmail] = useState('admin@fleetguard.demo');
  const [password, setPassword] = useState('admin123');
  const [localError, setLocalError] = useState<string | null>(null);

  function switchPortal(p: LoginPortal) {
    setPortal(p);
    setLocalError(null);
    if (p === 'manager') {
      setEmail('admin@fleetguard.demo');
      setPassword('admin123');
    } else {
      setEmail('arjun.mehta@fleetmail.com');
      setPassword('');
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLocalError(null);

    // Read from the DOM at submit time as well as maintaining controlled state.
    // Browser/password-manager autofill may update an input without dispatching
    // React's onChange, leaving state empty while the fields look populated.
    const formData = new FormData(e.currentTarget);
    const submittedEmail = String(formData.get('username') ?? '').trim();
    const submittedPassword = String(formData.get('password') ?? '');

    try {
      await login(submittedEmail, submittedPassword, portal);
      // After login, AuthContext sets user; redirect based on role
      // We read it from the context via the hook after the login promise resolves
      // but since login updates state asynchronously, use a small workaround:
      // The navigate happens after login resolves; the auth context will have updated.
      // Navigate to the portal home - the role guard in AppRoutes will enforce the rest.
      navigate(portal === 'driver' ? '/driver' : '/');
    } catch (err: unknown) {
      const errStr = String(err);
      const isNetworkIssue =
        err instanceof TypeError ||
        errStr.includes('Failed to fetch') ||
        errStr.includes('Network') ||
        errStr.includes('Cannot reach');

      if (isNetworkIssue && portal === 'manager') {
        setLocalError(
          'Backend is offline in this preview environment. Click "Continue as Demo Fleet Manager" below to open the dashboard.',
        );
      } else {
        setLocalError(err instanceof Error ? err.message : 'Sign-in failed. Please check your credentials.');
      }
    }
  }

  function handleDemoLogin() {
    setLocalError(null);
    loginAsDemo(portal);
    navigate(portal === 'driver' ? '/driver' : '/');
  }

  const isManager = portal === 'manager';

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-muted px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <span className="w-11 h-11 rounded-lg bg-brand-blue flex items-center justify-center mb-3">
            <ShieldCheck size={22} className="text-white" />
          </span>
          <h1 className="text-lg font-semibold text-text-primary">{APP_NAME}</h1>
          <p className="text-xs text-text-muted mt-1">AI Driver Monitoring &amp; Fleet Management</p>
        </div>

        {/* Portal Selector */}
        <div className="flex rounded-lg border border-border bg-surface-muted p-1 mb-4 gap-1">
          <button
            type="button"
            id="portal-manager"
            onClick={() => switchPortal('manager')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
              isManager
                ? 'bg-brand-blue text-white shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <LayoutDashboard size={13} />
            Fleet Manager
          </button>
          <button
            type="button"
            id="portal-driver"
            onClick={() => switchPortal('driver')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
              !isManager
                ? 'bg-brand-blue text-white shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Car size={13} />
            Driver
          </button>
        </div>

        <div className="bg-surface border border-border rounded-lg p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-text-primary mb-1">
            {isManager ? 'Fleet Manager Sign In' : 'Driver Sign In'}
          </h2>
          <p className="text-xs text-text-muted mb-5">
            {isManager
              ? <>Demo: <span className="font-mono text-text-primary">admin@fleetguard.demo</span> / <span className="font-mono text-text-primary">admin123</span></>
              : <>Use your driver email and password (e.g. <span className="font-mono text-text-primary">arjun.mehta@fleetmail.com</span>).</>}
          </p>

          {(error || localError) && (
            <div className="flex items-start gap-2 bg-status-danger-bg border border-status-danger-border text-status-danger-text text-xs rounded-md px-3 py-2 mb-4 animate-in fade-in duration-150">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <div className="flex-1">
              <span>
                 {localError ??
                  (typeof error === 'string'
                   ? error
                   : error == null
                    ? ''
                    : String(error))}
              </span>
                {portal === 'manager' && (
                  <div className="mt-1.5">
                    <button
                      type="button"
                      onClick={handleDemoLogin}
                      className="underline font-semibold hover:opacity-90 cursor-pointer text-[11px]"
                    >
                      Click here to enter in Demo Mode immediately
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-text-secondary mb-1.5">
                Email
              </label>
              <div className="relative">
                <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  id="email"
                  name="username"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={isManager ? 'admin@fleetguard.demo' : 'driver@fleetmail.com'}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-border bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-blue/40"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-text-secondary mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-border bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-blue/40"
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center gap-2 text-text-secondary">
                <input type="checkbox" defaultChecked className="rounded border-border" />
                Remember me
              </label>
              {isManager && (
                <button
                  type="button"
                  onClick={() => {
                    setEmail('admin@fleetguard.demo');
                    setPassword('admin123');
                  }}
                  className="text-brand-blue hover:underline cursor-pointer"
                >
                  Auto-fill demo
                </button>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Signing in…' : `Sign in as ${isManager ? 'Fleet Manager' : 'Driver'}`}
            </Button>

            {/* Standalone Demo Mode Button for Cloud Previews / Google AI Studio */}
            {isManager && (
              <div className="pt-2 border-t border-border mt-3">
                <button
                  type="button"
                  onClick={handleDemoLogin}
                  className="w-full py-2 px-3 rounded-md border border-brand-blue/30 bg-brand-blue/5 text-brand-blue hover:bg-brand-blue/10 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Sparkles size={14} />
                  Continue as Demo Fleet Manager (No Backend Required)
                </button>
              </div>
            )}
          </form>
        </div>

        <p className="text-center text-xs text-text-muted mt-5">
          {USE_MOCK_DATA
            ? 'Running in standalone demo mode with simulated telemetry.'
            : `API Endpoint: ${API_BASE_URL}`}
        </p>
      </div>
    </div>
  );
}

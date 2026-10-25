import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, AlertCircle, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { APP_NAME } from '@/utils/constants';
import { USE_MOCK_DATA, API_BASE_URL } from '@/services/config';
import { useAuth } from '@/hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loginAsDemo, loading, error } = useAuth();
  const [email, setEmail] = useState('admin@fleetguard.demo');
  const [password, setPassword] = useState('admin123');
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      const errStr = String(err);
      const isNetworkIssue =
        err instanceof TypeError ||
        errStr.includes('Failed to fetch') ||
        errStr.includes('Network') ||
        errStr.includes('Cannot reach');

      if (isNetworkIssue) {
        setLocalError('Backend is offline in this preview environment. Click "Continue as Demo Admin" below to open the dashboard.');
      } else {
        setLocalError(err instanceof Error ? err.message : 'Sign-in failed. Please check your credentials.');
      }
    }
  }

  function handleDemoLogin() {
    setLocalError(null);
    loginAsDemo();
    navigate('/');
  }

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

        <div className="bg-surface border border-border rounded-lg p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-text-primary mb-1">Sign in</h2>
          <p className="text-xs text-text-muted mb-5">
            Sign in with a registered account, or use the seeded demo login: <span className="font-mono text-text-primary">admin@fleetguard.demo</span> / <span className="font-mono text-text-primary">admin123</span>
          </p>

          {(error || localError) && (
            <div className="flex items-start gap-2 bg-status-danger-bg border border-status-danger-border text-status-danger-text text-xs rounded-md px-3 py-2 mb-4 animate-in fade-in duration-150">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <div className="flex-1">
                <span>{localError ?? error}</span>
                <div className="mt-1.5">
                  <button
                    type="button"
                    onClick={handleDemoLogin}
                    className="underline font-semibold hover:opacity-90 cursor-pointer text-[11px]"
                  >
                    Click here to enter in Demo Mode immediately
                  </button>
                </div>
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
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@fleetcompany.com"
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
                  type="password"
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
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>

            {/* Standalone Demo Mode Button for Cloud Previews / Google AI Studio */}
            <div className="pt-2 border-t border-border mt-3">
              <button
                type="button"
                onClick={handleDemoLogin}
                className="w-full py-2 px-3 rounded-md border border-brand-blue/30 bg-brand-blue/5 text-brand-blue hover:bg-brand-blue/10 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <Sparkles size={14} />
                Continue as Demo Admin (No Backend Required)
              </button>
            </div>
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

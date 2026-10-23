import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { APP_NAME } from '@/utils/constants';
import { USE_MOCK_DATA } from '@/services/config';
import { useAuth } from '@/hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loading, error } = useAuth();
  const [email, setEmail] = useState('admin@fleetguard.demo');
  const [password, setPassword] = useState('admin123');
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (USE_MOCK_DATA) {
      // Mock mode: UI placeholder only, matches original Phase 1 behavior
      // — no backend call, any input proceeds straight to the dashboard.
      navigate('/');
      return;
    }

    // Real mode: authenticate against the FastAPI backend.
    try {
      await login(email, password);
      navigate('/');
    } catch {
      // error state is already set by useAuth; nothing further to do.
      setLocalError('Sign-in failed. Check the backend is running and your credentials are correct.');
    }
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

        <div className="bg-surface border border-border rounded-lg p-6">
          <h2 className="text-sm font-semibold text-text-primary mb-1">Sign in</h2>
          <p className="text-xs text-text-muted mb-5">
            {USE_MOCK_DATA
              ? 'Demo mode: any input signs you in — no backend required.'
              : 'Sign in with a registered account, or use the seeded demo login: admin@fleetguard.demo / admin123'}
          </p>

          {!USE_MOCK_DATA && (error || localError) && (
            <div className="flex items-start gap-2 bg-status-danger-bg border border-status-danger-border text-status-danger-text text-xs rounded-md px-3 py-2 mb-4">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>{error ?? localError}</span>
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
                <input type="checkbox" className="rounded border-border" />
                Remember me
              </label>
              <span className="text-brand-blue cursor-not-allowed opacity-60">Forgot password?</span>
            </div>

            <Button type="submit" className="w-full" disabled={!USE_MOCK_DATA && loading}>
              {!USE_MOCK_DATA && loading ? 'Signing in…' : 'Sign in'}
            </Button>

            <button
              type="button"
              onClick={() => {
                setEmail('admin@fleetguard.demo');
                setPassword('admin123');
              }}
              className="w-full py-1.5 text-xs text-brand-blue hover:underline text-center cursor-pointer"
            >
              Click here to auto-fill demo credentials
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-text-muted mt-5">
          {USE_MOCK_DATA
            ? 'Set VITE_USE_MOCK=false to authenticate against the real backend.'
            : 'Authenticated against the FastAPI backend at ' + import.meta.env.VITE_API_BASE_URL}
        </p>
      </div>
    </div>
  );
}

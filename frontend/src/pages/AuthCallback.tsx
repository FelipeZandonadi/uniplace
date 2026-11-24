import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { Session } from '../api';
import { useAuth } from '../auth';
import { Loading } from '../components/UI';

let callbackPromise: Promise<Session> | null = null;

export function AuthCallback() {
  const { login } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    let active = true;
    if (!callbackPromise) callbackPromise = (async () => {
      const query = new URLSearchParams(window.location.search);
      const state = query.get('state');
      const stored = sessionStorage.getItem('uniplace_sso_state');
      sessionStorage.removeItem('uniplace_sso_state');
      if (!state || !stored || state !== stored) throw new ApiError('', 'invalid_state', 400);
      const error = query.get('error');
      if (error) throw new ApiError('', error, 400);
      const code = query.get('code');
      if (!code) throw new ApiError('', 'invalid_code', 400);
      return api<Session>('/api/auth/sso/callback/', { method: 'POST', body: JSON.stringify({ code, state }) }, false);
    })();
    callbackPromise.then(session => {
      if (active) {
        login(session);
        navigate('/', { replace: true });
      }
    }).catch(error => {
      if (active) navigate(
        `/login?error=${encodeURIComponent(error instanceof ApiError ? error.code : 'unknown')}`,
        { replace: true },
      );
    });
    return () => {
      active = false;
    };
  }, [login, navigate]);
  return <div className="center-screen">
    <Loading text="Concluindo sua entrada..." />
  </div>;
}

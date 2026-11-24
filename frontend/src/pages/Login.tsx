import { useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { Icon } from '../components/Icon';
import { Logo } from '../components/Layout';
import { Loading } from '../components/UI';
import { authMessages, message } from '../data';

export function Login() {
  const { user, loading } = useAuth();
  const [params] = useSearchParams();
  const [error, setError] = useState(
    params.get('error')
      ? authMessages[params.get('error')!] || 'Não foi possível entrar. Tente novamente.'
      : '',
  );
  const [busy, setBusy] = useState(false);
  if (loading) return <div className="center-screen">
    <Loading text="Preparando sua sessão..." />
  </div>;
  if (user) return <Navigate to="/" replace />;
  async function start() {
    setBusy(true);
    setError('');
    try {
      const result = await api<{
        authorize_url: string;
        state: string
      }>('/api/auth/sso/start/', {}, false);
      sessionStorage.setItem('uniplace_sso_state', result.state);
      window.location.assign(result.authorize_url);
    } catch (e) {
      setError(e instanceof ApiError && authMessages[e.code] || message(e));
      setBusy(false);
    }
  }
  return <main className="auth-page">
    <div className="auth-top">
      <Logo />
      <span>COMUNIDADE UNIVERSITÁRIA · UEM</span>
    </div>
    <section className="auth-card">
      <div className="auth-symbol">
        <Icon name="board" size={25} />
      </div>
      <h1>Bem-vindo de volta!</h1>
      <p
        className="auth-description"
      >Entre com a sua conta institucional para acessar o mural de avisos, oportunidades e eventos.</p>
      {error && <div className="banner error" role="alert">
        {error}
      </div>}
      <button className="button primary auth-button" onClick={() => void start()} disabled={busy}>
        {busy ? 'Conectando...' : 'Entrar com SSO Institucional'}
        {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="arrow" size={19} />}
      </button>
      <div className="security-note">
        <Icon name="lock" size={19} />
        <p>A UniPlace não armazena a sua senha. A autenticação é feita pelo SSO da universidade.</p>
      </div>
    </section>
    <p className="auth-bottom">A sua vida universitária em um só lugar.</p>
  </main>;
}

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { api, refresh, setAccess } from './api';
import type { User, Session } from './api';
import { Loading } from './components/UI';

type AuthValue = {
  user: User | null;
  loading: boolean;
  login: (session: Session) => void;
  logout: () => Promise<void>;
  canPublish: boolean;
  canManageJobs: boolean
};

const AuthContext = createContext<AuthValue>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    refresh().then(session => {
      if (active) setUser(session.user);
    }).catch(() => { }).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);
  const login = useCallback((session: Session) => {
    setAccess(session.access);
    setUser(session.user);
  }, []);
  const logout = useCallback(async () => {
    try {
      await api('/api/auth/logout/', { method: 'POST' }, false);
    } finally {
      setAccess(null);
      setUser(null);
      window.location.assign('/login');
    }
  }, []);
  return <AuthContext.Provider value={{
    user,
    loading,
    login,
    logout,
    canPublish: !!user && ['professor', 'colaborador', 'admin'].includes(user.role),
    canManageJobs: !!user && ['colaborador', 'admin'].includes(user.role)
  }}>
    {children}
  </AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-screen">
    <Loading text="Preparando sua sessão..." />
  </div>;
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}

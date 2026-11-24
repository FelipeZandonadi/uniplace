export type Role = 'aluno' | 'professor' | 'colaborador' | 'admin';

export interface User {
  id: number;
  email: string;
  name: string;
  ra: string;
  role: Role;
  course: string;
}

export interface Author {
  id: number;
  name: string;
  role: Role;
}

export type Session = {
  access: string;
  user: User;
};

export class ApiError extends Error {
  code: string;
  status: number;
  fields: Record<string, string[]>;

  constructor(
    message: string,
    code: string,
    status: number,
    fields: Record<string, string[]> = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}

let access: string | null = null;

let refreshing: Promise<Session> | null = null;

export function setAccess(token: string | null) {
  access = token;
}

async function parse<T>(response: Response): Promise<T> {
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const fields = data && typeof data === 'object'
      ? Object.fromEntries(
        Object.entries(data).filter(([, value]) => Array.isArray(value)),
      ) as Record<string, string[]>
      : {};
    throw new ApiError(
      data?.detail || 'Não foi possível concluir a solicitação. Tente novamente.',
      data?.code || '',
      response.status,
      fields,
    );
  }
  return data as T;
}

export function refresh(): Promise<Session> {
  if (!refreshing) refreshing = fetch('/api/auth/refresh/', {
    method: 'POST',
    credentials: 'same-origin',
  }).then(parse<Session>).then(session => {
    setAccess(session.access);
    return session;
  }).finally(() => {
    refreshing = null;
  });
  return refreshing;
}

export async function api<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (access) headers.set('Authorization', `Bearer ${access}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' });
  if (response.status === 401 && retry && await refresh().then(() => true, () => false)) {
    return api<T>(path, options, false);
  }
  if (response.status === 401) {
    // Sessão perdida: recarregar em /login zera o estado da aplicação.
    setAccess(null);
    if (window.location.pathname !== '/login') window.location.assign('/login');
  }
  return parse<T>(response);
}

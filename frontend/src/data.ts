import type { Categoria, TipoVaga, StatusCandidatura } from './api';

export const categories: Record<Categoria, string> = {
  aviso: 'Avisos',
  prazo: 'Prazos',
  alerta: 'Alertas',
  evento: 'Eventos',
};

export const types: Record<TipoVaga, string> = {
  estagio: 'Estágio',
  bolsa: 'Bolsa',
  monitoria: 'Monitoria',
};

export const statuses: Record<StatusCandidatura, string> = {
  enviada: 'Enviada',
  em_analise: 'Em análise',
  aprovada: 'Aprovada',
  recusada: 'Recusada'
};

// Só data ("2026-12-01") o JS lê como meia-noite UTC: formatar em UTC. Data e hora: fuso do usuário.
export const date = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeZone: value.length === 10 ? 'UTC' : undefined })
    .format(new Date(value));

export const message = (error: unknown) =>
  error instanceof Error ? error.message : 'Não foi possível conectar. Tente novamente.';

export const authMessages: Record<string, string> = {
  domain_not_allowed: 'Apenas e-mails institucionais @uem.br podem acessar a UniPlace.',
  user_inactive: 'Sua conta está desativada. Procure a administração da UniPlace.',
  invalid_state: 'Sua sessão expirou. Tente entrar novamente.',
  invalid_code: 'Sua sessão expirou. Tente entrar novamente.',
  sso_unavailable: 'O SSO está fora do ar. Tente novamente mais tarde.',
  throttled: 'Muitas tentativas de login. Aguarde um minuto e tente novamente.',
  access_denied: 'Login cancelado. Você pode tentar novamente quando quiser.'
};

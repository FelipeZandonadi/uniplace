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

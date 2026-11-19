# UniPlace — Plataforma Central de Comunicação Universitária

Projeto da disciplina de Construção de Software (UEM, 2026).

## Equipe

DANIEL KOBATA BARBOSA RA140453\
FELIPE ZANDONADI DOS SANTOS RA138579\
GUSTAVO KIMURA ROMERO RA140641\
MATHEUS ENRYCO MARQUES RA140503\
MIGUEL SILVA RAMPAZZO RA140768

## Objetivo

Atuar como um hub centralizador de comunicação e serviços acadêmicos, facilitando o acesso a informações essenciais e otimizando processos institucionais de forma ágil e organizada.

## Descrição do software

Plataforma web/mobile contemplando: autenticação via SSO institucional, mural inteligente de comunicados com notificações, calendário dinâmico, sistema de suporte e ouvidoria, gestão de oportunidades (estágios/monitorias) e repositório de documentos institucionais. O sistema focará em agregar recursos, sem substituir sistemas críticos (ex: sistema acadêmico de notas), apenas integrando-se a eles.

## Escopo da Sprint 1 (MVP)

| Item | Onde |
|---|---|
| US01 · Autenticação SSO via **Adapter** + **Mock** (Plano B) · T01.1–T01.4 | `backend/accounts/sso.py`, `backend/mock_sso/` |
| T15.1 PostgreSQL · T15.2 entidade Usuário · T15.3 carga de dados mockados | `docker-compose.yml`, `backend/accounts/models.py`, `manage.py seed` |
| US02/US03 · Mural de Avisos | `backend/mural/`, `frontend/src/pages/Mural.tsx` |
| US08/US09 · Vagas e candidaturas | `backend/vagas/`, `frontend/src/pages/Vagas.tsx` |

Contrato da API: [`docs/CONTRATO-API.md`](docs/CONTRATO-API.md).

## Arquitetura

```
React PWA (:5173) ──/api──▶ Django + DRF (:8000) ──ORM──▶ PostgreSQL
                                   │
                                   └─ SSOAdapter ─┬─ MockSSOAdapter  → mock_sso (IdP simulado)
                                                  └─ OIDCSSOAdapter  → SSO institucional (OAuth2/OIDC)
```

- O front nunca vê senha: o login acontece no IdP, que devolve um *authorization code* de uso único.
- O backend valida o `state` assinado, troca o code pela identidade (via Adapter), exige e-mail `@uem.br`
  e emite um **JWT próprio** (access de 15 min em memória + refresh em cookie `HttpOnly`/`SameSite=Strict`, rotacionado).
- Trocar do Mock para o SSO real = `SSO_ADAPTER=oidc` + variáveis `OIDC_*`. Nenhuma regra de negócio muda.

## Como rodar

```bash
docker compose up -d db                       # PostgreSQL

cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed               # contas de teste, avisos e vagas
.venv/bin/python manage.py runserver 8000

cd ../frontend
npm ci && npm run dev                         # http://localhost:5173
```

Swagger da API: http://localhost:5173/api/docs/ (via proxy do Vite) ou http://localhost:8000/api/docs/.

Contas de teste do Mock (senha `teste123`; entra por e-mail ou RA): `aluno.teste@uem.br` (140001),
`prof.teste@uem.br` (140002), `colab.teste@uem.br` (140003), `admin.teste@uem.br` (140004) e
`visitante@gmail.com` (140005, fora do domínio → acesso negado).

## Produção

O backend é *fail-closed*: servido via WSGI/ASGI sem configuração, ele se recusa a subir. Só o `manage.py`
liga `DEBUG=True` por padrão, e apenas para os comandos locais acima.

- Obrigatórias: `SECRET_KEY` (≥ 50 caracteres aleatórios), `SSO_ADAPTER=oidc` + `OIDC_*`, `ALLOWED_HOSTS`,
  `FRONTEND_URL` (origem do front; usada no redirect do SSO e na checagem de `Origin` do refresh/logout) e `POSTGRES_*`.
- Comandos `manage.py` em produção (`migrate`, `check --deploy`): exporte `DEBUG=False`.
- Rate limit do login é por IP: `NUM_PROXIES` (padrão 1 em produção) = quantos proxies confiáveis anexam o
  `X-Forwarded-For`; errar esse número faz todos dividirem o mesmo contador ou permite forjar o IP.
  Atrás do NAT do campus muitos alunos dividem um IP: ajuste `LOGIN_RATE` (padrão `30/min`) se precisar.
- Os contadores de rate limit ficam na memória de cada processo; com vários workers, configure um cache compartilhado (Redis).
- No servidor/proxy (fora deste repositório): servir `/media/` com `X-Content-Type-Options: nosniff`;
  headers do front (`Content-Security-Policy: frame-ancestors 'none'`, HSTS); limite de corpo ~6 MB; restringir `/admin/`
  (ex.: allowlist de IP), que não tem proteção própria contra força bruta.

## Testes

```bash
cd backend && .venv/bin/python manage.py test   # fluxo SSO completo, permissões, uploads, candidaturas
cd frontend && npm run build                    # type-check + build de produção
```

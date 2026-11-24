# UniPlace — Contrato da API (MVP / Sprint 1)

Fonte da verdade compartilhada entre `backend/` (Django + DRF) e `frontend/` (React PWA).
Base: Etapa 1 (US01, US15, T01.x, T15.x), Etapa 2 (Adapter + Mock SSO) e Trello (Backlog da Sprint).

## Ambiente de desenvolvimento

Na raiz do projeto, suba PostgreSQL, backend e frontend juntos:

```bash
docker compose up --build
```

O backend espera o banco ficar saudável, aplica as migrações e carrega os dados de
teste antes de iniciar. Este Compose é **somente para desenvolvimento**, com
`DEBUG=True` e SSO mock; não é uma configuração de produção.

| Serviço  | URL                    | Observação                                   |
|----------|------------------------|----------------------------------------------|
| Frontend | http://localhost:5173  | Vite; faz proxy de `/api`, `/mock-sso`, `/media` e `/static` para `backend:8000` na rede do Compose |
| Backend  | http://localhost:8000  | Django + DRF; conecta ao PostgreSQL pelo serviço `db:5432` |
| Postgres | localhost:5432         | Serviço `db`, com dados persistidos em volume |

As URLs acima usam as portas padrão publicadas no host. Os nomes `backend` e `db`
são endereços internos dos containers, não URLs para abrir no navegador. Para
alterar portas ou executar backend/frontend fora dos containers, consulte
[Como rodar no README](../README.md#como-rodar).

Como o Vite faz proxy, o navegador enxerga **uma única origem** (`localhost:5173`): cookies e redirects funcionam sem CORS.

**Swagger (OpenAPI 3):** http://localhost:5173/api/docs/ (via proxy do Vite) ou http://localhost:8000/api/docs/ — schema em `/api/schema/`.

## Convenções

- JSON em tudo, exceto upload de anexo (multipart) e o Mock IdP (HTML).
- Autenticação: header `Authorization: Bearer <access>`.
- Erros: `{"detail": "mensagem legível em PT-BR", "code": "codigo_estavel"}` (validação do DRF pode vir como `{campo: [msgs]}`).
- Datas: ISO 8601.
- Listas (todas as rotas GET de coleção) são paginadas por limit/offset:
  `?limit=` (padrão 20, máximo 50) e `?offset=` →
  `{"count": 55, "next": "...?offset=20" | null, "previous": ... | null, "results": [...]}`.
  O front pede `offset = itens já exibidos` ("Carregar mais").
- Limites de taxa → `429 code=throttled`: callback do SSO (30/min por IP, `LOGIN_RATE`);
  criação de avisos e vagas (30/hora por usuário).

## Papéis (`role`)

`aluno` · `professor` · `colaborador` · `admin`

## Objetos

```jsonc
// User
{ "id": 1, "email": "aluno.teste@uem.br", "name": "Ana Aluna", "ra": "140001", "role": "aluno", "course": "Engenharia de Software" }

// Aviso (US02/US03)
{ "id": 1, "titulo": "...", "conteudo": "...",
  "categoria": "aviso" | "prazo" | "alerta" | "evento",
  "prioridade": "alta" | "normal",
  "anexo": "/media/anexos/x.pdf" | null,
  "autor": { "id": 2, "name": "Paulo Professor", "role": "professor" },
  "created_at": "2026-11-19T10:00:00Z" }

// Vaga (US08/US09)
{ "id": 1, "titulo": "...", "descricao": "...",
  "tipo": "estagio" | "bolsa" | "monitoria",
  "curso": "Engenharia de Software" | "",   // vazio = qualquer curso
  "prazo": "2026-12-01",
  "aberta": true,
  "autor": { "id": 3, "name": "...", "role": "colaborador" },
  "ja_candidatou": false,                    // relativo ao usuário logado
  "created_at": "..." }

// Candidatura
{ "id": 1, "vaga": { "id": 1, "titulo": "...", "tipo": "estagio" },
  "aluno": { "id": 1, "name": "...", "email": "...", "ra": "...", "course": "..." },
  "mensagem": "...", "status": "enviada" | "em_analise" | "aprovada" | "recusada",
  "created_at": "..." }
```

## US01 — Autenticação (SSO via Adapter)

Fluxo (diagrama de sequência da Etapa 2):

1. Front `GET /api/auth/sso/start/` → `200 {"authorize_url": "...", "state": "..."}`
   + `Set-Cookie: uniplace_pkce=<code_verifier>; HttpOnly; SameSite=Strict; Path=/api/auth/sso/` (10 min).
   O `authorize_url` leva `code_challenge` (S256) e `code_challenge_method=S256` (PKCE, RFC 7636).
   Front salva `state` em `sessionStorage` e faz `window.location.assign(authorize_url)`.
2. IdP (Mock em `/mock-sso/authorize/` ou SSO real) autentica e redireciona para
   `http://localhost:5173/auth/callback?code=...&state=...`
   (em caso de erro/cancelamento: `?error=access_denied&state=...`).
3. Front confere `state` == `sessionStorage`, então `POST /api/auth/sso/callback/ {"code","state"}`.
4. Backend valida `state` (assinado, TTL 10 min) e a presença do cookie `uniplace_pkce`; o **Adapter** troca
   o code pela identidade enviando o `code_verifier` (um code vazado não serve sem o cookie do navegador que
   iniciou o login), valida vínculo (domínio `@uem.br`), cria/atualiza o `User` e emite JWT próprio.
   - `200 {"access": "<jwt>", "user": User}` + `Set-Cookie: uniplace_refresh=<jwt>; HttpOnly; SameSite=Strict; Path=/api/auth/`
     (o cookie `uniplace_pkce` é apagado)
   - `400 code=invalid_state` (state inválido/expirado ou sem cookie PKCE) `| invalid_code` (inclusive verifier errado)
   - `429 code=throttled` (30/min por IP)
   - `403 code=domain_not_allowed` (ex.: `visitante@gmail.com`)
   - `403 code=user_inactive` (conta desativada por um admin)
   - `415` se o corpo não for JSON (proteção contra login CSRF)
   - `502 code=sso_unavailable` (IdP fora do ar)
5. Sessão: access token (15 min) **só em memória** no front. Ao recarregar a página ou receber 401,
   o front chama `POST /api/auth/refresh/` (cookie enviado automaticamente) → `200 {"access", "user"}`
   com refresh rotacionado; `401` = deslogado.
6. `POST /api/auth/logout/` → `204`, revoga o refresh e limpa o cookie.
7. `GET /api/auth/me/` → `User`.

### Mock IdP (Plano B) — HTML servido pelo Django

- `GET /mock-sso/authorize/?response_type=code&client_id=uniplace&redirect_uri=...&state=...&code_challenge=...&code_challenge_method=S256`
  → tela de login (e-mail **ou RA** + senha), lista contas de teste. PKCE é obrigatório (sem ele: 400).
- `POST /mock-sso/authorize/` (`login`, `password`) → valida credenciais na base própria do mock; sucesso redireciona
  com `code` de uso único (TTL 60 s), que só é trocado com o `code_verifier` correspondente.
- `redirect_uri` precisa estar na allowlist (`SSO_REDIRECT_URIS`).

Contas de teste (senha `teste123`; entra por e-mail ou RA): `aluno.teste@uem.br` (140001), `prof.teste@uem.br` (140002),
`colab.teste@uem.br` (140003), `admin.teste@uem.br` (140004), `visitante@gmail.com` (140005, fora do domínio → 403).

## US02/US03 — Mural de Avisos

| Método | Rota | Quem | Notas |
|---|---|---|---|
| GET | `/api/avisos/?categoria=` | logado | ordem: `prioridade=alta` primeiro, depois mais recentes |
| POST | `/api/avisos/` | professor, colaborador, admin | multipart (`anexo` opcional: pdf/png/jpg, ≤ 5 MB) ou JSON; 403 para aluno |
| DELETE | `/api/avisos/{id}/` | autor ou admin | 204 |

## US08/US09 — Oportunidades (Vagas)

| Método | Rota | Quem | Notas |
|---|---|---|---|
| GET | `/api/vagas/?tipo=` | logado | alunos veem só `aberta=true` com `prazo` não vencido; filtra por `curso` vazio ou igual ao do aluno |
| POST | `/api/vagas/` | colaborador, admin | |
| PATCH | `/api/vagas/{id}/` | autor ou admin | ex.: `{"aberta": false}` |
| POST | `/api/vagas/{id}/candidatar/` | aluno | `{"mensagem"?}` → 201 Candidatura; 409 `code=already_applied`; 400 se fechada/prazo vencido |
| GET | `/api/candidaturas/minhas/` | aluno | |
| GET | `/api/vagas/{id}/candidaturas/` | autor da vaga ou admin | |
| PATCH | `/api/candidaturas/{id}/` | autor da vaga ou admin | `{"status"}` |

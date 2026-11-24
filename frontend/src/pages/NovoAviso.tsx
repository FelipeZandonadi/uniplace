import { useState } from 'react';
import type React from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { PageHeader, Field } from '../components/UI';
import { categories, message } from '../data';

export function NovoAviso() {
  const { canPublish } = useAuth();
  const navigate = useNavigate();
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (!canPublish) return <Navigate to="/" replace />;
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get('anexo') as File;
    setErrors({});
    setError('');
    if (file?.size > 5 * 1024 * 1024) {
      setErrors({ anexo: ['O arquivo deve ter no máximo 5 MB.'] });
      formElement.querySelector<HTMLInputElement>('#anexo')?.focus();
      return;
    }
    if (file?.size && !['application/pdf', 'image/png', 'image/jpeg'].includes(file.type)) {
      setErrors({ anexo: ['Envie um arquivo PDF, PNG ou JPG.'] });
      formElement.querySelector<HTMLInputElement>('#anexo')?.focus();
      return;
    }
    setBusy(true);
    try {
      let body: BodyInit;
      if (file?.size) body = form; else {
        form.delete('anexo');
        body = JSON.stringify(Object.fromEntries(form));
      }
      await api('/api/avisos/', { method: 'POST', body });
      navigate('/');
    } catch (e) {
      if (e instanceof ApiError) setErrors(e.fields);
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return <>
    <Link className="back-link" to="/">← Voltar ao mural</Link>
    <PageHeader
      title="Publicar aviso"
      description="Compartilhe uma informação com a comunidade universitária."
    />
    <form className="form-card" onSubmit={e => void submit(e)}>
      <h2>Informações do aviso</h2>
      <p className="form-intro">Preencha os dados abaixo para publicar no mural.</p>
      {error && <div className="banner error" role="alert">
        {error}
      </div>}
      <Field label="Título" name="titulo" errors={errors}>
        <input
          id="titulo"
          name="titulo"
          required
          aria-invalid={!!errors.titulo}
          aria-describedby={errors.titulo ? 'titulo-error' : undefined}
        />
      </Field>
      <Field label="Conteúdo" name="conteudo" errors={errors}>
        <textarea
          id="conteudo"
          name="conteudo"
          rows={6}
          required
          aria-invalid={!!errors.conteudo}
          aria-describedby={errors.conteudo ? 'conteudo-error' : undefined}
        />
      </Field>
      <div className="form-row">
        <Field label="Categoria" name="categoria" errors={errors}>
          <select id="categoria" name="categoria" defaultValue="aviso"
            aria-invalid={!!errors.categoria} aria-describedby={errors.categoria ? 'categoria-error' : undefined}>
            {Object.entries(categories).map(([v, l]) => <option value={v} key={v}>
              {l.replace(/s$/, '')}
            </option>)}
          </select>
        </Field>
        <Field label="Prioridade" name="prioridade" errors={errors}>
          <select id="prioridade" name="prioridade" defaultValue="normal"
            aria-invalid={!!errors.prioridade} aria-describedby={errors.prioridade ? 'prioridade-error' : undefined}>
            <option value="normal">Normal</option>
            <option value="alta">Alta</option>
          </select>
        </Field>
      </div>
      <Field label="Anexo (opcional)" name="anexo" errors={errors} hint="PDF, PNG ou JPG · até 5 MB">
        <input
          id="anexo"
          name="anexo"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          aria-invalid={!!errors.anexo}
          aria-describedby={errors.anexo ? 'anexo-hint anexo-error' : 'anexo-hint'}
        />
      </Field>
      <div className="form-actions">
        <button className="button primary" disabled={busy}>
          {busy ? 'Publicando...' : 'Publicar aviso'}
        </button>
        <Link className="button secondary" to="/">Cancelar</Link>
      </div>
    </form>
  </>;
}

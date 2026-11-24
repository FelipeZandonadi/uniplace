import { useState } from 'react';
import type React from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { PageHeader, Field } from '../components/UI';
import { types, message } from '../data';

export function NovaVaga() {
  const { canManageJobs } = useAuth();
  const navigate = useNavigate();
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (!canManageJobs) return <Navigate to="/vagas" replace />;
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setErrors({});
    try {
      await api('/api/vagas/', {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))),
      });
      navigate('/vagas');
    } catch (e) {
      if (e instanceof ApiError) setErrors(e.fields);
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return <>
    <Link className="back-link" to="/vagas">← Voltar às vagas</Link>
    <PageHeader
      title="Nova vaga"
      description="Divulgue uma oportunidade para a comunidade universitária."
    />
    <form className="form-card" onSubmit={e => void submit(e)}>
      <h2>Informações da vaga</h2>
      <p className="form-intro">Conte os detalhes para ajudar estudantes a encontrar esta oportunidade.</p>
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
      <Field label="Descrição" name="descricao" errors={errors}>
        <textarea
          id="descricao"
          name="descricao"
          rows={6}
          required
          aria-invalid={!!errors.descricao}
          aria-describedby={errors.descricao ? 'descricao-error' : undefined}
        />
      </Field>
      <div className="form-row">
        <Field label="Tipo" name="tipo" errors={errors}>
          <select id="tipo" name="tipo" aria-invalid={!!errors.tipo}
            aria-describedby={errors.tipo ? 'tipo-error' : undefined}>
            {Object.entries(types).map(([v, l]) => <option key={v} value={v}>
              {l}
            </option>)}
          </select>
        </Field>
        <Field label="Prazo" name="prazo" errors={errors}>
          <input
            id="prazo"
            name="prazo"
            type="date"
            required
            aria-invalid={!!errors.prazo}
            aria-describedby={errors.prazo ? 'prazo-error' : undefined}
          />
        </Field>
      </div>
      <Field
        label="Curso (opcional)"
        name="curso"
        errors={errors}
        hint="Deixe em branco para disponibilizar a todos os cursos."
      >
        <input
          id="curso"
          name="curso"
          aria-invalid={!!errors.curso}
          aria-describedby={errors.curso ? 'curso-hint curso-error' : 'curso-hint'}
        />
      </Field>
      <div className="form-actions">
        <button className="button primary" disabled={busy}>
          {busy ? 'Publicando...' : 'Publicar vaga'}
        </button>
        <Link className="button secondary" to="/vagas">Cancelar</Link>
      </div>
    </form>
  </>;
}

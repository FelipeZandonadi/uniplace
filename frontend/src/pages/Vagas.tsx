import { useRef, useState } from 'react';
import type React from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { Vaga } from '../api';
import { useAuth } from '../auth';
import { Icon } from '../components/Icon';
import { PageHeader, ErrorBox, Empty, Skeletons, Filters, LoadMore } from '../components/UI';
import { types, date, message } from '../data';
import { useList } from '../useList';

export function Vagas() {
  const { user, canManageJobs } = useAuth();
  const [search] = useSearchParams();
  const type = search.get('tipo') || '';
  const { data, setData, total, error, reload, more } = useList<Vaga>(
    `/api/vagas/${type ? `?tipo=${encodeURIComponent(type)}` : ''}`,
  );
  const [applying, setApplying] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<{ id: number; text: string } | null>(null);
  const applyTrigger = useRef<HTMLButtonElement | null>(null);
  const focusReceipt = useRef<number | null>(null);
  async function apply(event: React.FormEvent<HTMLFormElement>, job: Vaga) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    setBusy(true);
    setActionError(null);
    try {
      await api(`/api/vagas/${job.id}/candidatar/`, {
        method: 'POST',
        body: JSON.stringify({ mensagem: new FormData(form).get('mensagem') || '' }),
      });
    } catch (e) {
      if (!(e instanceof ApiError && e.code === 'already_applied')) {
        setActionError({
          id: job.id,
          text: e instanceof ApiError && e.code === 'vaga_fechada'
            ? 'Esta vaga está fechada ou o prazo de candidatura terminou.'
            : message(e),
        });
        return;
      }
    } finally {
      setBusy(false);
    }
    if (form.contains(document.activeElement)) focusReceipt.current = job.id;
    setData(current => current?.map(item => item.id === job.id ? { ...item, ja_candidatou: true } : item) ?? null);
    setApplying(null);
  }
  async function close(job: Vaga) {
    setBusy(true);
    setActionError(null);
    try {
      const updated = await api<Vaga>(`/api/vagas/${job.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ aberta: false }),
      });
      setData(current => current?.map(item => item.id === job.id ? updated : item) ?? null);
    } catch (e) {
      setActionError({ id: job.id, text: message(e) });
    } finally {
      setBusy(false);
    }
  }
  return <>
    <PageHeader
      title="Oportunidades"
      description="Encontre experiências para aprender, participar e crescer na universidade."
      action={canManageJobs && <Link className="button primary" to="/vagas/nova">
        <Icon name="plus" />Nova vaga</Link>}
    />
    <Filters param="tipo" options={{ '': 'Todas', ...types }}
      label="Filtrar vagas por tipo" count={total ?? undefined} item="vaga" />
    {error
      ? <ErrorBox error={error} retry={reload} />
      : !data
        ? <Skeletons />
        : !data.length
          ? <Empty
            title="Nenhuma oportunidade encontrada"
            icon="briefcase"
          >Confira outro filtro ou volte mais tarde para ver novas vagas.</Empty>
          : <div className="card-grid">
      {data.map(job => <article className="card job-card" key={job.id}>
        <div className="job-badges">
          <span className="badge type-badge">
            {types[job.tipo]}
          </span>
          <span className={`status ${job.aberta ? 'open' : 'closed'}`}>
            <span /> {job.aberta ? 'Aberta' : 'Fechada'}
          </span>
        </div>
        <h2>
          {job.titulo}
        </h2>
        <p className="card-copy">
          {job.descricao}
        </p>
        <dl className="job-details">
          <div>
            <dt>Curso</dt>
            <dd>
              {job.curso || 'Todos os cursos'}
            </dd>
          </div>
          <div>
            <dt>Prazo</dt>
            <dd>
              {date(job.prazo)}
            </dd>
          </div>
        </dl>
        {actionError?.id === job.id && <p className="banner error" role="alert">{actionError.text}</p>}
        {user?.role === 'aluno' && (job.ja_candidatou
          ? <Link className="applied" to="/minhas-candidaturas"
            aria-label={`Candidatura enviada para ${job.titulo}. Ver minhas candidaturas`}
            ref={link => {
              if (link && focusReceipt.current === job.id) {
                link.focus();
                focusReceipt.current = null;
              }
            }}>
            <Icon name="check" size={18} /><span>Candidatura enviada</span><Icon name="arrow" size={18} />
          </Link> : job.aberta && <button
            className="button secondary full"
            disabled={busy}
            aria-expanded={applying === job.id}
            aria-controls={applying === job.id ? `candidatura-${job.id}` : undefined}
            onClick={event => {
              applyTrigger.current = event.currentTarget;
              setApplying(applying === job.id ? null : job.id);
              setActionError(null);
            }}
          >Candidatar-se <Icon name="arrow" size={18} />
          </button>)}
        {applying === job.id && <form id={`candidatura-${job.id}`} className="inline-form" onSubmit={e => void apply(e, job)}>
          <label htmlFor={`mensagem-${job.id}`}>Mensagem (opcional)</label>
          <textarea
            id={`mensagem-${job.id}`}
            name="mensagem"
            rows={3}
            maxLength={2000}
            placeholder="Conte um pouco sobre seu interesse."
          />
          <div className="actions">
            <button className="button primary" aria-disabled={busy}>
              {busy ? 'Enviando...' : 'Enviar candidatura'}
            </button>
            <button
              className="button secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                applyTrigger.current?.focus();
                setApplying(null);
                setActionError(null);
              }}
            >Cancelar</button>
          </div>
        </form>}
        {canManageJobs && (user?.role === 'admin' || user?.id === job.autor.id) &&
          <div className="job-actions">
          <Link className="button secondary" to={`/vagas/${job.id}/candidaturas`}>Ver candidaturas</Link>
          {job.aberta && <button
            className="button text-button"
            disabled={busy}
            onClick={() => void close(job)}
          >Encerrar vaga</button>}
        </div>}
      </article>)}
    </div>}
    <LoadMore {...more} />
  </>;
}

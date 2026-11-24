import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
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
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<{ id: number; text: string } | null>(null);
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
        {canManageJobs && (user?.role === 'admin' || user?.id === job.autor.id) &&
          <div className="job-actions">
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

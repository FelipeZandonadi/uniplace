import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { api } from '../api';
import type { Candidatura, StatusCandidatura } from '../api';
import { useAuth } from '../auth';
import { PageHeader, ErrorBox, Empty, Loading, LoadMore } from '../components/UI';
import { statuses, message } from '../data';
import { useList } from '../useList';

export function CandidaturasVaga() {
  const { canManageJobs } = useAuth();
  const { id } = useParams();
  const { data, setData, error, reload, more } = useList<Candidatura>(
    `/api/vagas/${encodeURIComponent(id || '')}/candidaturas/`,
  );
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState<number | null>(null);
  if (!canManageJobs) return <Navigate to="/vagas" replace />;
  async function update(item: Candidatura, status: StatusCandidatura) {
    setSaving(item.id);
    setActionError('');
    try {
      const updated = await api<Candidatura>(`/api/candidaturas/${item.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      setData(current => current?.map(row => row.id === item.id ? updated : row) ?? null);
    } catch (e) {
      setActionError(message(e));
    } finally {
      setSaving(null);
    }
  }
  return <>
    <Link className="back-link" to="/vagas">← Voltar às vagas</Link>
    <PageHeader
      title="Candidaturas"
      description={data?.[0]
        ? `Pessoas candidatas à vaga ${data[0].vaga.titulo}.`
        : 'Acompanhe e atualize o andamento das candidaturas.'}
    />
    {actionError && <div className="banner error" role="alert">
      {actionError}
    </div>}
    {error
      ? <ErrorBox error={error} retry={reload} />
      : !data
        ? <Loading />
        : !data.length
          ? <Empty title="Nenhuma candidatura recebida">As pessoas candidatas aparecerão aqui.</Empty>
          : <div className="applicant-list">
      {data.map(item => <article className="applicant" key={item.id}>
        <div className="applicant-main">
          <div className="avatar large" aria-hidden="true">
            {item.aluno.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h2>
              {item.aluno.name}
            </h2>
            <p>
              {item.aluno.email}
            </p>
          </div>
        </div>
        <dl className="applicant-details">
          <div>
            <dt>RA</dt>
            <dd>
              {item.aluno.ra || 'Não informado'}
            </dd>
          </div>
          <div>
            <dt>Curso</dt>
            <dd>
              {item.aluno.course || 'Não informado'}
            </dd>
          </div>
          <div>
            <dt>Mensagem</dt>
            <dd>
              {item.mensagem || 'Sem mensagem'}
            </dd>
          </div>
        </dl>
        <div className="status-field">
          <label htmlFor={`status-${item.id}`}>Status da candidatura</label>
          <select
            id={`status-${item.id}`}
            value={item.status}
            disabled={saving !== null}
            onChange={e => void update(item, e.target.value as StatusCandidatura)}
          >
            {Object.entries(statuses).map(([v, l]) => <option value={v} key={v}>
              {l}
            </option>)}
          </select>
          {saving === item.id && <small role="status">Salvando...</small>}
        </div>
      </article>)}
    </div>}
    <LoadMore {...more} />
  </>;
}

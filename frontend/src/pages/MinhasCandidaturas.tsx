import { Link, Navigate } from 'react-router-dom';
import type { Candidatura } from '../api';
import { useAuth } from '../auth';
import { PageHeader, ErrorBox, Empty, Skeletons, LoadMore } from '../components/UI';
import { types, statuses, date } from '../data';
import { useList } from '../useList';

export function MinhasCandidaturas() {
  const { user } = useAuth();
  const { data, error, reload, more } = useList<Candidatura>('/api/candidaturas/minhas/');
  if (user?.role !== 'aluno') return <Navigate to="/" replace />;
  return <>
    <PageHeader
      title="Minhas candidaturas"
      description="Veja as oportunidades para as quais você se candidatou."
    />
    {error
      ? <ErrorBox error={error} retry={reload} />
      : !data
        ? <Skeletons />
        : !data.length
          ? <Empty
            title="Você ainda não se candidatou"
            icon="briefcase"
            action={<Link className="button secondary" to="/vagas">Ver vagas</Link>}
          >Explore as oportunidades e encontre uma vaga para você.</Empty>
          : <div className="application-list">
      {data.map(item => <article className="application-row" key={item.id}>
        <div>
          <span className="overline">
            {types[item.vaga.tipo]}
          </span>
          <h2>
            {item.vaga.titulo}
          </h2>
          <p>Enviada em {date(item.created_at)}
          </p>
        </div>
        <span className={`badge application-status ${item.status}`}>
          {statuses[item.status]}
        </span>
      </article>)}
    </div>}
    <LoadMore {...more} />
  </>;
}

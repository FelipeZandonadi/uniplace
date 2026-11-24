import { useSearchParams } from 'react-router-dom';
import type { Aviso, Categoria } from '../api';
import { Icon } from '../components/Icon';
import { PageHeader, ErrorBox, Empty, Skeletons, Filters, LoadMore } from '../components/UI';
import { categories, date } from '../data';
import { useList } from '../useList';

export function Mural() {
  const [search] = useSearchParams();
  const category = search.get('categoria') || '';
  const { data, total, error, reload, more } = useList<Aviso>(
    `/api/avisos/${category ? `?categoria=${encodeURIComponent(category)}` : ''}`,
  );
  const icons: Record<Categoria, string> = {
    aviso: 'bell',
    prazo: 'clock',
    alerta: 'alert',
    evento: 'calendar',
  };
  return <>
    <PageHeader
      title="Mural da Universidade"
      description="Avisos, prazos e acontecimentos importantes para a comunidade."
    />
    <Filters param="categoria" options={{ '': 'Todos', ...categories }}
      label="Filtrar avisos por categoria" count={total ?? undefined} item="aviso" />
    {error
      ? <ErrorBox error={error} retry={reload} />
      : !data
        ? <Skeletons />
        : !data.length
          ? <Empty
            title="Nenhum aviso por aqui"
          >Quando houver novidades nesta categoria, elas aparecerão aqui.</Empty>
          : <div className="card-grid">
      {data.map(notice => <article className="card notice-card" key={notice.id}>
        <div className="card-top">
          <div className={`category-icon ${notice.categoria}`}>
            <Icon name={icons[notice.categoria]} />
          </div>
          <span className={`category-label ${notice.categoria}`}>
            {categories[notice.categoria]?.replace(/s$/, '')}
          </span>
          {notice.prioridade === 'alta' && <span className="badge priority">Prioridade alta</span>}
        </div>
        <div className="notice-content">
          <h2>{notice.titulo}</h2>
          <p className="card-copy">{notice.conteudo}</p>
          {notice.anexo && <a className="attachment" href={notice.anexo} target="_blank" rel="noreferrer">
            <Icon name="file" size={17} /> Ver anexo</a>}
        </div>
        <div className="card-footer">
          <p>Postado por: <strong>
            {notice.autor.name}
          </strong>
            <br />
            <time dateTime={notice.created_at}>
              {date(notice.created_at)}
            </time>
          </p>
        </div>
      </article>)}
    </div>}
    <LoadMore {...more} />
  </>;
}

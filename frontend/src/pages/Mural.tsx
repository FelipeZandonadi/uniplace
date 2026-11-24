import { useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import type { Aviso, Categoria } from '../api';
import { useAuth } from '../auth';
import { Icon } from '../components/Icon';
import { PageHeader, ErrorBox, Empty, Skeletons, Filters, LoadMore } from '../components/UI';
import { categories, date, message } from '../data';
import { useList } from '../useList';

export function Mural() {
  const { user, canPublish } = useAuth();
  const [search] = useSearchParams();
  const category = search.get('categoria') || '';
  const { data, setData, total, setTotal, error, reload, more } = useList<Aviso>(
    `/api/avisos/${category ? `?categoria=${encodeURIComponent(category)}` : ''}`,
  );
  const [confirm, setConfirm] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState('');
  const deleteTrigger = useRef<HTMLButtonElement | null>(null);
  async function remove(id: number) {
    setDeleting(true);
    setActionError('');
    try {
      await api(`/api/avisos/${id}/`, { method: 'DELETE' });
      setData(current => current?.filter(item => item.id !== id) ?? null);
      setTotal(current => current === null ? null : current - 1);
      setConfirm(null);
    } catch (e) {
      setActionError(message(e));
    } finally {
      setDeleting(false);
    }
  }
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
      action={canPublish && <Link className="button primary" to="/mural/novo">
        <Icon name="plus" />Publicar aviso</Link>}
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
          {(user?.role === 'admin' || user?.id === notice.autor.id) && <button
            className="icon-button"
            aria-label={`Excluir aviso ${notice.titulo}`}
            aria-expanded={confirm === notice.id}
            disabled={deleting}
            onClick={event => {
              deleteTrigger.current = event.currentTarget;
              setConfirm(confirm === notice.id ? null : notice.id);
              setActionError('');
            }}
          >
            <Icon name="trash" size={18} />
          </button>}
        </div>
        {confirm === notice.id && <div className="confirm-box">
          <p>Excluir este aviso? Esta ação não pode ser desfeita.</p>
          {actionError && <p className="field-error" role="alert">{actionError}</p>}
          <div className="actions">
            <button className="button danger" disabled={deleting} onClick={() => void remove(notice.id)}>
              {deleting ? 'Excluindo...' : 'Sim, excluir'}
            </button>
            <button className="button secondary" disabled={deleting} onClick={() => {
              deleteTrigger.current?.focus();
              setConfirm(null);
            }}>Cancelar</button>
          </div>
        </div>}
      </article>)}
    </div>}
    <LoadMore {...more} />
  </>;
}

import type { ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Icon } from './Icon';

export function Loading({ text = 'Carregando...' }: { text?: string }) {
  return <div className="loading" role="status">
    <span className="spinner" />
    {text}
  </div>;
}

export function PageHeader({ title, description, action }: {
  title: string;
  description: string;
  action?: ReactNode
}) {
  return <header className="page-header">
    <div>
      <h1>{title}</h1>
      <p className="page-description">{description}</p>
    </div>
    {action}
  </header>;
}

export function ErrorBox({ error, retry }: {
  error: string;
  retry?: () => void
}) {
  return <div className="state-box" role="alert">
    <h2>Não foi possível carregar</h2>
    <p>
      {error}
    </p>
    {retry && <button className="button secondary" onClick={retry}>Tentar novamente</button>}
  </div>;
}

export function Empty({ title, children, icon = 'board', action }: {
  title: string;
  children: ReactNode;
  icon?: string;
  action?: ReactNode;
}) {
  return <div className="state-box">
    <div className="empty-icon">
      <Icon name={icon} size={24} />
    </div>
    <h2>
      {title}
    </h2>
    <p>
      {children}
    </p>
    {action}
  </div>;
}

export function Skeletons() {
  return <div className="card-grid" aria-label="Carregando conteúdo" role="status">
    {[1, 2, 3].map(i => <div className="card skeleton" key={i}>
      <span />
      <span />
      <span />
      <span />
    </div>)}
  </div>;
}

export function LoadMore({ hasMore, loading, error, load }: {
  hasMore: boolean;
  loading: boolean;
  error: string;
  load: () => void
}) {
  if (!hasMore) return null;
  return <div className="load-more">
    {error && <p className="field-error" role="alert">{error}</p>}
    <button className="button secondary" onClick={load} disabled={loading}>
      {loading ? 'Carregando...' : 'Carregar mais'}
    </button>
  </div>;
}

export function Filters({ param, options, label, count, item }: {
  param: string;
  options: Record<string, string>;
  label: string;
  count?: number;
  item: string;
}) {
  const [search, setSearch] = useSearchParams();
  const selected = search.get(param) || '';
  return <div className="list-toolbar">
    <div className="filters" role="group" aria-label={label}>
      {Object.entries(options).map(([value, optionLabel]) => <button
        key={value}
        className={`filter ${selected === value ? 'selected' : ''}`}
        aria-pressed={selected === value}
        onClick={() => {
          if (selected === value) return;
          const next = new URLSearchParams(search);
          if (value) next.set(param, value);
          else next.delete(param);
          setSearch(next);
        }}
      >
        {optionLabel}
      </button>)}
    </div>
    <span className="result-count" role="status">
      {count != null && `${count} ${item}${count === 1 ? '' : 's'}`}
    </span>
  </div>;
}

export function Field({ label, name, errors, children, hint }: {
  label: string;
  name: string;
  errors: Record<string, string[]>;
  children: ReactNode;
  hint?: string
}) {
  return <div className="field">
    <label htmlFor={name}>
      {label}
    </label>
    {children}
    {hint && <small id={`${name}-hint`}>
      {hint}
    </small>}
    {errors[name] && <span className="field-error" id={`${name}-error`}>
      {errors[name].join(' ')}
    </span>}
  </div>;
}

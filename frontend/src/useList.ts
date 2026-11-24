import { useEffect, useRef, useState } from 'react';
import { api } from './api';
import { message } from './data';

type Page<T> = { count: number; next: string | null; results: T[] };

const withOffset = (url: string, offset: number) => `${url}${url.includes('?') ? '&' : '?'}offset=${offset}`;

export function useList<T extends { id: number }>(url: string) {
  const [data, setData] = useState<T[] | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const [total, setTotal] = useState<number | null>(null); // `count` da API, não só o que já carregou
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState('');
  const generation = useRef(0); // descarta "carregar mais" de um filtro/URL antigo
  useEffect(() => {
    const current = ++generation.current;
    setData(null);
    setError('');
    setMoreError('');
    setHasMore(false);
    setTotal(null);
    api<Page<T>>(url).then(page => {
      if (current !== generation.current) return;
      setData(page.results);
      setTotal(page.count);
      setHasMore(!!page.next);
    }).catch(e => {
      if (current === generation.current) setError(message(e));
    });
  }, [url, version]);
  async function loadMore() {
    const current = generation.current;
    setLoadingMore(true);
    setMoreError('');
    try {
      // offset = o que já está na tela: uma exclusão local não faz o próximo lote pular item.
      const page = await api<Page<T>>(withOffset(url, data?.length || 0));
      if (current !== generation.current) return;
      setData(items => {
        const seen = new Set(items?.map(item => item.id)); // itens novos no topo empurram repetidos
        return [...(items || []), ...page.results.filter(item => !seen.has(item.id))];
      });
      setTotal(page.count);
      setHasMore(!!page.next);
    } catch (e) {
      if (current === generation.current) setMoreError(message(e));
    } finally {
      setLoadingMore(false);
    }
  }
  return {
    data, setData, total, setTotal, error, reload: () => setVersion(v => v + 1),
    more: { hasMore, loading: loadingMore, error: moreError, load: () => void loadMore() },
  };
}

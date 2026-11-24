import { Link } from 'react-router-dom';
import { Icon } from '../components/Icon';
import { Logo } from '../components/Layout';

export function NotFound() {
  return <div className="center-screen not-found">
    <Logo />
    <p className="eyebrow">ERRO 404</p>
    <h1>Página não encontrada</h1>
    <p>O endereço pode ter mudado ou não existe.</p>
    <Link className="button primary" to="/">Ir para o mural <Icon name="arrow" />
    </Link>
  </div>;
}

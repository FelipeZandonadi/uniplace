import { useEffect, useRef } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigationType } from 'react-router-dom';
import { useAuth } from '../auth';
import { Icon } from './Icon';

const roles = {
  aluno: 'Aluno',
  professor: 'Professor',
  colaborador: 'Colaborador',
  admin: 'Administrador'
};

export function Logo() {
  return <span className="logo">Uni<span>Place</span>
    <i aria-hidden="true">.</i>
  </span>;
}

export function Layout() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const navigationType = useNavigationType();
  const lastPath = useRef(pathname);
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    if (pathname !== lastPath.current && navigationType !== 'POP') {
      window.scrollTo(0, 0);
      main.current?.focus({ preventScroll: true });
    }
    lastPath.current = pathname;
  }, [pathname, navigationType]);
  return <>
    <a className="skip-link" href="#conteudo-principal">Pular para o conteúdo</a>
    <header className="topbar">
      <div className="topbar-inner">
        <Link to="/" className="brand-link" aria-label="UniPlace, ir ao mural">
          <Logo />
        </Link>
        <nav aria-label="Navegação principal" className="nav">
          <NavLink to="/" end>
            <Icon name="board" size={18} />Mural</NavLink>
        </nav>
        <div className="account">
          <div className="avatar" aria-hidden="true">
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div className="account-info">
            <strong>
              {user?.name}
            </strong>
            <span>
              {user && roles[user.role]}
            </span>
          </div>
          <button className="logout" onClick={() => void logout()}>Sair</button>
        </div>
      </div>
    </header>
    <main id="conteudo-principal" className="container" ref={main} tabIndex={-1}>
      <Outlet />
    </main>
    <footer className="footer">
      <div className="container footer-inner">
        <Logo />
        <span>A sua vida universitária em um só lugar.</span>
        <span>UEM · Construção de Software</span>
      </div>
    </footer>
  </>;
}

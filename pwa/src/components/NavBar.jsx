import { Link, useLocation } from 'react-router-dom';

const LINKS = [
  { to: '/',         label: 'Home'     },
  { to: '/theme',    label: 'Theme'    },
  { to: '/room',     label: 'Room'     },
  { to: '/settings', label: 'Settings' },
];

export function NavBar() {
  const { pathname } = useLocation();
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-zinc-900 border-t border-zinc-800 flex justify-around py-2">
      {LINKS.map(({ to, label }) => (
        <Link key={to} to={to} className={`text-xs py-1 px-3 rounded ${pathname === to ? 'text-purple-400 font-medium' : 'text-zinc-500'}`}>
          {label}
        </Link>
      ))}
    </nav>
  );
}

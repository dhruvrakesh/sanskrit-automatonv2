/**
 * The working corpus's own sections - CORPUS_LIBRARY_C6_2026_10_08: the library (every text on its
 * shelf), the stories drawn from the texts, the names index, and the published texts.
 */
import { Link, useLocation } from 'react-router-dom';
import { BookMarked, Library, Users, BookOpen } from 'lucide-react';

const ITEMS = [
  { to: '/corpus', label: 'Library', icon: Library, match: (p: string) => p === '/corpus' || (/^\/corpus\/[^/]+$/.test(p) && !/^\/corpus\/(stories|names)$/.test(p)) },
  { to: '/corpus/stories', label: 'Stories', icon: BookMarked, match: (p: string) => p.startsWith('/corpus/stories') },
  { to: '/corpus/names', label: 'Names', icon: Users, match: (p: string) => p.startsWith('/corpus/names') },
  { to: '/texts', label: 'Published texts', icon: BookOpen, match: () => false },
];

export default function CorpusNav() {
  const { pathname } = useLocation();
  return (
    <nav aria-label="The working corpus" className="mb-6 flex flex-wrap gap-1 border-b border-border text-sm">
      {ITEMS.map(({ to, label, icon: Icon, match }) => {
        const on = match(pathname);
        return (
          <Link
            key={to}
            to={to}
            aria-current={on ? 'page' : undefined}
            className={`-mb-px inline-flex items-center gap-1.5 border-b-2 px-3 py-2 ${on ? 'border-burgundy text-foreground font-medium' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" /> {label}
          </Link>
        );
      })}
    </nav>
  );
}

/**
 * The working corpus's own sections - CORPUS_LIBRARY_C6_2026_10_08: the library (every text on its
 * shelf), the stories drawn from the texts, the names index, and the published texts.
 * CORPUS_MEDIA_C8_2026_10_09: and the pictures and the graphic novels drawn from them.
 * CORNER_C9_2026_10_09: and the Researchers' Corner, with its anthologies.
 * LEARN_T1_2026_10_09: and Learn, the quests that teach every tool.
 */
import { Link, useLocation } from 'react-router-dom';
import { BookImage, BookMarked, Images, Library, Users, BookOpen, NotebookPen, GraduationCap } from 'lucide-react';

const ITEMS = [
  { to: '/corpus', label: 'Library', icon: Library, match: (p: string) => p === '/corpus' || (/^\/corpus\/[^/]+$/.test(p) && !/^\/corpus\/(stories|names|images|novels|corner|anthologies|learn)$/.test(p)) },
  { to: '/corpus/stories', label: 'Stories', icon: BookMarked, match: (p: string) => p.startsWith('/corpus/stories') },
  { to: '/corpus/names', label: 'Names', icon: Users, match: (p: string) => p.startsWith('/corpus/names') },
  { to: '/corpus/images', label: 'Pictures', icon: Images, match: (p: string) => p.startsWith('/corpus/images') },
  { to: '/corpus/novels', label: 'Graphic novels', icon: BookImage, match: (p: string) => p.startsWith('/corpus/novels') },
  { to: '/corpus/corner', label: 'Corner', icon: NotebookPen, match: (p: string) => p.startsWith('/corpus/corner') || p.startsWith('/corpus/anthologies') },
  { to: '/texts', label: 'Published texts', icon: BookOpen, match: () => false },
  { to: '/corpus/learn', label: 'Learn', icon: GraduationCap, match: (p: string) => p.startsWith('/corpus/learn') },
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

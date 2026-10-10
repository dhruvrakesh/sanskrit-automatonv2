/**
 * The working corpus in the site's navigation - NAV_RBAC_2026_10_10.
 *
 * Shown only to those who may read it (useCorpusAccess): the header's "Corpus" menu on a wide
 * screen, a section of the menu sheet on a phone, and a tab of the phone's bottom bar. Learn (the
 * quests that teach every tool) is in each of them. The same links as the corpus's own tabs
 * (CorpusNav), with a line on what each is for.
 */
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface CorpusLink { label: string; href: string; desc: string }

export const CORPUS_LINKS: readonly CorpusLink[] = [
  { label: 'Library', href: '/corpus', desc: 'Every text on the translation desk: Sanskrit, IAST, English and Hindi' },
  { label: 'Stories', href: '/corpus/stories', desc: 'Episodes retold from the texts, each line cited' },
  { label: 'Names', href: '/corpus/names', desc: 'People, places and things, and where they appear' },
  { label: 'Pictures', href: '/corpus/images', desc: 'Pictures drawn for passages and stories' },
  { label: 'Graphic novels', href: '/corpus/novels', desc: 'Approved stories told again page by page' },
  { label: "Researchers' Corner", href: '/corpus/corner', desc: 'Ask the desk for stories, pictures and novels; make anthologies' },
  { label: 'Learn', href: '/corpus/learn', desc: 'Short quests that teach every tool, with XP, levels and badges' },
  { label: 'Published texts', href: '/texts', desc: 'The texts reviewed and published to everyone' },
];

/** The header's menu (wide screens). */
export function CorpusMenu({ onItemClick }: { onItemClick?: (label: string, href?: string) => void }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1"
          onClick={() => {
            window.dispatchEvent(new CustomEvent('menu_open', { detail: { menu: 'Corpus' } }));
          }}
        >
          Corpus
          <ChevronDown className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[680px] p-4" align="start">
        <div className="mb-3 text-sm text-muted-foreground">
          The working corpus, open to invited researchers and the editors.
        </div>
        <nav aria-label="The working corpus" className="grid grid-cols-2 gap-2">
          {CORPUS_LINKS.map((l) => (
            <Link
              key={l.href}
              to={l.href}
              className={cn(
                'block rounded-lg px-3 py-2 hover:bg-accent hover:text-accent-foreground',
                'focus:bg-accent focus:text-accent-foreground focus:outline-none',
              )}
              onClick={() => onItemClick?.(l.label, l.href)}
            >
              <div className="text-sm font-medium">{l.label}</div>
              <div className="text-xs text-muted-foreground mt-1">{l.desc}</div>
            </Link>
          ))}
        </nav>
      </PopoverContent>
    </Popover>
  );
}

/** The menu sheet's section (phones). */
export function CorpusMobileLinks({ onItemClick }: { onItemClick: () => void }) {
  return (
    <div className="pt-4 border-t border-border">
      <Link
        to="/corpus"
        className="block px-3 py-2 rounded-md hover:bg-accent hover:text-accent-foreground font-medium"
        onClick={onItemClick}
      >
        The working corpus
      </Link>
      <div className="ml-4 mt-1 space-y-1">
        {CORPUS_LINKS.filter((l) => l.href !== '/corpus').map((l) => (
          <Link
            key={l.href}
            to={l.href}
            className="block px-3 py-1 rounded text-sm hover:bg-accent/50 hover:text-accent-foreground"
            onClick={onItemClick}
          >
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

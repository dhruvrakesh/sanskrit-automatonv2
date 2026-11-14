/**
 * "Start here" on the home page - HOME_HEAL_2026_11_14.
 *
 * Asked on 13 and 14 Nov: "have we made local and srangam ui/ux good enough for non technical amateur sanskritists to use
 * this?" and "is homepage rationalised and reflective of our present implementation and stack?". The home page showed
 * the articles, the themes and the tools of 2025, and nothing of the library of Sanskrit texts the articles now rest on:
 * the published texts, the scholarly editions and, for invited readers, the working corpus (the scholarly English read
 * as prose, the dynasties verse by verse, the names, the stories). This section says, in plain words, where to begin,
 * and which doors need an invitation. Static: it calls nothing, so it costs the first visit nothing but its own chunk.
 */
import { Link } from 'react-router-dom';
import { BookOpen, BookText, Crown, GraduationCap, Library, ScrollText, Users } from 'lucide-react';

export type StartDoor = {
  to: string;
  title: string;
  text: string;
  open: boolean;
  icon: typeof BookOpen;
};

export const START_DOORS: StartDoor[] = [
  {
    to: '/texts',
    title: 'Read a text, verse by verse',
    text: 'The Sanskrit as the printed edition has it, its transliteration and an English translation, side by side.',
    open: true,
    icon: BookOpen,
  },
  {
    to: '/editions',
    title: 'Read a scholarly edition',
    text: 'An English made for study, with notes at the end of each chapter and the doubts about the reading.',
    open: true,
    icon: BookText,
  },
  {
    to: '/corpus/scholarly',
    title: 'Read a text as a book',
    text: 'The scholarly English read as prose, chapter by chapter, each verse number a link to its Sanskrit.',
    open: false,
    icon: Library,
  },
  {
    to: '/corpus/genealogies/dynasties',
    title: 'Follow a line of kings',
    text: 'The dynasties as the Puranas trace them, each step with its verse and what the Purana Index says.',
    open: false,
    icon: Crown,
  },
  {
    to: '/corpus/names',
    title: 'Find a person, a place or a god',
    text: 'Every name in the texts, with the verses that speak of it.',
    open: false,
    icon: Users,
  },
  {
    to: '/corpus/stories',
    title: 'Stories from the texts',
    text: 'Episodes retold from the translated verses, each one checked against its citations.',
    open: false,
    icon: ScrollText,
  },
  {
    to: '/corpus/learn',
    title: 'Learn your way around',
    text: 'Short guided steps through every part of the working corpus.',
    open: false,
    icon: GraduationCap,
  },
];

export default function CorpusStartSection() {
  return (
    <section className="py-16 bg-background" aria-labelledby="start-here">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <header className="mb-10 text-center">
          <h2 id="start-here" className="font-serif text-3xl font-bold text-foreground">Start here: the texts themselves</h2>
          <p className="mx-auto mt-4 max-w-3xl text-lg leading-relaxed text-muted-foreground">
            Srangam&apos;s articles rest on a library of Sanskrit texts, read from their printed editions and translated
            verse by verse. Begin with one of these. No Sanskrit is needed to start: every verse has its English beside it.
          </p>
        </header>
        <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3" aria-label="Where to begin">
          {START_DOORS.map(({ to, title, text, open, icon: Icon }) => (
            <li key={to}>
              <Link to={to} className="flex h-full flex-col rounded-xl border border-border bg-card p-6 shadow-sm transition-shadow hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                <span className="mb-3 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span className="font-semibold text-foreground">{title}</span>
                </span>
                <span className="flex-1 text-sm text-muted-foreground">{text}</span>
                <span className={`mt-4 self-start rounded border px-2 py-0.5 text-xs ${open ? 'border-emerald-600/40 text-emerald-800 dark:text-emerald-300' : 'border-amber-500/40 text-amber-800 dark:text-amber-300'}`}>
                  {open ? 'Open to all' : 'For invited readers'}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-8 text-center text-sm text-muted-foreground">
          The pages for invited readers open once you <Link to="/auth" className="text-primary hover:underline">sign in</Link> with
          an invitation. The working corpus is shared with fellow researchers by invitation while it is being edited.
        </p>
      </div>
    </section>
  );
}

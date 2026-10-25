/**
 * The credits of the genealogies - INDEX_SITE_2026_10_25: the three indexes (the Cologne digitizations, CC BY-NC-SA
 * 3.0, with the licence linked), every text whose verses were read, with its edition and its rights as the desk keeps
 * them (GRETIL's, CC BY-NC-SA 4.0; the Mahabharata's e-text for its references and counts only), and the caution.
 */
import { CAUTION, INDEX_CREDIT, LICENCE_URL } from '@/lib/indexSite';

export interface CreditText { code?: string; title: string; edition: string; rights: string }

export default function IndexCredits({ texts }: { texts: CreditText[] }) {
  return (
    <footer className="mt-10 border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground" aria-label="Credits">
      <p>
        {INDEX_CREDIT}{' '}
        <a href={LICENCE_URL} className="text-burgundy hover:underline" rel="license noopener noreferrer" target="_blank">The licence</a>.
      </p>
      {texts.length > 0 && (
        <p className="mt-2">
          The Sanskrit: GRETIL (Göttingen Register of Electronic Texts in Indian Languages):{' '}
          {texts.map((t, i) => (
            <span key={t.code ?? t.title}>
              {i > 0 ? '; ' : ''}<span className="font-medium text-foreground/80">{t.title}</span>
              {t.edition ? `, ${t.edition}` : ''}{t.rights ? ` (${t.rights})` : ''}
            </span>
          ))}.
        </p>
      )}
      <p className="mt-2">{CAUTION}</p>
    </footer>
  );
}

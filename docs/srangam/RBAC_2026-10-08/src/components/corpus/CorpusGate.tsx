/**
 * The working corpus is for signed-in readers - CORPUS_READER_C5_2026_10_08.
 * This only decides what to show while signed out; the database decides who may read
 * (corpus_reader_allowed()), and its refusal is shown by the pages themselves.
 * RBAC_RESEARCHERS_2026_10_08: fellow researchers join by invitation (/invite/<token>), so the
 * refusal says how to get in.
 */
import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Loader2, Lock } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';

export function CorpusRefused({ message }: { message?: string | null }) {
  return (
    <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
      <CardContent className="pt-6 flex items-start gap-3 text-sm">
        <Lock className="w-5 h-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">{message || 'The working corpus is open to signed-in readers only.'}</p>
          <p className="text-muted-foreground mt-1">
            Your account is signed in but is not on the reader list. The working corpus is open to
            invited researchers: if you have an invitation link, open it while signed in with the
            address it was sent to; otherwise ask the editor for one.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function CorpusGate({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const loc = useLocation();
  if (isLoading) {
    return (
      <div className="flex justify-center py-16" aria-busy="true">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
      </div>
    );
  }
  if (!user) {
    const next = encodeURIComponent(loc.pathname + loc.search);
    return (
      <div className="max-w-2xl mx-auto px-4 py-16">
        <Card>
          <CardContent className="pt-6 space-y-3 text-sm">
            <p className="flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
              <Lock className="w-5 h-5 text-burgundy" aria-hidden="true" /> The working corpus
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Every text in the Srangam corpus, as it stands on the translation desk: the Sanskrit,
              the IAST, the English and the Hindi, before review and publication. It is open to
              signed-in readers; fellow researchers join by invitation.
            </p>
            <Link to={`/auth?next=${next}`} className="inline-block font-medium text-burgundy hover:underline">
              Sign in to read it
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }
  return <>{children}</>;
}

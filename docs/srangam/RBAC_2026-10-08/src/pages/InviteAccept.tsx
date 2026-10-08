/**
 * /invite/:token - RBAC_RESEARCHERS_2026_10_08. Where an invited researcher lands.
 *
 * Asks the database what the link is (research_invite_peek: open to anyone, it tells only the
 * status, the expiry and a masked address), then walks the researcher through: sign in or create
 * an account with the invited address, accept (research_invite_accept, which checks the address and
 * that it is confirmed), and on to the working corpus. The page never sees the full invited email.
 */
import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { BookOpen, CheckCircle2, Loader2, LogOut, MailCheck, ShieldAlert, UserPlus } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ACCEPT_TEXT, acceptInvite, formatDate, isInviteToken, peekInvite, type AcceptResult } from '@/lib/rbac';

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-xl px-4 py-12">
      <Helmet>
        <title>Invitation | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
        <meta name="referrer" content="no-referrer" />
      </Helmet>
      {children}
    </div>
  );
}

function Onward() {
  return (
    <div className="flex flex-wrap gap-3 pt-2">
      <Button asChild className="gap-2"><Link to="/corpus"><BookOpen className="h-4 w-4" aria-hidden="true" /> Open the working corpus</Link></Button>
      <Button asChild variant="outline"><Link to="/corpus/stories">Stories</Link></Button>
      <Button asChild variant="outline"><Link to="/corpus/names">Names</Link></Button>
    </div>
  );
}

function Closed({ title, text }: { title: string; text: string }) {
  return (
    <Shell>
      <Card role="alert">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl"><ShieldAlert className="h-5 w-5 text-amber-600" aria-hidden="true" /> {title}</CardTitle>
          <CardDescription>{text}</CardDescription>
        </CardHeader>
      </Card>
    </Shell>
  );
}

export default function InviteAccept() {
  const { token = '' } = useParams();
  const { user, isLoading, roleChecked, isResearcher, refreshRoles, signOut } = useAuth();
  const [result, setResult] = useState<AcceptResult | null>(null);
  const valid = isInviteToken(token);
  const next = encodeURIComponent(`/invite/${token}`);

  const peek = useQuery({
    queryKey: ['invite', token, user?.id ?? 'signed-out'],
    queryFn: () => peekInvite(token),
    enabled: valid && !isLoading,
    staleTime: 0,
    retry: false,
  });
  const accept = useMutation({
    mutationFn: async () => {
      const r = await acceptInvite(token);
      if (!r.ok) throw new Error(r.error ?? 'failed');
      return r.data as AcceptResult;
    },
    onSuccess: async (r) => {
      if (r === 'accepted' || r === 'already_accepted') await refreshRoles();
      setResult(r);
    },
  });

  if (!valid) return <Closed title="This link is not valid" text={ACCEPT_TEXT.invalid} />;
  if (isLoading || peek.isLoading || (user && !roleChecked)) {
    return (
      <Shell>
        <div className="flex justify-center py-16" role="status" aria-label="Checking the invitation">
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
        </div>
      </Shell>
    );
  }
  if (peek.data && !peek.data.ok) {
    return (
      <Closed
        title="The invitation could not be checked"
        text={peek.data.missing ? 'Invitations are not switched on yet. Please try again later.' : 'Please try again shortly.'}
      />
    );
  }
  const info = peek.data?.data;
  if (!info) return <Closed title="The invitation could not be checked" text="Please try again shortly." />;

  if (result === 'accepted' || result === 'already_accepted' || (info.status === 'accepted' && (isResearcher || info.for_you))) {
    return (
      <Shell>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl"><CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" /> You are a Srangam researcher</CardTitle>
            <CardDescription>{result ? ACCEPT_TEXT[result] : ACCEPT_TEXT.already_accepted}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              The working corpus is every text as it stands on the translation desk: the Sanskrit, the IAST, the English and the
              Hindi, before review. Machine translation and OCR are marked as such on every page.
            </p>
            <Onward />
          </CardContent>
        </Card>
      </Shell>
    );
  }
  if (info.status === 'accepted') return <Closed title="Already used" text={ACCEPT_TEXT.used} />;
  if (info.status === 'revoked') return <Closed title="Invitation withdrawn" text={ACCEPT_TEXT.revoked} />;
  if (info.status === 'expired') return <Closed title="Invitation expired" text={ACCEPT_TEXT.expired} />;
  if (info.status !== 'pending') return <Closed title="This link is not valid" text={ACCEPT_TEXT.invalid} />;

  return (
    <Shell>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl"><MailCheck className="h-5 w-5 text-burgundy" aria-hidden="true" /> An invitation to read the working corpus</CardTitle>
          <CardDescription>
            You are invited to the Srangam working corpus as a fellow researcher: the texts with their translations, the stories
            drawn from them and the names index.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <p>
            This invitation is for <strong>{info.email_hint}</strong>
            {info.expires_at && <> and is valid until <strong>{formatDate(info.expires_at)}</strong></>}.
          </p>

          {!user && (
            <>
              <p className="text-muted-foreground">Sign in, or create an account, with that email address. You will come back here to accept.</p>
              <div className="flex flex-wrap gap-3">
                <Button asChild className="gap-2"><Link to={`/auth?next=${next}&tab=signup`}><UserPlus className="h-4 w-4" aria-hidden="true" /> Create an account</Link></Button>
                <Button asChild variant="outline"><Link to={`/auth?next=${next}`}>I have an account: sign in</Link></Button>
              </div>
              <p className="text-xs text-muted-foreground">
                If the site asks you to confirm your email address, open the email it sends, then come back to this link.
              </p>
            </>
          )}

          {user && info.for_you === false && (
            <div className="space-y-3" role="alert">
              <p>
                You are signed in as <strong>{user.email}</strong>, but this invitation is for {info.email_hint}. Sign out, then sign
                in or create an account with the invited address.
              </p>
              <Button type="button" variant="outline" className="gap-2" onClick={() => { signOut().catch(() => undefined); }}>
                <LogOut className="h-4 w-4" aria-hidden="true" /> Sign out
              </Button>
            </div>
          )}

          {user && info.for_you !== false && (
            <div className="space-y-3">
              <p>Signed in as <strong>{user.email}</strong>.</p>
              <Button type="button" onClick={() => accept.mutate()} disabled={accept.isPending} className="gap-2">
                {accept.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
                Accept the invitation
              </Button>
              {result && <p role="alert" className="text-amber-700 dark:text-amber-300">{ACCEPT_TEXT[result]}</p>}
              {accept.isError && <p role="alert" className="text-destructive">The invitation could not be accepted: {(accept.error as Error).message}</p>}
            </div>
          )}
        </CardContent>
      </Card>
    </Shell>
  );
}

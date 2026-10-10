/**
 * /admin/researchers - RBAC_RESEARCHERS_2026_10_08. The super admin's page.
 *
 * Invite fellow researchers to read the working corpus, see who has been invited and who has
 * access, withdraw an invitation or take the researcher role away, choose who may read the
 * corpus, and read the audit log. Every action is a database function (docs/cloud/C7) that checks
 * the caller again; this page only hides itself from admins who are not the super admin.
 *
 * An invitation link is shown ONCE, when it is made: the database keeps only its hash. The super
 * admin copies it or opens it in their own email program (mailto:).
 * CORNER_C10_MAIL_2026_10_09: or sends it from nartiang.org: corner_mail_invite(invite_id, token)
 * queues the email while the token is still known (right after it is made), then the corner-mail
 * function is asked to send it (cornerMail.flushMail). Shown only when the database has the
 * Corner's email (C12); the mailto path stays as it was.
 */
import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  AlertTriangle, Check, Copy, History, Info, Loader2, Mail, Send, ShieldCheck, UserMinus, UserPlus, Users, XCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  AUDIT_TEXT, INVITE_DAYS, MODE_TEXT, ROLE_LABEL, STATUS_TEXT, auditDetail, createInvite, formatDate, formatDateTime,
  getAccessMode, inviteEmail, inviteLink, listAudit, listInvites, listMembers, mailtoHref, removeResearcher,
  revokeInvite, setAccessMode, type AccessMode, type CreatedInvite, type InviteStatus, type MemberRow, type RbacResult,
} from '@/lib/rbac';
import { flushMail, loadMailPrefs, MAIL_PREFS_KEY, mailInvite, mailShown } from '@/lib/cornerMail';

const KEY = ['rbac'] as const;

function unwrap<T>(r: RbacResult<T>): T {
  if (!r.ok) {
    const e = new Error(r.error ?? 'failed') as Error & { missing?: boolean; refused?: boolean };
    e.missing = r.missing; e.refused = r.refused;
    throw e;
  }
  return r.data as T;
}

const isMissing = (e: unknown) => !!(e && (e as { missing?: boolean }).missing);

const STATUS_STYLE: Record<InviteStatus, string> = {
  pending: 'bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200',
  accepted: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200',
  revoked: 'bg-muted text-muted-foreground',
  expired: 'bg-muted text-muted-foreground',
  invalid: 'bg-muted text-muted-foreground',
};

function LoadError({ error, what }: { error: unknown; what: string }) {
  if (!error || isMissing(error)) return null;
  return (
    <p className="flex items-start gap-2 text-sm text-destructive" role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      {what} could not be loaded: {(error as Error)?.message}
    </p>
  );
}

/** CORNER_C10_MAIL_2026_10_09: the invitation's email, sent from nartiang.org by the Corner's mail
 *  (only while the token is known, so only here, right after the invitation is made). */
function SendFromSite({ invite }: { invite: CreatedInvite }) {
  const prefs = useQuery({ queryKey: MAIL_PREFS_KEY, queryFn: loadMailPrefs, staleTime: 60 * 1000 });
  const send = useMutation({
    mutationFn: () => mailInvite(invite.invite_id, invite.token),
    onSuccess: (r) => {
      if (!r.ok) return;
      toast.success(`The invitation for ${invite.email} is on its way`);
      void flushMail();
    },
  });
  if (!mailShown(prefs.data)) return null;
  const on = prefs.data.data.mail_enabled;
  const sent = !!send.data?.ok;
  return (
    <div className="space-y-1.5">
      <Button type="button" variant="outline" className="gap-2" disabled={!on || send.isPending}
              onClick={() => send.mutate()}>
        {send.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
        {sent ? 'Send it again from nartiang.org' : 'Send it from nartiang.org'}
      </Button>
      {!on && (
        <p className="text-sm text-muted-foreground">
          Email from nartiang.org is off. Turn it on in{' '}
          <Link to="/corpus/corner?tab=settings" className="text-primary underline underline-offset-2">the Researchers&apos; Corner, Settings</Link>.
        </p>
      )}
      {sent && <p role="status" className="text-sm text-emerald-800 dark:text-emerald-300">Queued: it is sent from nartiang.org within a minute or two.</p>}
      {send.data && !send.data.ok && <p role="alert" className="text-sm text-destructive">{send.data.error}</p>}
    </div>
  );
}

function NewInvite({ invite, onDone }: { invite: CreatedInvite; onDone: () => void }) {
  const link = inviteLink(window.location.origin, invite.token);
  const mail = inviteEmail(link, invite.email, invite.expires_at, null);
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      toast.success('Link copied');
    } catch {
      toast.error('Copying was refused by the browser: select the link and copy it by hand.');
    }
  };
  return (
    <div className="space-y-3 rounded-md border border-emerald-500/40 bg-emerald-50/60 p-4 dark:bg-emerald-950/20" role="status">
      <p className="text-sm font-medium">
        Invitation for {invite.email}, valid until {formatDate(invite.expires_at)}.
        {invite.reissued && ' The earlier link for this address no longer works.'}
      </p>
      <p className="text-sm text-muted-foreground">
        This link is shown once. Copy it now, or open it in your email program, and send it to the researcher.
      </p>
      <SendFromSite invite={invite} />
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input readOnly value={link} aria-label="Invitation link" className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={copy} className="gap-2">
            {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
            Copy link
          </Button>
          <Button type="button" asChild className="gap-2">
            <a href={mailtoHref(invite.email, mail.subject, mail.body)}>
              <Mail className="h-4 w-4" aria-hidden="true" /> Email it
            </a>
          </Button>
        </div>
      </div>
      <Button type="button" variant="ghost" size="sm" onClick={onDone}>Done</Button>
    </div>
  );
}

export default function Researchers() {
  const { isSuperAdmin, roleChecked, user } = useAuth();
  const qc = useQueryClient();
  const enabled = roleChecked && isSuperAdmin;

  const mode = useQuery({ queryKey: [...KEY, 'mode'], queryFn: async () => unwrap(await getAccessMode()), enabled, staleTime: 0 });
  const invites = useQuery({ queryKey: [...KEY, 'invites'], queryFn: async () => unwrap(await listInvites()), enabled, staleTime: 0 });
  const members = useQuery({ queryKey: [...KEY, 'members'], queryFn: async () => unwrap(await listMembers()), enabled, staleTime: 0 });
  const audit = useQuery({ queryKey: [...KEY, 'audit'], queryFn: async () => unwrap(await listAudit(50)), enabled, staleTime: 0 });
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });

  const [email, setEmail] = useState('');
  const [note, setNote] = useState('');
  const [days, setDays] = useState(14);
  const [made, setMade] = useState<CreatedInvite | null>(null);
  const [pickedMode, setPickedMode] = useState<AccessMode | null>(null);
  const [removing, setRemoving] = useState<MemberRow | null>(null);

  const create = useMutation({
    mutationFn: async () => unwrap(await createInvite(email, note, days)),
    onSuccess: (inv) => { setMade(inv); setEmail(''); setNote(''); refresh(); },
    onError: (e: Error) => toast.error(e.message),
  });
  const revoke = useMutation({
    mutationFn: async (id: string) => unwrap(await revokeInvite(id)),
    onSuccess: (ok) => { toast[ok ? 'success' : 'info'](ok ? 'Invitation withdrawn' : 'It was no longer open'); refresh(); },
    onError: (e: Error) => toast.error(e.message),
  });
  const remove = useMutation({
    mutationFn: async (uid: string) => unwrap(await removeResearcher(uid)),
    onSuccess: (ok) => { toast[ok ? 'success' : 'info'](ok ? 'Researcher role removed' : 'That account was not a researcher'); setRemoving(null); refresh(); },
    onError: (e: Error) => { toast.error(e.message); setRemoving(null); },
  });
  const saveMode = useMutation({
    mutationFn: async (m: AccessMode) => unwrap(await setAccessMode(m)),
    onSuccess: (m) => { toast.success(`Now: ${MODE_TEXT[m].label}`); setPickedMode(null); refresh(); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!roleChecked) {
    return (
      <div className="flex justify-center py-16" role="status" aria-label="Checking access">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
      </div>
    );
  }
  if (!isSuperAdmin) {
    return (
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" aria-hidden="true" /> Super admin only</CardTitle>
          <CardDescription>
            Inviting researchers and choosing who may read the working corpus is for the super admin. Your account is an admin's.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const missing = [mode.error, invites.error, members.error, audit.error].some(isMissing);
  const current = mode.data ?? null;
  const chosen = pickedMode ?? current;
  const researchers = (members.data ?? []).filter((m) => m.roles.includes('researcher')).length;

  return (
    <div className="max-w-5xl space-y-6">
      <Helmet><title>Researchers | Admin | Srangam</title></Helmet>
      <div>
        <h2 className="flex items-center gap-2 text-2xl font-semibold"><Users className="h-6 w-6" aria-hidden="true" /> Researchers</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Invite fellow researchers to read the working corpus (the Shelf, Stories, Names and search), and decide who may read it.
        </p>
      </div>

      {missing && (
        <Card className="border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20" role="alert">
          <CardContent className="flex items-start gap-3 pt-6 text-sm">
            <Info className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
            <p>
              The database does not have the roles functions yet. Run <code>docs/cloud/C7a_rbac_roles_2026-10-08.sql</code> and
              then <code>docs/cloud/C7_rbac_researchers_2026-10-08.sql</code> in the Lovable Cloud SQL editor, then reload this page.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Who may read the working corpus</CardTitle>
          <CardDescription>The database checks this on every request. Admins can always read, except that nobody can while signed out.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode.isLoading ? <Loader2 className="h-5 w-5 animate-spin" aria-label="Loading" /> : (
            <>
              <RadioGroup value={chosen ?? undefined} onValueChange={(v) => setPickedMode(v as AccessMode)} aria-label="Who may read">
                {(Object.keys(MODE_TEXT) as AccessMode[]).map((m) => (
                  <div key={m} className="flex items-start gap-3">
                    <RadioGroupItem value={m} id={`mode-${m}`} className="mt-1" />
                    <Label htmlFor={`mode-${m}`} className="cursor-pointer font-normal">
                      <span className="font-medium">{MODE_TEXT[m].label}</span>
                      {current === m && <Badge variant="secondary" className="ml-2">now</Badge>}
                      <span className="block text-sm text-muted-foreground">{MODE_TEXT[m].help}</span>
                    </Label>
                  </div>
                ))}
              </RadioGroup>
              {pickedMode && pickedMode !== current && (
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="button" onClick={() => saveMode.mutate(pickedMode)} disabled={saveMode.isPending}>
                    {saveMode.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
                    Change to: {MODE_TEXT[pickedMode].label}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setPickedMode(null)}>Cancel</Button>
                  {pickedMode === 'readers' && researchers === 0 && (
                    <p className="text-sm text-amber-700 dark:text-amber-300">No researcher has accepted an invitation yet: only admins will be able to read.</p>
                  )}
                </div>
              )}
              <LoadError error={mode.error} what="The setting" />
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg"><UserPlus className="h-5 w-5" aria-hidden="true" /> Invite a researcher</CardTitle>
          <CardDescription>
            The researcher opens the link, signs in or creates an account with this email address, and accepts. A link works once,
            for that address only. Inviting the same address again makes a new link and voids the old one.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {made ? <NewInvite invite={made} onDone={() => setMade(null)} /> : (
            <form className="grid gap-4 sm:grid-cols-[1fr_auto]" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email address</Label>
                <Input id="invite-email" type="email" required maxLength={254} value={email}
                       onChange={(e) => setEmail(e.target.value)} placeholder="colleague@university.edu" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-days">Valid for</Label>
                <select id="invite-days" value={days} onChange={(e) => setDays(Number(e.target.value))}
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  {INVITE_DAYS.map((d) => <option key={d} value={d}>{d} days</option>)}
                </select>
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="invite-note">Note (only you see it)</Label>
                <Textarea id="invite-note" maxLength={500} rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                          placeholder="Who they are, what they work on" />
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={create.isPending || missing} className="gap-2">
                  {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <UserPlus className="h-4 w-4" aria-hidden="true" />}
                  Create invitation
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Invitations</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadError error={invites.error} what="The invitations" />
          {invites.isLoading ? <Loader2 className="h-5 w-5 animate-spin" aria-label="Loading" /> : (invites.data ?? []).length === 0 ? (
            !invites.error && <p className="text-sm text-muted-foreground">No invitations yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead><TableHead>Status</TableHead><TableHead>Sent</TableHead>
                    <TableHead>Until / accepted</TableHead><TableHead>Note</TableHead><TableHead><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(invites.data ?? []).map((i) => (
                    <TableRow key={i.id}>
                      <TableCell className="font-medium">{i.email}</TableCell>
                      <TableCell><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[i.status]}`}>{STATUS_TEXT[i.status] ?? i.status}</span></TableCell>
                      <TableCell className="whitespace-nowrap text-sm">{formatDate(i.created_at)}</TableCell>
                      <TableCell className="whitespace-nowrap text-sm">
                        {i.accepted_at
                          ? `${formatDate(i.accepted_at)}${i.accepted_by_email && i.accepted_by_email.toLowerCase() !== i.email ? ` (${i.accepted_by_email})` : ''}`
                          : formatDate(i.expires_at)}
                      </TableCell>
                      <TableCell className="max-w-[12rem] truncate text-sm text-muted-foreground" title={i.note ?? ''}>{i.note}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">
                        {i.status === 'pending' && (
                          <Button type="button" variant="ghost" size="sm" className="gap-1" disabled={revoke.isPending}
                                  onClick={() => revoke.mutate(i.id)} aria-label={`Withdraw the invitation for ${i.email}`}>
                            <XCircle className="h-4 w-4" aria-hidden="true" /> Withdraw
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">People with access</CardTitle>
          <CardDescription>Everyone with a role, and anyone on the older reader list (corpus.readers).</CardDescription>
        </CardHeader>
        <CardContent>
          <LoadError error={members.error} what="The people" />
          {members.isLoading ? <Loader2 className="h-5 w-5 animate-spin" aria-label="Loading" /> : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead><TableHead>Roles</TableHead><TableHead>Since</TableHead>
                    <TableHead>Last signed in</TableHead><TableHead>Invited by</TableHead><TableHead><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(members.data ?? []).map((m) => (
                    <TableRow key={m.user_id}>
                      <TableCell className="font-medium">{m.email ?? m.user_id}{m.user_id === user?.id && <span className="ml-1 text-xs text-muted-foreground">(you)</span>}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {m.roles.map((r) => <Badge key={r} variant={r === 'researcher' ? 'secondary' : 'default'} className="whitespace-nowrap">{ROLE_LABEL[r] ?? r}</Badge>)}
                          {m.on_reader_list && <Badge variant="outline" className="whitespace-nowrap">Reader list</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-sm">{formatDate(m.since)}</TableCell>
                      <TableCell className="whitespace-nowrap text-sm">{formatDateTime(m.last_sign_in_at)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{m.invited_by_email}</TableCell>
                      <TableCell className="whitespace-nowrap text-right">
                        {m.roles.includes('researcher') && (
                          <Button type="button" variant="ghost" size="sm" className="gap-1" onClick={() => setRemoving(m)}
                                  aria-label={`Remove the researcher role from ${m.email ?? m.user_id}`}>
                            <UserMinus className="h-4 w-4" aria-hidden="true" /> Remove
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg"><History className="h-5 w-5" aria-hidden="true" /> Audit log</CardTitle>
          <CardDescription>The last 50 changes to invitations, roles and access. Changes made in the SQL editor show no actor.</CardDescription>
        </CardHeader>
        <CardContent>
          <LoadError error={audit.error} what="The audit log" />
          {audit.isLoading ? <Loader2 className="h-5 w-5 animate-spin" aria-label="Loading" /> : (audit.data ?? []).length === 0 ? (
            !audit.error && <p className="text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-border text-sm">
              {(audit.data ?? []).map((a, n) => (
                <li key={`${a.at}-${n}`} className="flex flex-wrap gap-x-3 gap-y-1 py-2">
                  <span className="w-40 shrink-0 text-muted-foreground">{formatDateTime(a.at)}</span>
                  <span className="font-medium">{AUDIT_TEXT[a.action] ?? a.action}</span>
                  {a.target_email && <span>{a.target_email}</span>}
                  {auditDetail(a) && <span className="text-muted-foreground">{auditDetail(a)}</span>}
                  <span className="ml-auto text-xs text-muted-foreground">{a.actor_email ?? 'SQL editor'}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={!!removing} onOpenChange={(o) => { if (!o) setRemoving(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove the researcher role?</AlertDialogTitle>
            <AlertDialogDescription>
              {removing?.email ?? 'This account'} will no longer be able to read the working corpus while it is open to invited
              researchers only. The account itself stays; you can invite them again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep</AlertDialogCancel>
            <AlertDialogAction onClick={() => removing && remove.mutate(removing.user_id)}>Remove</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

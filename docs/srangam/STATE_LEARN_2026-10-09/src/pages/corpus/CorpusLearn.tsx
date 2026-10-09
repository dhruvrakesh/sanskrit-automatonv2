/**
 * /corpus/learn - Learn the working corpus - LEARN_T1_2026_10_09.
 *
 * Short quests that teach invited researchers and editors every tool of the working corpus, in
 * five tracks (find your way, read what the desk made, ask the desk, make and publish, and the
 * editors' own), with XP, levels and a badge for each track finished. A self quest is marked by
 * the person ("I did this", learn_mark); an auto quest is checked live by the database from what
 * they did in the Researchers' Corner and can never be marked by hand. Editors also see the team's
 * progress (learn_team); a researcher sees only their own. There is no public leaderboard.
 *
 * The database decides all of it (src/lib/learn.ts, docs/cloud/C11). Without C11 the page shows
 * the toolbox and how the desk works, and says quietly that progress is not switched on yet.
 */
import { type ReactNode } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Award, CheckCircle2, Circle, GraduationCap, Info, Lock, Users, Wrench } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import CorpusGate, { CorpusRefused } from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import { ActionNote, CornerProblem } from '@/components/corpus/CornerParts';
import { when } from '@/lib/corner';
import {
  DESK_STEPS, doneDate, groupByTrack, isQuestRow, LEARN_KEY, levelProgress, loadQuests, loadSummary, loadTeam,
  markedDone, markQuest, nextQuest, PAID_NOTE, refusedByCorpus, roleLabel, summarize, TOOLBOX,
  type LearnResult, type LearnSummary, type Quest, type QuestRow, type TrackGroup,
} from '@/lib/learn';

const KEY = LEARN_KEY;
const ME_KEY = [...KEY, 'me'] as const;
const LINK = 'font-medium text-burgundy underline decoration-burgundy/40 underline-offset-2 hover:decoration-burgundy';

// ---- parts ----------------------------------------------------------------------------------

/** A progress bar that says what it measures, from min to max. */
function Bar({ label, min = 0, max, now, text }: { label: string; min?: number; max: number; now: number; text: string }) {
  const span = max - min;
  const pct = span > 0 ? Math.min(100, Math.max(0, Math.round((100 * (now - min)) / span))) : 100;
  return (
    <div
      role="progressbar" aria-label={label} aria-valuemin={min} aria-valuemax={max} aria-valuenow={now} aria-valuetext={text}
      className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
    >
      <div className="h-full rounded-full bg-burgundy transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

function SectionHead({ id, icon, children }: { id: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <h2 id={id} className="mb-3 flex items-center gap-2 font-serif text-2xl font-semibold text-foreground">
      {icon}{children}
    </h2>
  );
}

// ---- your progress --------------------------------------------------------------------------

function Progress({ s, groups }: { s: LearnSummary; groups: TrackGroup[] }) {
  const p = levelProgress(s);
  const earned = new Set(s.badges ?? []);
  return (
    <section aria-labelledby="progress-head" className="mb-8 rounded-md border border-border bg-muted/30 p-4 sm:p-5">
      <h2 id="progress-head" className="sr-only">Your progress</h2>
      <dl className="flex flex-wrap gap-x-8 gap-y-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">Level</dt>
          <dd className="font-serif text-2xl font-semibold text-foreground">{s.level}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">XP</dt>
          <dd className="font-serif text-2xl font-semibold text-foreground">{s.xp}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">Quests done</dt>
          <dd className="font-serif text-2xl font-semibold text-foreground">{s.quests_done} of {s.quests_total}</dd>
        </div>
      </dl>
      <div className="mt-4 space-y-1.5">
        <Bar
          label={s.next_level ? `XP towards ${s.next_level}` : 'XP'} min={p.min} max={p.max} now={p.now}
          text={p.toNext != null && s.next_level ? `${s.xp} XP, ${p.toNext} more to ${s.next_level}` : `${s.xp} XP, the top level`}
        />
        <p className="text-sm text-muted-foreground">
          {p.toNext != null && s.next_level
            ? `${p.toNext} XP more to ${s.next_level} (at ${s.next_level_xp} XP).`
            : `${s.level} is the top level.`}
        </p>
      </div>
      <div className="mt-4">
        <h3 className="text-sm font-medium text-foreground">Badges</h3>
        <ul aria-label="Badges" className="mt-2 flex flex-wrap gap-2">
          {groups.map((g) => {
            const on = earned.has(g.key);
            return (
              <li
                key={g.key}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${on ? 'border-burgundy/60 bg-burgundy/10 text-foreground' : 'border-border text-muted-foreground'}`}
              >
                <Award className={`h-4 w-4 ${on ? 'text-burgundy' : ''}`} aria-hidden="true" />
                <span className={on ? 'font-medium' : ''}>{g.badge}</span>
                <span className="text-xs">{on ? 'earned' : `not yet: finish ${g.title}`}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

function Next({ q, groups }: { q: Quest; groups: TrackGroup[] }) {
  const track = groups.find((g) => g.key === q.track);
  return (
    <p className="mb-8 flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm text-foreground">
      <span className="font-medium">Next quest:</span>
      <a href={`#quest-${q.quest}`} className={LINK}>{q.copy.title}</a>
      {track && <span className="text-muted-foreground">({track.title}, {q.xp} XP)</span>}
    </p>
  );
}

// ---- quests ---------------------------------------------------------------------------------

function QuestCard({ q }: { q: Quest }) {
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: () => markQuest(q.quest),
    onSuccess: (r) => {
      if (!r.ok) return;
      qc.setQueryData<LearnResult<QuestRow>>(ME_KEY, (old) => (old?.ok ? { ...old, rows: markedDone(old.rows, q.quest) ?? old.rows } : old));
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
  const self = q.mode === 'self';
  const date = doneDate(q.done_at);
  const title = q.copy.title;
  return (
    <li id={`quest-${q.quest}`} className="scroll-mt-20">
      <Card className={`h-full ${q.done ? 'border-emerald-500/40' : ''}`}>
        <CardContent className="flex h-full flex-col gap-2 pb-4 pt-4">
          <div className="flex items-start gap-2">
            {q.done
              ? <CheckCircle2 className="mt-1 h-5 w-5 shrink-0 text-emerald-600" aria-hidden="true" />
              : <Circle className="mt-1 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />}
            <h3 className="font-serif text-lg leading-snug text-foreground">{title}</h3>
            <span className="ml-auto shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">{q.xp} XP</span>
          </div>
          {q.copy.why && <p className="text-sm text-muted-foreground">{q.copy.why}</p>}
          {q.copy.steps.length > 0 && (
            <ol className="list-decimal space-y-1 pl-5 text-sm text-foreground">
              {q.copy.steps.map((s) => <li key={s}>{s}</li>)}
            </ol>
          )}
          <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-2 pt-2 text-sm">
            <Link to={q.copy.href} aria-label={`Try it: ${title}`} className={LINK}>Try it</Link>
            {q.done && (
              <span className="inline-flex items-center gap-1 text-emerald-800 dark:text-emerald-300">
                Done{date ? ` on ${date}` : ''}{self ? '' : ' (checked for you)'}
              </span>
            )}
            {!q.done && self && (
              <Button
                type="button" size="sm" variant="outline" disabled={m.isPending} onClick={() => m.mutate()}
                aria-label={`I did this: ${title}`} className="border-burgundy/50 text-burgundy hover:border-burgundy"
              >
                {m.isPending ? 'Saving...' : 'I did this'}
              </Button>
            )}
            {!q.done && !self && <span className="text-muted-foreground">Checked for you from the Corner</span>}
          </div>
          {m.data && !m.data.ok && <ActionNote ok={false} text={m.data.error} />}
        </CardContent>
      </Card>
    </li>
  );
}

function Track({ g }: { g: TrackGroup }) {
  const id = `track-${g.key}`;
  return (
    <section aria-labelledby={id} className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id={id} className="font-serif text-xl font-semibold text-foreground">{g.title}</h2>
        <p className="text-sm text-muted-foreground">{g.done} of {g.total} done · {g.xpDone} of {g.xp} XP</p>
      </div>
      <Bar label={`${g.title}: quests done`} max={g.total} now={g.done} text={`${g.done} of ${g.total} quests done`} />
      {g.intro && <p className="max-w-3xl text-sm text-muted-foreground">{g.intro}</p>}
      {g.key === 'ask' && (
        <p className="flex max-w-3xl items-start gap-2 rounded-md border border-amber-500/40 bg-amber-50/50 p-3 text-sm text-foreground dark:bg-amber-950/20">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" /> <span>{PAID_NOTE}</span>
        </p>
      )}
      {g.complete && (
        <p className="inline-flex items-center gap-1.5 text-sm font-medium text-burgundy">
          <Award className="h-4 w-4" aria-hidden="true" /> Badge earned: {g.badge}
        </p>
      )}
      <ol className="grid gap-4 md:grid-cols-2">
        {g.quests.map((q) => <QuestCard key={q.quest} q={q} />)}
      </ol>
    </section>
  );
}

// ---- the toolbox and the desk ---------------------------------------------------------------

function Toolbox() {
  return (
    <section aria-labelledby="toolbox" className="scroll-mt-20">
      <SectionHead id="toolbox" icon={<Wrench className="h-5 w-5 text-burgundy" aria-hidden="true" />}>Your toolbox</SectionHead>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {TOOLBOX.map((t) => (
          <li key={t.name}>
            <Card className="h-full transition-colors hover:border-burgundy/50">
              <CardContent className="space-y-1 pb-4 pt-4 text-sm">
                <Link to={t.href} className="font-serif text-lg text-foreground hover:text-burgundy">{t.name}</Link>
                <p className="text-muted-foreground">{t.what}</p>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </section>
  );
}

function HowTheDeskWorks() {
  return (
    <section aria-labelledby="desk" className="scroll-mt-20">
      <SectionHead id="desk">How the desk works</SectionHead>
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {DESK_STEPS.map((s, i) => (
          <li key={s.title} className="rounded-md border border-border p-4 text-sm">
            <p className="flex items-center gap-2 font-medium text-foreground">
              <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-burgundy text-xs text-white" aria-hidden="true">{i + 1}</span>
              {s.title}
            </p>
            <p className="mt-2 text-muted-foreground">{s.text}</p>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-sm text-muted-foreground">
        Follow what you asked in <Link to="/corpus/corner?tab=mine" className={LINK}>My requests</Link>.
      </p>
    </section>
  );
}

// ---- the team (editors) ---------------------------------------------------------------------

function Team() {
  const q = useQuery({ queryKey: [...KEY, 'team'], queryFn: loadTeam, staleTime: 60 * 1000 });
  const rows = (q.data?.ok ? q.data.rows : []).filter((m) => m && typeof m.user_id === 'string');
  return (
    <section aria-labelledby="team" className="scroll-mt-20">
      <SectionHead id="team" icon={<Users className="h-5 w-5 text-burgundy" aria-hidden="true" />}>Team</SectionHead>
      <p className="mb-3 max-w-3xl text-sm text-muted-foreground">
        Everyone with a role in the working corpus: researchers, admins and the super admin. Only editors see this;
        each researcher sees their own progress alone.
      </p>
      {q.isLoading && <Skeleton className="h-24 w-full" />}
      {q.data && !q.data.ok && <CornerProblem r={q.data} what="The team's progress" />}
      {q.data?.ok && rows.length === 0 && <p className="text-sm text-muted-foreground">No one has a role yet.</p>}
      {rows.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((m) => (
            <li key={m.user_id}>
              <Card className="h-full">
                <CardContent className="space-y-1 pb-4 pt-4 text-sm">
                  <p className="break-all font-medium text-foreground">{m.email || 'No email address'}</p>
                  <p className="text-xs text-muted-foreground">{(m.roles ?? []).map(roleLabel).join(', ') || 'no role'}</p>
                  <p className="text-foreground">{m.level} · {m.xp} XP · {m.quests_done} {m.quests_done === 1 ? 'quest' : 'quests'} done</p>
                  <p className="text-xs text-muted-foreground">Last activity: {when(m.last_activity) || 'none yet'}</p>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ---- the page -------------------------------------------------------------------------------

function NotOpen() {
  return (
    <Card className="mb-8 border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20">
      <CardContent className="flex items-start gap-3 pt-6 text-sm">
        <Lock className="h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div>
          <p className="font-semibold">The quests are for invited researchers and editors.</p>
          <p className="mt-1 text-muted-foreground">
            They follow what you do in the Researchers&apos; Corner, which is for invited researchers and editors. The
            toolbox below is for every reader of the working corpus. To join, ask the editor for an invitation link and
            open it while signed in with the address it was sent to.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function Body() {
  const quests = useQuery({ queryKey: ME_KEY, queryFn: loadQuests, staleTime: 30 * 1000 });
  const r = quests.data;
  const rows = r?.ok ? r.rows.filter(isQuestRow) : [];
  const groups = groupByTrack(rows);
  const editor = rows.some((x) => x.editors_only);
  const sum = useQuery({ queryKey: [...KEY, 'summary'], queryFn: loadSummary, enabled: !!r?.ok, staleTime: 30 * 1000 });
  const s: LearnSummary = (sum.data?.ok && sum.data.rows[0]) || summarize(rows);
  const next = nextQuest(rows);
  const corpusRefused = !!r && !r.ok && refusedByCorpus(r);
  const showTools = !corpusRefused;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      <header className="mb-6">
        <h1 className="flex items-center gap-3 font-serif text-3xl font-semibold text-foreground">
          <GraduationCap className="h-7 w-7 text-burgundy" aria-hidden="true" /> Learn the working corpus
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          Short quests that walk you through every tool of the working corpus, from opening a text to publishing an
          anthology. Each quest earns XP, enough XP takes you up a level, and finishing a track earns its badge. Your
          progress is your own: editors can see how the team is getting on, and there is no public leaderboard.
        </p>
        {showTools && (
          <nav aria-label="On this page" className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {r?.ok && <a href="#quests" className={LINK}>Quests</a>}
            <a href="#toolbox" className={LINK}>Your toolbox</a>
            <a href="#desk" className={LINK}>How the desk works</a>
            {r?.ok && editor && <a href="#team" className={LINK}>Team</a>}
          </nav>
        )}
      </header>

      {quests.isLoading && <div className="mb-8 space-y-3" aria-busy="true"><Skeleton className="h-28 w-full" /><Skeleton className="h-48 w-full" /></div>}
      {corpusRefused && <CorpusRefused message={r?.error} />}
      {r && !r.ok && !corpusRefused && r.refused && <NotOpen />}
      {r && !r.ok && r.missing && (
        <p className="mb-8 flex items-start gap-2 text-sm text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Progress is not switched on here yet. The toolbox and how the desk works are below.
        </p>
      )}
      {r && !r.ok && !r.refused && !r.missing && <div className="mb-8"><CornerProblem r={r} what="Your progress" /></div>}

      {r?.ok && (
        <>
          <Progress s={s} groups={groups} />
          {next && <Next q={next} groups={groups} />}
          {!next && groups.length > 0 && <p className="mb-8 text-sm font-medium text-foreground">Every quest is done.</p>}
          <div id="quests" className="mb-12 scroll-mt-20 space-y-10">
            {groups.map((g) => <Track key={g.key} g={g} />)}
          </div>
        </>
      )}

      {showTools && (
        <div className="space-y-12">
          <Toolbox />
          <HowTheDeskWorks />
          {r?.ok && editor && <Team />}
        </div>
      )}
    </div>
  );
}

export default function CorpusLearn() {
  return (
    <>
      <Helmet>
        <title>Learn | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}

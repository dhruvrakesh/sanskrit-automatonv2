/**
 * /corpus/corner - the Researchers' Corner - CORNER_C9_2026_10_09.
 *
 * Invited researchers and editors ask the translation desk for stories, pictures and graphic
 * novels drawn from the translated texts (?tab=ask), follow what they asked (?tab=mine), and make
 * anthologies of the approved stories (?tab=anthologies). Editors decide researchers' paid
 * requests (?tab=queue); the super admin sets the daily cap (?tab=settings). The database decides
 * all of it (src/lib/corner.ts); this page only shows each person what the database lets them do.
 * A reader who is not invited sees how to get in, and the published anthologies.
 *
 * Deep links prefill a form: ?tab=ask&kind=<kind>&doc=<code>&story_id=&image_id=&novel_id=&from=&to=&at=
 *
 * CORNER_STATE_S1_2026_10_09: the page knows where things are. The strip says when the desk comes
 * next (and, for editors, the mirror, the pictures and the desk's spend); every request shows its
 * stages with their times and, while the desk works on it, its progress (corner_request_track,
 * quietly left out while the database does not have it); the lists are asked again every 20
 * seconds while one of them is open, and a request that is done or failed meanwhile is announced
 * once; a finished request links on to its next steps; editors have a Sync tab (?tab=sync).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, BookImage, BookMarked, CheckCircle2, Clock, Images, Info, NotebookPen, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import CorpusGate from '@/components/corpus/CorpusGate';
import CorpusNav from '@/components/corpus/CorpusNav';
import CorpusImage from '@/components/corpus/CorpusImage';
import {
  ActionNote, CornerClosed, CornerProblem, RequestBadge,
} from '@/components/corpus/CornerParts';
import {
  DeskChips, NextSteps, StageBar, SyncPanel,
} from '@/components/corpus/CornerState';
import { toast } from '@/hooks/use-toast';
import { MediaStatus } from '@/components/corpus/MediaParts';
import { listMirrorDocs, type MirrorDoc } from '@/lib/corpusMirror';
import { bookTitle, isStory, loadStories, parseVerify, type StoryRow } from '@/lib/corpusLibrary';
import { isMedia, isNovel, loadMedia, loadNovels, type MediaRow, type NovelRow } from '@/lib/corpusMedia';
import {
  aboutUsd, AUDIENCE_LABEL, canWithdraw, cancelRequest, cleanRef, CORNER_KEY, createRequest, decideRequest,
  deskIsLate, estimateFor, formatUsd, imageIdOf, lastSeenText, loadCollections, loadKinds, loadMe, num, parsePages,
  requestSummary, resultLinks, setSetting, verifyText, when, type CollectionRow, type CornerKind, type CornerMe,
  type CornerRequest, type CornerResult, type SettingKey,
} from '@/lib/corner';
import {
  finishNotice, listRefresh, loadLiveRequests, meRefresh, newlyFinished, nextRound, nextSteps, parseDeskInfo,
  ROUND_MIN, type FinishNotice, type LiveRequest,
} from '@/lib/cornerState';

type Tab = 'ask' | 'mine' | 'queue' | 'sync' | 'anthologies' | 'settings';

const KIND_TITLES: Record<string, string> = {
  story_range: 'A story from passages you choose', story_write: 'Write a proposed episode',
  story_mine: 'Find episodes in a text', picture_passage: 'A picture for a passage', story_illustrate: 'A picture for a story',
  picture_redraw: 'Draw a picture again', novel_plan: 'Plan a graphic novel from a story',
  novel_cast: "Draw a graphic novel's cast", novel_draw: "Draw a graphic novel's pages",
};

const SELECT = 'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm';
const KEY = CORNER_KEY;

function storyName(s: Pick<StoryRow, 'story_id' | 'title' | 'status'>): string {
  return `${s.title || `Story ${s.story_id}`}${s.status && s.status !== 'approved' ? ` (${s.status})` : ''}`;
}

// ---- the desk's state -----------------------------------------------------------------------

/** The time now, again every half minute, so "next round about 15:48" turns into "a round is due". */
function useNow(ms = 30 * 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}

const capFirst = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

function DeskStrip({ me }: { me: CornerMe }) {
  const now = useNow();
  const late = deskIsLate(me.worker_last_seen, now);
  const info = me.is_editor ? parseDeskInfo(me.worker_info) : null;
  const round = nextRound(me.worker_last_seen, now, info?.sync?.every_min ?? ROUND_MIN);
  return (
    <section aria-label="The desk" className="mb-6 space-y-2 rounded-md border border-border bg-muted/30 px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className={`inline-flex flex-wrap items-center gap-x-1.5 ${late ? 'font-medium text-amber-700 dark:text-amber-300' : 'text-foreground'}`}>
          {late ? <AlertTriangle className="h-4 w-4" aria-hidden="true" /> : <Clock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />}
          Desk last seen: {lastSeenText(me.worker_last_seen, now)}
          {late && <span className="font-normal text-muted-foreground"> (approved requests wait until it is back)</span>}
        </span>
        {round.state !== 'never' && (
          <span className={round.state === 'next' ? 'text-muted-foreground' : 'font-medium text-amber-700 dark:text-amber-300'}>{capFirst(round.text)}</span>
        )}
        <span className="text-muted-foreground">{num(me.queued)} queued · {num(me.running)} being worked on</span>
        {me.is_editor && <span className="text-muted-foreground">{num(me.pending)} waiting for an editor</span>}
        {num(me.mine_open) > 0 && <span className="text-muted-foreground">{num(me.mine_open)} of yours open</span>}
        {me.is_editor && (
          <span className="text-foreground">Today: {formatUsd(me.committed_today)} of {formatUsd(me.daily_cap_usd)} committed</span>
        )}
      </div>
      {info && <DeskChips info={info} now={now} />}
    </section>
  );
}

// ---- asking ---------------------------------------------------------------------------------

interface AskProps {
  kind: string;
  k: CornerKind | undefined;
  doc: string;
  params: Record<string, unknown>;
  ready: boolean;
  estimate: number;
  highlight: boolean;
  help?: string;
  children?: ReactNode;
}

function AskCard({ kind, k, doc, params, ready, estimate, highlight, help, children }: AskProps) {
  const qc = useQueryClient();
  const [note, setNote] = useState('');
  const m = useMutation({
    mutationFn: () => createRequest(kind, doc, params, note),
    onSuccess: (r) => { if (r.ok) void qc.invalidateQueries({ queryKey: KEY }); },
  });
  const title = k?.label || KIND_TITLES[kind] || kind;
  const r = m.data;
  const x = r?.ok ? r.rows[0] : undefined;
  const can = !!doc && ready && !m.isPending;
  return (
    <Card id={`ask-${kind}`} className={`scroll-mt-20 ${highlight ? 'border-burgundy ring-1 ring-burgundy/40' : ''}`}>
      <CardContent className="space-y-3 pb-4 pt-4">
        <h3 className="font-serif text-lg leading-snug text-foreground">{title}</h3>
        {help && <p className="text-xs text-muted-foreground">{help}</p>}
        <form aria-label={title} className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (can) m.mutate(); }}>
          {children}
          <div className="space-y-1.5">
            <Label htmlFor={`${kind}-note`}>Note for the editor (optional)</Label>
            <Textarea id={`${kind}-note`} rows={2} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" size="sm" disabled={!can} className="bg-burgundy text-white hover:bg-burgundy/90">
              {m.isPending ? 'Asking...' : 'Ask the desk'}
            </Button>
            {k?.cost_bearing && estimate > 0 && <span className="text-sm text-muted-foreground">{aboutUsd(estimate)}</span>}
            {!doc && <span className="text-xs text-muted-foreground">Choose a text first.</span>}
          </div>
        </form>
        {r && r.ok && <ActionNote ok text={`${x?.message ?? 'Asked.'}${x?.request_id ? ` (request #${x.request_id})` : ''}`} mineLink />}
        {r && !r.ok && <ActionNote ok={false} text={r.error} />}
      </CardContent>
    </Card>
  );
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function StoryPick({ id, label, stories, value, onChange, empty }: {
  id: string; label: string; stories: StoryRow[]; value: string; onChange: (v: string) => void; empty: string;
}) {
  return (
    <Field id={id} label={label}>
      <select id={id} className={SELECT} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{stories.length ? 'Choose a story' : empty}</option>
        {stories.map((s) => <option key={s.story_id} value={String(s.story_id)}>{storyName(s)}</option>)}
      </select>
    </Field>
  );
}

function NovelPick({ id, novels, value, onChange }: { id: string; novels: NovelRow[]; value: string; onChange: (v: string) => void }) {
  return (
    <Field id={id} label="The graphic novel">
      <select id={id} className={SELECT} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{novels.length ? 'Choose a graphic novel' : 'This text has no graphic novel yet'}</option>
        {novels.map((n) => (
          <option key={n.novel_id} value={String(n.novel_id)}>
            {n.title || `Graphic novel ${n.novel_id}`}{n.status !== 'approved' ? ` (${n.status})` : ''}
          </option>
        ))}
      </select>
    </Field>
  );
}

function AskTab({ me }: { me: CornerMe }) {
  const [search] = useSearchParams();
  const want = search.get('kind');
  const init = (kind: string, key: string) => (want === kind ? (search.get(key) ?? '') : '');
  const [doc, setDoc] = useState(search.get('doc') ?? '');

  const docs = useQuery({ queryKey: ['mirror', 'docs'], queryFn: listMirrorDocs, staleTime: 2 * 60 * 1000 });
  const kinds = useQuery({ queryKey: [...KEY, 'kinds'], queryFn: loadKinds, staleTime: 5 * 60 * 1000 });
  const stories = useQuery({ queryKey: ['mirror', 'stories', 'list', doc], queryFn: () => loadStories(doc, false), enabled: !!doc, staleTime: 2 * 60 * 1000 });
  const novels = useQuery({ queryKey: ['mirror', 'novels', 'doc', doc], queryFn: () => loadNovels(doc), enabled: !!doc, staleTime: 2 * 60 * 1000 });
  const media = useQuery({ queryKey: ['mirror', 'media', 'pick', doc], queryFn: () => loadMedia({ doc, k: 200 }), enabled: !!doc, staleTime: 2 * 60 * 1000 });

  const texts = useMemo(() => (docs.data?.ok ? docs.data.rows : [])
    .filter((d: MirrorDoc) => d && typeof d.doc_code === 'string' && d.english > 0)
    .map((d) => ({ ...d, label: bookTitle(d).title }))
    .sort((a, b) => a.label.localeCompare(b.label)), [docs.data]);
  const text = texts.find((d) => d.doc_code === doc);
  const known = useMemo(() => new Map((kinds.data?.ok ? kinds.data.rows : []).map((k) => [k.kind, k])), [kinds.data]);
  const all = useMemo(() => (stories.data?.ok ? stories.data.rows.filter(isStory) : []), [stories.data]);
  const nov = useMemo(() => (novels.data?.ok ? novels.data.rows.filter(isNovel) : []), [novels.data]);
  const pics = useMemo(() => (media.data?.ok ? media.data.rows.filter(isMedia) : [])
    .filter((p: MediaRow) => imageIdOf(p.media_key) != null), [media.data]);

  const live = (s: StoryRow) => s.status !== 'retired' && s.status !== 'rejected';
  const toWrite = all.filter((s) => s.status === 'candidate' || s.status === 'draft');
  const toIllustrate = all.filter(live);
  const toPlan = all.filter((s) => s.status === 'approved');

  // the forms' fields
  const [rFrom, setRFrom] = useState(init('story_range', 'from'));
  const [rTo, setRTo] = useState(init('story_range', 'to'));
  const [rTitle, setRTitle] = useState('');
  const [rWhy, setRWhy] = useState('');
  const [wStory, setWStory] = useState(init('story_write', 'story_id'));
  const [mMax, setMMax] = useState('6');
  const [pAt, setPAt] = useState(init('picture_passage', 'at'));
  const [pTitle, setPTitle] = useState('');
  const [pBrief, setPBrief] = useState('');
  const [pCaption, setPCaption] = useState('');
  const [iStory, setIStory] = useState(init('story_illustrate', 'story_id'));
  const [dImage, setDImage] = useState(init('picture_redraw', 'image_id'));
  const [nStory, setNStory] = useState(init('novel_plan', 'story_id'));
  const [nPages, setNPages] = useState('12');
  const [nAudience, setNAudience] = useState('general');
  const [cNovel, setCNovel] = useState(init('novel_cast', 'novel_id'));
  const [gNovel, setGNovel] = useState(init('novel_draw', 'novel_id'));
  const [gPages, setGPages] = useState('');

  const chooseDoc = (v: string) => {
    setDoc(v);
    for (const f of [setWStory, setIStory, setDImage, setNStory, setCNovel, setGNovel]) f('');
  };

  useEffect(() => {
    if (!want) return;
    const t = setTimeout(() => document.getElementById(`ask-${want}`)?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }), 50);
    return () => clearTimeout(t);
  }, [want]);

  const usable = (kind: string) => {
    const k = known.get(kind);
    return !k || (k.enabled && (!k.editor_only || me.is_editor));
  };
  const est = (kind: string, params: Record<string, unknown> = {}, extra: { english?: number | null; pages?: number | null } = {}) =>
    estimateFor(known.get(kind), params, extra);
  const card = (kind: string, params: Record<string, unknown>, ready: boolean, children: ReactNode, o: { help?: string; extra?: { english?: number | null; pages?: number | null } } = {}) =>
    usable(kind) ? (
      <AskCard key={kind} kind={kind} k={known.get(kind)} doc={doc} params={params} ready={ready}
        estimate={est(kind, params, o.extra)} highlight={want === kind} help={o.help}>
        {children}
      </AskCard>
    ) : null;

  const range = { from: cleanRef(rFrom) ?? rFrom.trim(), to: cleanRef(rTo) ?? rTo.trim(), title: rTitle.trim(), why: rWhy.trim() };
  const passage = { at: cleanRef(pAt) ?? pAt.trim(), title: pTitle.trim(), brief: pBrief.trim(), caption_en: pCaption.trim() };
  const drawNovel = nov.find((n) => String(n.novel_id) === gNovel);
  const pagesOk = gPages.trim() === '' || parsePages(gPages) != null;

  return (
    <div className="space-y-8">
      <div className="max-w-xl space-y-2">
        {docs.data && !docs.data.ok && <CornerProblem r={{ ...docs.data, missing: false }} what="The list of texts" />}
        <Field id="ask-doc" label="The text" hint={text ? `${text.english} of its ${text.passages} passages are translated into English.` : 'The desk works from the translated passages of one text at a time.'}>
          <select id="ask-doc" className={SELECT} value={doc} onChange={(e) => chooseDoc(e.target.value)} disabled={docs.isLoading}>
            <option value="">{docs.isLoading ? 'Loading the texts...' : 'Choose a text'}</option>
            {texts.map((d) => <option key={d.doc_code} value={d.doc_code}>{d.label}</option>)}
            {doc && !text && docs.data?.ok && <option value={doc}>{doc}</option>}
          </select>
        </Field>
      </div>

      <section aria-labelledby="ask-stories">
        <h2 id="ask-stories" className="mb-3 flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
          <BookMarked className="h-5 w-5 text-burgundy" aria-hidden="true" /> Stories
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {card('story_range', range, !!cleanRef(rFrom) && !!cleanRef(rTo) && range.title.length >= 3 && range.title.length <= 200, (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field id="story_range-from" label="From passage"><Input id="story_range-from" value={rFrom} onChange={(e) => setRFrom(e.target.value)} placeholder="25.2" inputMode="decimal" maxLength={13} /></Field>
                <Field id="story_range-to" label="To passage"><Input id="story_range-to" value={rTo} onChange={(e) => setRTo(e.target.value)} placeholder="25.9" inputMode="decimal" maxLength={13} /></Field>
              </div>
              <Field id="story_range-title" label="A working title"><Input id="story_range-title" value={rTitle} onChange={(e) => setRTitle(e.target.value)} maxLength={200} /></Field>
              <Field id="story_range-why" label="Why this episode (optional)"><Textarea id="story_range-why" rows={2} value={rWhy} onChange={(e) => setRWhy(e.target.value)} maxLength={1000} /></Field>
            </>
          ), { help: 'Passages are named as in the margin of the reader: scan page and passage, such as 25.2. At most 60 passages.' })}
          {card('story_write', { story_id: Number(wStory) }, !!wStory, (
            <StoryPick id="story_write-story" label="The proposed episode" stories={toWrite} value={wStory} onChange={setWStory} empty="No proposed episode in this text" />
          ), { help: 'The desk writes a proposed episode (or a draft again) in English and Hindi from the passages it cites.' })}
          {card('story_mine', { max: Number(mMax) }, Number.isInteger(Number(mMax)) && Number(mMax) >= 1 && Number(mMax) <= 12, (
            <Field id="story_mine-max" label="At most this many episodes (1 to 12)">
              <Input id="story_mine-max" type="number" min={1} max={12} value={mMax} onChange={(e) => setMMax(e.target.value)} className="w-28" />
            </Field>
          ), { help: 'The desk reads the whole text for episodes worth telling and proposes them; the estimate grows with its length.', extra: { english: text?.english ?? 0 } })}
        </div>
      </section>

      <section aria-labelledby="ask-pictures">
        <h2 id="ask-pictures" className="mb-3 flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
          <Images className="h-5 w-5 text-burgundy" aria-hidden="true" /> Pictures
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {card('picture_passage', passage, !!cleanRef(pAt) && passage.title.length >= 3 && passage.brief.length >= 20, (
            <>
              <Field id="picture_passage-at" label="The passage"><Input id="picture_passage-at" value={pAt} onChange={(e) => setPAt(e.target.value)} placeholder="25.7" inputMode="decimal" maxLength={13} /></Field>
              <Field id="picture_passage-title" label="A title"><Input id="picture_passage-title" value={pTitle} onChange={(e) => setPTitle(e.target.value)} maxLength={200} /></Field>
              <Field id="picture_passage-brief" label="What the picture should show" hint="20 to 2000 characters: the scene, the figures, what they hold and wear, as the passage tells it.">
                <Textarea id="picture_passage-brief" rows={3} value={pBrief} onChange={(e) => setPBrief(e.target.value)} maxLength={2000} />
              </Field>
              <Field id="picture_passage-caption" label="A caption (optional)"><Input id="picture_passage-caption" value={pCaption} onChange={(e) => setPCaption(e.target.value)} maxLength={500} /></Field>
            </>
          ))}
          {card('story_illustrate', { story_id: Number(iStory) }, !!iStory, (
            <StoryPick id="story_illustrate-story" label="The story" stories={toIllustrate} value={iStory} onChange={setIStory} empty="No story in this text yet" />
          ), { help: 'A story with a picture already is not drawn again here; ask for that picture to be drawn again instead.' })}
          {card('picture_redraw', { image_id: Number(dImage) }, !!dImage, (
            <Field id="picture_redraw-image" label="The picture">
              <select id="picture_redraw-image" className={SELECT} value={dImage} onChange={(e) => setDImage(e.target.value)}>
                <option value="">{pics.length ? 'Choose a picture' : 'No picture of this text yet'}</option>
                {pics.map((p) => {
                  const id = imageIdOf(p.media_key);
                  return <option key={p.media_key} value={String(id)}>{p.title || p.media_key}{p.status !== 'approved' ? ` (${p.status})` : ''}</option>;
                })}
              </select>
            </Field>
          ))}
        </div>
      </section>

      <section aria-labelledby="ask-novels">
        <h2 id="ask-novels" className="mb-3 flex items-center gap-2 font-serif text-xl font-semibold text-foreground">
          <BookImage className="h-5 w-5 text-burgundy" aria-hidden="true" /> Graphic novels
        </h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {card('novel_plan', { story_id: Number(nStory), pages: Number(nPages), audience: nAudience },
            !!nStory && Number.isInteger(Number(nPages)) && Number(nPages) >= 8 && Number(nPages) <= 16, (
            <>
              <StoryPick id="novel_plan-story" label="The approved story" stories={toPlan} value={nStory} onChange={setNStory} empty="No approved story in this text yet" />
              <div className="grid grid-cols-2 gap-3">
                <Field id="novel_plan-pages" label="Pages (8 to 16)">
                  <Input id="novel_plan-pages" type="number" min={8} max={16} value={nPages} onChange={(e) => setNPages(e.target.value)} />
                </Field>
                <Field id="novel_plan-audience" label="For">
                  <select id="novel_plan-audience" className={SELECT} value={nAudience} onChange={(e) => setNAudience(e.target.value)}>
                    <option value="general">general readers</option>
                    <option value="teen">teenagers</option>
                    <option value="young">young readers</option>
                  </select>
                </Field>
              </div>
            </>
          ), { help: 'The desk plans the pages, their captions and the lines spoken, each citing its passage. The pictures are asked for next.' })}
          {card('novel_cast', { novel_id: Number(cNovel) }, !!cNovel, (
            <NovelPick id="novel_cast-novel" novels={nov} value={cNovel} onChange={setCNovel} />
          ), { help: 'One sheet per figure, so the pages draw each one the same way.' })}
          {card('novel_draw', { novel_id: Number(gNovel), pages: gPages.replace(/\s+/g, '') }, !!gNovel && pagesOk, (
            <>
              <NovelPick id="novel_draw-novel" novels={nov} value={gNovel} onChange={setGNovel} />
              <Field id="novel_draw-pages" label="Pages (optional)" hint="Leave it empty for every page still to be drawn, or name them: 1-12, or 1,3,5-7.">
                <Input id="novel_draw-pages" value={gPages} onChange={(e) => setGPages(e.target.value)} maxLength={60} aria-invalid={!pagesOk} />
              </Field>
            </>
          ), { extra: { pages: drawNovel?.pages ?? null } })}
        </div>
      </section>
    </div>
  );
}

// ---- requests -------------------------------------------------------------------------------

function Preview({ p }: { p: NonNullable<CornerRequest['preview']> }) {
  const v = parseVerify(verifyText(p.verify));
  const text = (p.story_en ?? '').trim();
  return (
    <div className="rounded-md bg-muted/40 p-3 text-sm">
      <p className="flex flex-wrap items-center gap-2">
        <span className="font-serif text-base text-foreground">{p.title || `Story ${p.story_id ?? ''}`}</span>
        <MediaStatus status={p.status} />
      </p>
      {p.title_hi && <p lang="hi" className="font-devanagari text-muted-foreground">{p.title_hi}</p>}
      {text && <p className="mt-1 text-muted-foreground">{text.length > 300 ? `${text.slice(0, 300).trimEnd()}...` : text}</p>}
      <p className="mt-1 flex items-start gap-1.5 text-xs text-muted-foreground">
        {v.ok ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden="true" /> : <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
        <span>
          {v.ok === true && 'Checked against its citations: every citation is in the text.'}
          {v.ok === false && `The check against its citations found problems: ${v.problems.join('; ') || 'see the desk'}.`}
          {v.ok === null && 'Not checked against its citations yet.'}
        </span>
      </p>
    </div>
  );
}

/** The next steps of a done request, once corner_kinds() has said what this viewer may ask for. */
function Next({ r, editor }: { r: CornerRequest; editor: boolean }) {
  const kinds = useQuery({ queryKey: [...KEY, 'kinds'], queryFn: loadKinds, staleTime: 5 * 60 * 1000 });
  if (kinds.isLoading) return null;
  return <NextSteps links={nextSteps(r, { isEditor: editor, kinds: kinds.data?.ok ? kinds.data.rows : null })} />;
}

function RequestCard({ r, editor, children }: { r: LiveRequest; editor: boolean; children?: ReactNode }) {
  const links = resultLinks(r);
  const doc = r.doc_code ? bookTitle({ doc_code: r.doc_code, title: r.doc_title }).title : null;
  return (
    <li>
      <Card>
        <CardContent className="space-y-2 pb-4 pt-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <RequestBadge status={r.status} />
            <span className="font-medium text-foreground">{r.label}</span>
            <span className="font-mono text-xs text-muted-foreground">#{r.id}</span>
          </div>
          <p className="text-foreground">{doc && <span className="text-muted-foreground">{doc} · </span>}{requestSummary(r.kind, r.params)}</p>
          <StageBar r={r} />
          <p className="text-xs text-muted-foreground">
            Asked {when(r.requested_at)}{r.requester ? ` by ${r.requester}` : ''}
            {num(r.est_usd) > 0 && ` · estimate ${aboutUsd(num(r.est_usd))}`}
            {r.cost_usd != null && ` · cost ${formatUsd(r.cost_usd)}`}
            {r.finished_at && ` · finished ${when(r.finished_at)}`}
          </p>
          {r.note && <p className="whitespace-pre-line text-muted-foreground"><span className="font-medium text-foreground">Note:</span> {r.note}</p>}
          {r.decision_note && <p className="whitespace-pre-line text-muted-foreground"><span className="font-medium text-foreground">The editor:</span> {r.decision_note}</p>}
          {r.message && <p className="whitespace-pre-line text-muted-foreground"><span className="font-medium text-foreground">The desk:</span> {r.message}</p>}
          {r.preview && <Preview p={r.preview} />}
          {links.length > 0 && (
            <p className="flex flex-wrap gap-3">
              {links.map((l) => <Link key={l.href} to={l.href} className="font-medium text-burgundy underline decoration-burgundy/40 underline-offset-2 hover:decoration-burgundy">{l.label}</Link>)}
            </p>
          )}
          {r.status === 'done' && <Next r={r} editor={editor} />}
          {children}
        </CardContent>
      </Card>
    </li>
  );
}

function Withdraw({ id }: { id: number }) {
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: () => cancelRequest(id),
    onSuccess: (r) => { if (r.ok) void qc.invalidateQueries({ queryKey: KEY }); },
  });
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button type="button" size="sm" variant="outline" disabled={m.isPending} onClick={() => m.mutate()}>
        {m.isPending ? 'Withdrawing...' : 'Withdraw'}
      </Button>
      {m.data && <ActionNote ok={m.data.ok} text={m.data.ok ? m.data.rows[0]?.message : m.data.error} />}
    </div>
  );
}

/** Tells the page what a list showed, so a request that finishes meanwhile is announced once. */
const WatchRows = createContext<(rows: readonly CornerRequest[]) => void>(() => undefined);

function useWatch(d: CornerResult<LiveRequest> | undefined) {
  const watch = useContext(WatchRows);
  useEffect(() => {
    if (d?.ok) watch(d.rows);
  }, [d, watch]);
}

function MineTab({ me }: { me: CornerMe }) {
  const q = useQuery({
    queryKey: [...KEY, 'requests', 'mine'],
    queryFn: () => loadLiveRequests('mine', { k: 100 }),
    refetchInterval: (query) => listRefresh(query.state.data),
  });
  useWatch(q.data);
  return (
    <div className="space-y-4">
      {q.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div>}
      {q.data && !q.data.ok && <CornerProblem r={q.data} what="Your requests" />}
      {q.data?.ok && q.data.rows.length === 0 && (
        <p className="text-sm text-muted-foreground">You have not asked the desk for anything yet. <Link to="/corpus/corner?tab=ask" className="text-burgundy hover:underline">Ask it now</Link>.</p>
      )}
      {q.data?.ok && q.data.rows.length > 0 && (
        <ol className="space-y-3">
          {q.data.rows.map((r) => (
            <RequestCard key={r.id} r={r} editor={me.is_editor}>{canWithdraw(r.status) && <Withdraw id={r.id} />}</RequestCard>
          ))}
        </ol>
      )}
    </div>
  );
}

function Decide({ r }: { r: CornerRequest }) {
  const qc = useQueryClient();
  const [note, setNote] = useState('');
  const m = useMutation({
    mutationFn: (approve: boolean) => decideRequest(r.id, approve, note),
    onSuccess: (x) => { if (x.ok) void qc.invalidateQueries({ queryKey: KEY }); },
  });
  return (
    <div className="space-y-2 border-t border-border pt-3">
      <div className="space-y-1.5">
        <Label htmlFor={`decide-${r.id}`}>Note to the researcher (optional)</Label>
        <Textarea id={`decide-${r.id}`} rows={2} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" size="sm" disabled={m.isPending} onClick={() => m.mutate(true)} className="bg-burgundy text-white hover:bg-burgundy/90">
          Approve{num(r.est_usd) > 0 ? ` (${aboutUsd(num(r.est_usd))})` : ''}
        </Button>
        <Button type="button" size="sm" variant="outline" disabled={m.isPending} onClick={() => m.mutate(false)}>Reject</Button>
        {m.data && <ActionNote ok={m.data.ok} text={m.data.ok ? m.data.rows[0]?.message : m.data.error} />}
      </div>
    </div>
  );
}

const HISTORY_STATUSES = ['pending', 'approved', 'claimed', 'running', 'done', 'failed', 'rejected', 'cancelled'];

function QueueTab({ me }: { me: CornerMe }) {
  const [status, setStatus] = useState('');
  const queue = useQuery({
    queryKey: [...KEY, 'requests', 'queue'],
    queryFn: () => loadLiveRequests('queue', { k: 100 }),
    refetchInterval: (query) => listRefresh(query.state.data) || 30 * 1000,
  });
  const all = useQuery({
    queryKey: [...KEY, 'requests', 'all', status],
    queryFn: () => loadLiveRequests('all', { status: status || null, k: 50 }),
    refetchInterval: (query) => listRefresh(query.state.data),
  });
  useWatch(queue.data);
  useWatch(all.data);
  return (
    <div className="space-y-8">
      <section aria-labelledby="queue-head" className="space-y-3">
        <h2 id="queue-head" className="font-serif text-xl font-semibold text-foreground">Waiting for an editor</h2>
        {queue.isLoading && <Skeleton className="h-24 w-full" />}
        {queue.data && !queue.data.ok && <CornerProblem r={queue.data} what="The queue" />}
        {queue.data?.ok && queue.data.rows.length === 0 && <p className="text-sm text-muted-foreground">Nothing is waiting for a decision.</p>}
        {queue.data?.ok && queue.data.rows.length > 0 && (
          <ol className="space-y-3">{queue.data.rows.map((r) => <RequestCard key={r.id} r={r} editor={me.is_editor}><Decide r={r} /></RequestCard>)}</ol>
        )}
      </section>
      <section aria-labelledby="history-head" className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="history-head" className="font-serif text-xl font-semibold text-foreground">Recent requests</h2>
          <div className="w-56 space-y-1.5">
            <Label htmlFor="history-status">Show</Label>
            <select id="history-status" className={SELECT} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">every status</option>
              {HISTORY_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        {all.isLoading && <Skeleton className="h-24 w-full" />}
        {all.data && !all.data.ok && <CornerProblem r={all.data} what="The requests" />}
        {all.data?.ok && all.data.rows.length === 0 && <p className="text-sm text-muted-foreground">No request{status ? ` is ${status}` : ' yet'}.</p>}
        {all.data?.ok && all.data.rows.length > 0 && <ol className="space-y-3">{all.data.rows.map((r) => <RequestCard key={r.id} r={r} editor={me.is_editor} />)}</ol>}
      </section>
    </div>
  );
}

// ---- anthologies ----------------------------------------------------------------------------

function CollectionCards({ scope, canMake }: { scope: 'all' | 'published'; canMake: boolean }) {
  const q = useQuery({ queryKey: [...KEY, 'collections', scope], queryFn: () => loadCollections(scope), staleTime: 60 * 1000 });
  const rows = (q.data?.ok ? q.data.rows : []).filter((c: CollectionRow) => c && typeof c.id === 'number');
  return (
    <div className="space-y-4">
      {canMake && (
        <Link to="/corpus/anthologies/new" className="inline-flex items-center gap-1.5 rounded-md border border-burgundy/50 px-3 py-1.5 text-sm text-burgundy hover:border-burgundy">
          <Plus className="h-4 w-4" aria-hidden="true" /> New anthology
        </Link>
      )}
      {q.isLoading && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true"><Skeleton className="h-56 w-full" /><Skeleton className="h-56 w-full" /></div>}
      {q.data && !q.data.ok && <CornerProblem r={q.data} what="The anthologies" />}
      {q.data?.ok && rows.length === 0 && (
        <p className="text-sm text-muted-foreground">
          {scope === 'published' ? 'No anthology has been published yet.' : 'No anthology yet. An anthology gathers approved stories from any of the texts, in the order you choose, with an introduction.'}
        </p>
      )}
      {rows.length > 0 && (
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((c) => (
            <li key={c.id}>
              <Card className="h-full overflow-hidden transition-colors hover:border-burgundy/50">
                <Link to={`/corpus/anthologies/${c.id}`} aria-label={`Open ${c.title}`}>
                  <CorpusImage sha={c.cover_sha} available={!!c.cover_has_thumb} ratio="4 / 3" alt={`The first picture of ${c.title}`} className="rounded-none" />
                </Link>
                <CardContent className="space-y-1 pb-4 pt-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{num(c.items)} {num(c.items) === 1 ? 'story' : 'stories'}</span>
                    {AUDIENCE_LABEL[c.audience] && <span>{AUDIENCE_LABEL[c.audience]}</span>}
                    {c.status !== 'published' && <MediaStatus status={c.status} />}
                  </div>
                  <Link to={`/corpus/anthologies/${c.id}`} className="block font-serif text-lg leading-snug text-foreground hover:text-burgundy">{c.title}</Link>
                  {c.title_hi && <p lang="hi" className="font-devanagari text-sm text-muted-foreground">{c.title_hi}</p>}
                  {c.owner && <p className="text-xs text-muted-foreground">by {c.owner}</p>}
                </CardContent>
              </Card>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// ---- settings -------------------------------------------------------------------------------

function SettingRow({ k, label, hint, value, children }: { k: SettingKey; label: string; hint: string; value: () => string | null; children: ReactNode }) {
  const qc = useQueryClient();
  const [bad, setBad] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: (v: string) => setSetting(k, v),
    onSuccess: (r) => { if (r.ok) void qc.invalidateQueries({ queryKey: KEY }); },
  });
  const save = () => {
    const v = value();
    if (v == null) { setBad(hint); return; }
    setBad(null);
    m.mutate(v);
  };
  return (
    <div className="space-y-2 border-b border-border pb-4 last:border-0">
      <p className="font-medium text-foreground">{label}</p>
      <div className="flex flex-wrap items-end gap-3">
        {children}
        <Button type="button" size="sm" variant="outline" disabled={m.isPending} onClick={save}>{m.isPending ? 'Saving...' : 'Save'}</Button>
      </div>
      <p className="text-xs text-muted-foreground">{hint}</p>
      {bad && <ActionNote ok={false} text={bad} />}
      {m.data && <ActionNote ok={m.data.ok} text={m.data.ok ? `Saved: ${m.data.rows[0] ?? ''}` : m.data.error} />}
    </div>
  );
}

function SettingsTab({ me }: { me: CornerMe }) {
  const [cap, setCap] = useState(num(me.daily_cap_usd).toFixed(2));
  const [need, setNeed] = useState(!!me.researchers_need_approval);
  const [maxp, setMaxp] = useState('20');
  return (
    <Card className="max-w-2xl">
      <CardContent className="space-y-4 pt-6 text-sm">
        <SettingRow k="daily_cap_usd" label="The daily cap" hint="In US dollars, 0 to 50, India time. Approved requests may commit no more than this in a day."
          value={() => { const n = Number(cap); return cap.trim() !== '' && Number.isFinite(n) && n >= 0 && n <= 50 ? n.toFixed(2) : null; }}>
          <div className="space-y-1.5">
            <Label htmlFor="setting-cap">Dollars a day</Label>
            <Input id="setting-cap" type="number" min={0} max={50} step={0.01} value={cap} onChange={(e) => setCap(e.target.value)} className="w-32" />
          </div>
        </SettingRow>
        <SettingRow k="researchers_need_approval" label="Researchers' paid requests" hint="When on, a researcher's paid request waits for an editor; when off, it is approved at once within the cap."
          value={() => (need ? 'true' : 'false')}>
          <label htmlFor="setting-need" className="flex items-center gap-2 text-sm font-medium">
            <input id="setting-need" type="checkbox" aria-label="Researchers' paid requests wait for an editor" checked={need} onChange={(e) => setNeed(e.target.checked)} className="h-4 w-4 accent-[hsl(var(--burgundy))]" />
            wait for an editor
          </label>
        </SettingRow>
        <SettingRow k="max_pending_per_person" label="Requests waiting per researcher" hint="1 to 200: how many of one researcher's requests may wait for an editor at once."
          value={() => (/^\d{1,3}$/.test(maxp.trim()) && Number(maxp) >= 1 && Number(maxp) <= 200 ? String(Number(maxp)) : null)}>
          <div className="space-y-1.5">
            <Label htmlFor="setting-max">At most</Label>
            <Input id="setting-max" type="number" min={1} max={200} value={maxp} onChange={(e) => setMaxp(e.target.value)} className="w-28" />
          </div>
        </SettingRow>
      </CardContent>
    </Card>
  );
}

// ---- sync (editors) -------------------------------------------------------------------------

function SyncTab({ me }: { me: CornerMe }) {
  const now = useNow();
  return <SyncPanel me={me} info={parseDeskInfo(me.worker_info)} now={now} />;
}

// ---- the page -------------------------------------------------------------------------------

/** Announces, once each, the requests that finish while the page is open: a polite live line
 *  on the page and a toast. */
function useFinishWatch() {
  const qc = useQueryClient();
  const seen = useRef(new Map<number, string>());
  const told = useRef(new Set<number>());
  const [notes, setNotes] = useState<FinishNotice[]>([]);
  const watch = useCallback((rows: readonly CornerRequest[]) => {
    const fresh = newlyFinished(seen.current, rows).filter((r) => !told.current.has(r.id));
    for (const r of rows) if (r && typeof r.id === 'number') seen.current.set(r.id, r.status);
    if (!fresh.length) return;
    const said = fresh.map((r) => {
      told.current.add(r.id);
      return finishNotice(r);
    });
    setNotes((prev) => [...prev, ...said].slice(-3));
    for (const n of said) toast({ title: n.title, description: n.detail ?? undefined, variant: n.ok ? 'default' : 'destructive' });
    void qc.invalidateQueries({ queryKey: [...KEY, 'me'] });
  }, [qc]);
  return { watch, notes };
}

function Corner({ me }: { me: CornerMe }) {
  const [search, setSearch] = useSearchParams();
  const { watch, notes } = useFinishWatch();
  const allowed: Tab[] = [
    'ask', 'mine', ...(me.is_editor ? ['queue' as Tab, 'sync' as Tab] : []), 'anthologies', ...(me.is_super_admin ? ['settings' as Tab] : []),
  ];
  const asked = search.get('tab') as Tab | null;
  const tab: Tab = asked && allowed.includes(asked) ? asked : 'ask';
  const go = (t: string) => {
    const next = new URLSearchParams();
    next.set('tab', t);
    setSearch(next, { replace: true });
  };
  return (
    <WatchRows.Provider value={watch}>
      <div aria-live="polite" className={notes.length ? 'mb-4 space-y-1' : undefined}>
        {notes.map((n) => (
          <p key={n.id} className={`flex items-start gap-1.5 text-sm ${n.ok ? 'text-emerald-800 dark:text-emerald-300' : 'text-red-700 dark:text-red-300'}`}>
            {n.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
            <span>{n.line}</span>
          </p>
        ))}
      </div>
      <Tabs value={tab} onValueChange={go}>
        <TabsList className="mb-4 h-auto flex-wrap justify-start">
          <TabsTrigger value="ask">Ask the desk</TabsTrigger>
          <TabsTrigger value="mine">My requests{num(me.mine_open) > 0 ? ` (${num(me.mine_open)})` : ''}</TabsTrigger>
          {me.is_editor && <TabsTrigger value="queue">Queue{num(me.pending) > 0 ? ` (${num(me.pending)})` : ''}</TabsTrigger>}
          {me.is_editor && <TabsTrigger value="sync">Sync</TabsTrigger>}
          <TabsTrigger value="anthologies">Anthologies</TabsTrigger>
          {me.is_super_admin && <TabsTrigger value="settings">Settings</TabsTrigger>}
        </TabsList>
        <TabsContent value="ask"><AskTab me={me} /></TabsContent>
        <TabsContent value="mine"><MineTab me={me} /></TabsContent>
        {me.is_editor && <TabsContent value="queue"><QueueTab me={me} /></TabsContent>}
        {me.is_editor && <TabsContent value="sync"><SyncTab me={me} /></TabsContent>}
        <TabsContent value="anthologies"><CollectionCards scope="all" canMake /></TabsContent>
        {me.is_super_admin && <TabsContent value="settings"><SettingsTab me={me} /></TabsContent>}
      </Tabs>
    </WatchRows.Provider>
  );
}

function Body() {
  const me = useQuery({ queryKey: [...KEY, 'me'], queryFn: loadMe, staleTime: 60 * 1000, refetchInterval: (query) => meRefresh(query.state.data) });
  const row = me.data?.ok ? me.data.rows[0] : undefined;
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <CorpusNav />
      <header className="mb-6">
        <h1 className="flex items-center gap-3 font-serif text-3xl font-semibold text-foreground">
          <NotebookPen className="h-7 w-7 text-burgundy" aria-hidden="true" /> The Researchers&apos; Corner
        </h1>
        <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
          Ask the translation desk for stories, pictures and graphic novels drawn from the translated texts. Every
          result is checked against its citations and comes back as a draft until an editor approves it. Paid
          requests from researchers wait for an editor first. The desk takes approved requests on its rounds, every
          ten minutes or so while the desk PC is on.
        </p>
      </header>

      {me.isLoading && <div className="space-y-3" aria-busy="true"><Skeleton className="h-12 w-full" /><Skeleton className="h-48 w-full" /></div>}
      {me.data && !me.data.ok && <CornerProblem r={me.data} what="The Researchers' Corner" />}
      {me.data?.ok && row?.can_request && <DeskStrip me={row} />}
      {me.data?.ok && row?.can_request && <Corner me={row} />}
      {me.data?.ok && !row?.can_request && (
        <div className="space-y-6">
          <CornerClosed />
          <section aria-labelledby="published-head">
            <h2 id="published-head" className="mb-3 font-serif text-xl font-semibold text-foreground">Published anthologies</h2>
            <CollectionCards scope="published" canMake={false} />
          </section>
        </div>
      )}
    </div>
  );
}

export default function CorpusCorner() {
  return (
    <>
      <Helmet>
        <title>Researchers&apos; Corner | Working Corpus | Srangam</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <CorpusGate>
        <Body />
      </CorpusGate>
    </>
  );
}

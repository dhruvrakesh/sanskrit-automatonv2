# Pictures and graphic novels in the working corpus (2026-10-09)

Marker: CORPUS_MEDIA_C8_2026_10_09. This brings the translation desk's image library and graphic novels to the site, for the working corpus's readers. Until now they were only on the desk (the dashboard's Images and Novels pages, and the PDF and HTML exports).

## Pages

| Page | What a reader gets | From the desk's |
|---|---|---|
| `/corpus/images` (Pictures) | **The gallery.** Every approved picture, by text, each linked to the passage it illustrates (`?at=69.1`). **One picture.** `?pic=img:103` opens it at full size, with its caption in English and Hindi, its story, and the label "Illustration - generated, not a historical source." Arrow keys go to the next and previous. **Editors.** Admins also see drafts, marked as such. | `images.py` (doc_images) |
| `/corpus/novels` (Graphic novels) | Every approved graphic novel, with its first page as the cover, its text and the story it retells. Editors also see novels being planned or drawn. | `novel.py` (doc_novels) |
| `/corpus/novels/:id` | **The cast.** The cast sheets, with each figure's description. **The pages.** Each page's picture beside its caption, in English, Hindi or both. Every bracketed citation is a link into the text, and every spoken line carries its verse. "The scene the artist was asked for" is folded under each page. **The end.** The passages it retells and the check against its citations. | the plan, the check, the page and cast pictures |
| `/corpus/stories/:doc/:id` | The story's picture now heads the page, and "Read it as a graphic novel" appears when there is one. With no picture, the page reads exactly as before. | `doc_stories.image_id` |

## Where the pictures are kept, and why

- **Storage.** The pictures are kept in the Srangam Shared Drive, in the folder "Srangam corpus media". They are **not shared by link**: only the project's service account and the Shared Drive's own members can open them.
  - The service account is the one `generate-article-og`, `tts-save-drive` and `context-save-drive` already use (`GOOGLE_SERVICE_ACCOUNT_JSON`, `_shared/google-drive.ts`).
  - Drive is used to keep costs low: it sits within the Workspace storage we already have, and needs no new bucket, plan or key.
- **Two sizes of each picture.** The desk makes them:
  - `thumb`: 480 px on the long side, about 30 KB;
  - `display`: 1600 px, about 250 KB.
  - The originals stay on the desk.
  - 57 pictures make 114 files and about 14 MB.
- **The trade-off we accepted.** Drive is not a CDN.
  - The first view of a picture passes through the edge function and Drive, and takes a moment.
  - After that the browser keeps it. A picture is named by its sha256 and never changes, so it opens at once next time.
  - `corpus.media_files.storage` names the store (`'gdrive'`). Moving to a bucket later is a change to the edge function and one column, not to the pages.

## How a picture reaches a reader

1. **The desk.** `scripts/corpus_media.py` in the automaton repo runs after the mirror, every 2 hours, in the same scheduled task.
   - It asks `corpus-media` (signed with `CORPUS_SYNC_SECRET`, as `corpus-ingest` is) what the site has.
   - It uploads the renditions the site lacks. The function puts each in Drive, private, once per sha256 and size.
   - Only then does it send the rows: captions, anchor, status, model, the generation prompt, and the novels' plans and checks.
   - A row whose pictures are not all on Drive is held back, so the site never lists a picture it cannot show.
   - A picture retired on the desk is retired on the site, never deleted.
2. **The database decides who sees what** (C8, in the automaton repo: `docs/cloud/C8_corpus_media_2026-10-09.sql`).
   - Readers pass the corpus gate first (C5/C7).
   - They see approved pictures, and approved novels with every page of them.
   - Admins and the super admin also see drafts and novels still being drawn.
   - Retired is never shown.
3. **The page asks for a picture** (`src/lib/corpusMedia.ts`): `GET /functions/v1/corpus-media?sha=<64 hex>&r=thumb|display`.
   - The request carries the reader's own token in the `Authorization` header, never in the URL.
   - The function asks the database **as that reader** (`corpus_reader_media_file`). If the answer is no, it returns 403 or 404 before Drive is touched.
   - If the answer is yes, it streams the bytes from Drive with the service account.
   - `Cache-Control: private, max-age=2592000, immutable`, with an ETag. A repeat gets 304.
4. **The browser keeps it.**
   - **In this tab:** as an object URL.
   - **Across visits:** in Cache Storage (`srangam-corpus-media-v1`), under the user's id.
   - **Fetching:** at most 6 at once. A picture is fetched only when it comes near the screen. Each holds its place at its own proportions, so nothing jumps.

## Code

- `src/lib/corpusMedia.ts`:
  - the loaders `loadMedia`, `loadNovels` and `loadNovel` (`missing` when C8 is not applied);
  - the pure rules `parsePlan`, `parseNovelVerify`, `citeParts`, `novelPictures`, `anchorRef` and `isGenerated`;
  - the fetcher `pictureUrl` (token in a header, a queue, the caches).
- `src/components/corpus/CorpusImage.tsx`: one picture (lazy, placeholder, "Picture to come", errors in words).
- `src/components/corpus/MediaParts.tsx`: the draft badge, the generated label, captions with linked citations, and the failure card.
- `src/components/corpus/StoryPlate.tsx`: the story's picture and its novel link.
- `src/pages/corpus/CorpusImages.tsx` and `src/pages/corpus/CorpusNovels.tsx`: the pages above.
- `src/components/corpus/CorpusNav.tsx`: the Pictures and Graphic novels tabs. The Library tab is no longer lit on them.
- `supabase/functions/corpus-media/` (`index.ts`, `lib.ts`): the function.
  - Its tests are in the automaton repo: `docs/cloud/C8_corpus-media/lib_test.ts` and `_test/handler_test.ts`, run with `deno test`.
- `src/__tests__/corpus-media.test.tsx`: 12 tests.
  - the rules;
  - the token in the header, never in the URL;
  - one fetch per tab;
  - errors;
  - the gallery and the lightbox link;
  - without C8, and refused;
  - a novel's pages, citations, speech and Hindi;
  - the story plate, with and without C8;
  - the tabs.

## Switching it on

1. Apply C8 in the Lovable Cloud SQL editor. Run its checks before and after (`docs/cloud/C8_checks_2026-10-09.sql`, one query per paste).
2. Push this repo, then ask Lovable to deploy `corpus-media` without changing its code.
   - It needs no new secret.
   - It needs no `config.toml` entry, as `corpus-ingest` needs none.
3. On the desk, run `python scripts\corpus_media.py --hello`, then the plan, then `--apply`.
4. Publish. Check that `/corpus/images` shows the approved pictures to a reader and the drafts to an admin.

**Before C8 and the function are in:** the two pages say the pictures are not available yet, and the story pages read as before.

## Security (RELIABILITY_AUDIT Phase Y)

- No picture is public:
  - nothing is shared by link on Drive;
  - no URL carries a token;
  - every byte passes the reader gate and C8's visibility rule, as the reader.
- The four tables are in the closed schema `corpus`, with RLS on and no grants.
  - Readers have four functions.
  - The desk's eight are for `service_role` only, through the signed function.
- The function makes no AI call. Its cost is the invocation and Drive's quota.
- `gdrive-image-proxy` (public OG images) is not used and is unchanged.

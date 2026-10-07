# Taking the brain to the cloud: platform choice and design (2026-10-07)

Marker: CLOUD_BRAIN_2026_10_07. A design, not yet built.

The brain moves to the cloud. The translation engine stays on this machine.

## What has to move, measured

These figures were taken on 2026-10-05 from the backup `context_pre_stui_20261005_194301.db`. That backup was opened read-only and immutable.

| Part | Size today | Notes |
|---|---|---|
| `data/context.db` (the whole file) | 970 MB | Mostly vectors and indexes. It is not what is served. |
| Passages | 75,734 rows | 10.9 M characters of Sanskrit and 5.6 M characters of English. |
| Hindi (`translations_l10n`) | 12,513 rows | 3.1 M characters. |
| Passage vectors | 21,015 vectors | `models/gemini-embedding-001`, 3,072 dimensions, float32: 258 MB. |
| Entities | 32,646 mentions | |
| Images (`data/images`) | 30 MB | 9 approved, 10 draft. |
| Stories (`doc_stories`) | 13 rows | 4 drafts and 9 candidates. |

Only a small part of this needs to be served: the text, the approved stories and images, and the vectors. That is well under 1 GB.

Most of the 970 MB stays at home: the ledger, QA history, outcome logs, retired documents and raw OCR files.

## Recommendation

Use the Supabase project that already serves the Srangam site (Lovable Cloud) as the public brain. Do not add a second platform.

1. **Srangam already reads from it.**
   - `publish_srangam.py` / block_BE already push texts and passages there (`srangam_texts`, `srangam_text_passages`).
   - A second platform would split the brain from the reader that shows it.
2. **Cost.**
   - Supabase Pro is $25 a month. It includes 8 GB of database and 250 GB of egress.
   - Overage is $0.125 per GB of database and $0.09 per GB of egress.
   - The Small compute size costs $5 after the $10 compute credit.
   - The data to serve is under 1 GB, so the plan's allowances, not its overage prices, set the bill.
   - Prices read on 2026-10-07 from makerkit.dev (updated 2026-09-24) and activepieces.com (2026-09-30). Check Lovable's own billing, because Lovable Cloud is billed through Lovable.
3. **Vector search fits Postgres (pgvector).**
   - **The limit.** pgvector's HNSW and IVFFlat indexes accept at most 2,000 dimensions for `vector` and 4,000 for `halfvec`. The 3,072-dimension vectors therefore need either an expression index over `embedding::halfvec(3072)`, or shorter vectors.
   - **Shorter vectors without new calls.** gemini-embedding-001 is trained so that its leading dimensions can be used on their own (Matryoshka). The first 768 dimensions of the stored vectors, renormalised, should be close to what asking for 768 dimensions would give.
   - **Check it first.** Compare recall@12 on 50 real questions, 768 against 3,072, before relying on it. If it falls short, re-embedding everything costs about $0.56. That is the ledger's own rate: 56 passages cost $0.0015 on 2026-10-05.
   - **Size at 768 dimensions.** As `halfvec(768)`, 21,015 vectors take about 32 MB, plus the index.
4. **Pictures: R2 or Supabase Storage.**
   - Cloudflare R2 is $0.015 per GB-month and its egress is free. The first 10 GB are free, so 30 MB costs nothing.
   - Supabase Storage keeps everything in one place.
   - Either works. Choose R2 if the pictures are hotlinked heavily.
5. **Ask runs as an Edge Function, with the Gemini key held as a secret.**
   - It embeds the question, calls a `match_passages(query, k)` function in the database, and adds up to 3 editorial items (`brain_items`).
   - Then it calls Gemini, with the same system prompt as `/api/ask`.
   - Public use needs sign-in (Supabase Auth), a daily limit per user, and a global spend cap mirrored from `budget_state`.

**Alternative: Cloudflare.**
- The stack would be Workers Paid ($5 a month), D1, Vectorize and R2.
- Vectorize includes 10 million stored dimensions and 50 million queried dimensions a month, then charges $0.05 per 100 million stored and $0.01 per million queried. 21,015 vectors at 768 dimensions are 16 million stored dimensions, which costs a few cents.
- It is the cheapest option at scale. But it is a second platform beside the Supabase that Srangam uses, and the reader would have to move or call across.
- Revisit it if the site leaves Lovable.

## Design: one-way and incremental, local first

```
this PC (authoring)                              cloud (serving, read-only to the public)
  OCR -> translate -> QA -> stories/images            srangam_texts / srangam_text_passages (exists)
  approve (person)                                    srangam_passage_vectors  halfvec(768) + HNSW
  maintenance (3-hourly): embeddings, brain_items     srangam_stories  (approved only)
        |                                             srangam_images   (approved; files in R2/Storage)
        +-- publish bridge (block_BE, existing) --->  brain_items      (approved stories, images, episodes)
            batches with content hashes; never pulls  edge fn: ask, book (HTML), search
```

- **This PC stays the source of truth.** The cloud receives only approved content and vectors. Each row carries the content hash it was built from, so a push sends only what changed. Nothing is ever pulled back.
- **Pushes use the existing publish bridge.** The repository holds no service key, consistent with the Lovable Cloud rule. Schema changes go through the Lovable SQL editor as reviewed migrations. Rows are never inserted into `schema_migrations` by hand.
- **Public book making** can run in an Edge Function that assembles HTML from approved stories, using the same audience layouts as `stories.py book`. PDF stays local, or the browser prints it.

## Phases

| Phase | What | Gate |
|---|---|---|
| C0 | Run the read-only audit Q1-Q6 (`srangam_migration_audit_2026_10_04.sql`) and verify block_BE | Already pending |
| C1 | Migrations for `srangam_passage_vectors` (halfvec 768, HNSW), `srangam_stories`, `srangam_images`, `brain_items`, and the RPC `match_passages` | Migration reviewed in the Lovable editor |
| C2 | Push vectors, then approved stories and images, through the bridge (incremental, hashed) | Recall check (768 vs 3,072) passes |
| C3 | Ask Edge Function behind sign-in, with a per-user and a global cap | Spend cap mirrored |
| C4 | Story library and book maker on the site (HTML) | Approved-only data |

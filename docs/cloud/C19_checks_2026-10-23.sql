-- C19 checks (HEALTH_MAIL_C19_2026_10_23): read-only, one query per paste in the Lovable Cloud SQL editor.

-- H1. The trigger and its function are there (expect 1 row: corner_worker_health, enabled O).
SELECT t.tgname, t.tgenabled, p.proname
FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
WHERE t.tgrelid = 'corner.worker'::regclass AND t.tgname = 'corner_worker_health';

-- H2. The outbox takes 'health' (expect the CHECK's text to name health).
SELECT con.conname, pg_get_constraintdef(con.oid) AS def
FROM pg_constraint con WHERE con.conrelid = 'corner.outbox'::regclass AND con.contype = 'c';

-- H3. The last report and when it was mailed.
SELECT status, problems, mailed_at, seen_at FROM corner.health_state;

-- H4. The desk's last visit and what it said of its health (after the desk carries HEALTH_2026_10_23).
SELECT w.last_seen, w.info -> 'health' AS health, w.info -> 'sync' -> 'mirror' AS mirror FROM corner.worker w;

-- H5. The health emails of the last week: queued, sent, failed.
SELECT o.id, o.created_at, o.sent_at, o.failed_at, o.attempts, o.subject
FROM corner.outbox o WHERE o.kind = 'health' AND o.created_at > now() - interval '7 days' ORDER BY o.id DESC LIMIT 20;

-- H6. Is the Corner's mail on (expect true; the super admin turns it on in the Corner's settings).
SELECT value FROM corner.settings WHERE key = 'mail_enabled';

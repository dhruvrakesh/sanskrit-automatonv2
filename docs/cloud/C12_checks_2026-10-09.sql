-- ============================================================
-- C12 checks (CORNER_MAIL_C12_2026_10_09). Read-only. ONE QUERY PER PASTE; export each result
-- (Export CSV) to D:\backups\corner_2026-10-09\ and keep it. No query here shows an address or a body.
--
-- The order:  P1  ->  C12 in one paste  ->  V1-V3  ->  (the corner-mail edge function deployed,
--             RESEND_API_KEY in Lovable Secrets, the super admin turns mail on in Corner -> Settings)
--             ->  D1-D2 whenever you want to see what the Corner has sent.
-- ============================================================


-- ---------------- PREFLIGHT (before C12) ----------------

-- P1 C9 and C10a are there, C7's invitations too, and C12 is not yet. Expect
--    true | true | true | true | true | settings_key_check | true
--    (key_checks names the CHECK on corner.settings.key that C12 widens; if no_c12_yet is false,
--    C12 has run: skip it).
SELECT to_regclass('corner.settings') IS NOT NULL AS c9_settings,
       to_regprocedure('public.corner_settings_set(text, text)') IS NOT NULL AS c9_settings_set,
       to_regclass('corner.requests') IS NOT NULL AS c9_requests,
       to_regprocedure('public.corner_request_track(bigint[])') IS NOT NULL AS c10a_track,
       to_regprocedure('rbac._token_hash(text)') IS NOT NULL AS c7_invites,
       (SELECT string_agg(x.conname, ', ' ORDER BY x.conname) FROM pg_constraint x
         WHERE x.conrelid = to_regclass('corner.settings') AND x.contype = 'c') AS key_checks,
       to_regclass('corner.outbox') IS NULL AS no_c12_yet;


-- ---------------- AFTER C12 ----------------

-- V1 the two tables: RLS on, closed to everyone (the edge function reads them only through
--    corner_mail_claim). Expect 2 rows, rls true and every other column false:
--      mail_prefs | true | false | false | false | false | false
--      outbox     | true | false | false | false | false | false
SELECT c.relname, c.relrowsecurity AS rls,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_select,
       has_table_privilege('authenticated', c.oid, 'INSERT') AS auth_insert,
       has_table_privilege('service_role', c.oid, 'SELECT') AS service_select,
       has_table_privilege('service_role', c.oid, 'UPDATE') AS service_update
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'corner' AND c.relname IN ('mail_prefs', 'outbox') AND c.relkind = 'r'
ORDER BY 1;

-- V2 who may call what. Expect 10 rows, config {search_path=""} and anon false everywhere;
--    security_definer true for all but the two plain helpers _mail_text and _mail_usd (false):
--      corner._mail_on_request, _mail_text, _mail_usd   | authenticated false | service false
--      corner_mail_claim, corner_mail_done               | authenticated false | service true
--      corner_mail_invite, corner_mail_prefs, corner_mail_prefs_set, corner_mail_state,
--      corner_settings_set                               | authenticated true  | service as Supabase's
--                                                          defaults give it (each refuses anyone who
--                                                          is not signed in)
SELECT n.nspname, p.proname, pg_get_function_identity_arguments(p.oid) AS args, p.prosecdef AS security_definer,
       p.proconfig AS config,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE (n.nspname = 'corner' AND p.proname LIKE '\_mail\_%')
   OR (n.nspname = 'public' AND (p.proname LIKE 'corner\_mail\_%' OR p.proname = 'corner_settings_set'))
ORDER BY 1, 2;

-- V3 the trigger, the widened key CHECK and the settings. Expect:
--      check   | settings_key_check   | CHECK ((key = ANY (ARRAY['daily_cap_usd'::text, ... 'site_url'::text])))
--                                       (seven keys)
--      setting | daily_cap_usd, max_pending_per_person, researchers_need_approval as they were;
--                mail_enabled false | mail_from Srangam desk <desk@nartiang.org> | mail_reply_to (empty)
--                | site_url https://srangam.nartiang.org
--      trigger | corner_requests_mail | O (O = enabled) | AFTER INSERT OR UPDATE OF status ... FOR EACH
--                ROW EXECUTE FUNCTION corner._mail_on_request()
SELECT 'check' AS what, x.conname::text AS key, pg_get_constraintdef(x.oid) AS value, NULL::text AS detail
FROM pg_constraint x WHERE x.conrelid = 'corner.settings'::regclass AND x.contype = 'c'
UNION ALL
SELECT 'setting', s.key, s.value, s.updated_at::text FROM corner.settings s
UNION ALL
SELECT 'trigger', t.tgname::text, t.tgenabled::text, pg_get_triggerdef(t.oid)
FROM pg_trigger t WHERE t.tgrelid = 'corner.requests'::regclass AND NOT t.tgisinternal
ORDER BY 1, 2;


-- ---------------- ONCE MAIL IS ON ----------------

-- D1 the emails by kind: waiting (not sent, not given up), sent, failed (given up). Nothing while
--    mail is off. request_pending goes to editors, request_done / request_failed / request_rejected
--    to the one who asked, invite to an invited address.
SELECT o.kind,
       count(*) FILTER (WHERE o.sent_at IS NULL AND o.failed_at IS NULL) AS waiting,
       count(*) FILTER (WHERE o.sent_at IS NOT NULL) AS sent,
       count(*) FILTER (WHERE o.sent_at IS NULL AND o.failed_at IS NOT NULL) AS failed,
       max(o.sent_at) AS last_sent_at
FROM corner.outbox o
GROUP BY o.kind
ORDER BY o.kind;

-- D2 the last 20 emails, without addresses or bodies. attempts: how many times the edge function
--    took it (at most 5); last_error: what Resend or the claim said ('no address', 'the invitation
--    is no longer pending', 'not confirmed in 5 attempts', or the HTTP status and its text).
SELECT o.id, o.kind, o.request_id, o.created_at, o.sent_at, o.failed_at, o.attempts, o.last_error
FROM corner.outbox o
ORDER BY o.id DESC
LIMIT 20;

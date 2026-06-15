#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui.py -- Sanskrit Automaton dashboard.

Tabs:
  Ingest   -- upload PDFs, run ingest
  Translate -- configure + start translation run
  Live     -- real-time under-the-hood view (auto-refreshes every 2s)
  Queue    -- pending passages: filter, sort, skip
"""
import os, subprocess, sqlite3, time, glob, sys, json
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────
PY              = sys.executable
DB_PATH         = Path("data/context.db")
PROGRESS_PATH   = Path("data/translation_progress.json")
CONFIG_PATH     = Path("data/translation_config.json")
PROC_PID_PATH   = Path("data/.translate_pid")

ENGINES = [
    "gemini:gemini-2.5-flash",
    "gemini:gemini-2.5-pro",
    "gemini:gemini-2.0-flash",
    "openai:gpt-4o-mini",
    "openai:gpt-4o",
    "echo",
]

DEFAULT_ENGINE      = "gemini:gemini-2.5-flash"
DEFAULT_MIN_QUALITY = 0.25
DEFAULT_MIN_DEV     = 0.05

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sanskrit Automaton",
    page_icon=":om:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .san-block {
      font-family: "Noto Serif Devanagari", "Noto Serif", serif;
      font-size: 1.35rem;
      line-height: 1.9;
      color: #d97706;
      background: #1c1917;
      border-left: 3px solid #d97706;
      padding: 12px 16px;
      border-radius: 4px;
      white-space: pre-wrap;
  }
  .en-block {
      font-family: "Noto Serif", serif;
      font-size: 1.05rem;
      line-height: 1.8;
      color: #e5e7eb;
      background: #111827;
      border-left: 3px solid #3b82f6;
      padding: 12px 16px;
      border-radius: 4px;
      white-space: pre-wrap;
  }
  .status-badge {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.04em;
  }
  .badge-running { background: #065f46; color: #6ee7b7; }
  .badge-paused  { background: #78350f; color: #fcd34d; }
  .badge-done    { background: #1e3a5f; color: #93c5fd; }
  .badge-idle    { background: #374151; color: #9ca3af; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_progress():
    try:
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

def _load_cfg():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "engine": DEFAULT_ENGINE,
            "min_quality": DEFAULT_MIN_QUALITY,
            "min_dev": DEFAULT_MIN_DEV,
            "paused": False,
            "skip_rowids": [],
        }

def _save_cfg(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def _is_running():
    if not PROC_PID_PATH.exists():
        p = _load_progress()
        return p is not None and p.get("status") == "running"
    try:
        pid = int(PROC_PID_PATH.read_text().strip())
        try:
            import psutil
            return psutil.pid_exists(pid) and psutil.Process(pid).status() != "zombie"
        except ImportError:
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, PermissionError):
        PROC_PID_PATH.unlink(missing_ok=True)
        return False
    except Exception:
        p = _load_progress()
        return p is not None and p.get("status") == "running"

def _db_con():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(DB_PATH)

def _list_docs(proj):
    con = _db_con()
    if not con:
        return []
    try:
        return [r[0] for r in con.execute(
            "SELECT code FROM docs WHERE code LIKE ? ORDER BY code", (f"{proj}-%",)
        ).fetchall()]
    except Exception:
        return []
    finally:
        con.close()

def _progress_summary(proj):
    con = _db_con()
    if not con:
        return pd.DataFrame()
    try:
        rows = con.execute("""
            SELECT d.code AS doc,
                   COUNT(*) AS total,
                   SUM(CASE WHEN IFNULL(TRIM(p.translation),'')='' THEN 1 ELSE 0 END) AS missing,
                   ROUND(AVG(COALESCE(p.quality_score, 0)), 3) AS avg_quality
            FROM passages p JOIN docs d ON d.id=p.doc_id
            WHERE d.code LIKE ?
            GROUP BY d.code ORDER BY d.code
        """, (f"{proj}-%",)).fetchall()
        df = pd.DataFrame(rows, columns=["doc","total","missing","avg_quality"])
        df["translated"] = df["total"] - df["missing"]
        df["pct%"] = (df["translated"] / df["total"].replace(0,1) * 100).round(1)
        return df[["doc","total","translated","missing","pct%","avg_quality"]]
    except Exception:
        return pd.DataFrame()
    finally:
        con.close()

def _pending_passages(doc, min_quality=0.0):
    con = _db_con()
    if not con:
        return pd.DataFrame()
    try:
        rows = con.execute("""
            SELECT p.rowid, p.page_no, p.idx,
                   SUBSTR(COALESCE(p.text,''), 1, 150) AS text_preview,
                   COALESCE(p.quality_score, 0.0) AS quality,
                   COALESCE(p.verse_ref, '') AS verse_ref,
                   COALESCE(p.chandas, '') AS chandas,
                   COALESCE(p.text_type, 'mula') AS text_type
            FROM passages p
            JOIN docs d ON d.id = p.doc_id
            WHERE d.code = ?
              AND COALESCE(TRIM(p.translation), '') = ''
              AND COALESCE(p.text_type, 'mula') NOT IN ('noise', 'frontmatter')
            ORDER BY p.page_no, p.idx
        """, (doc,)).fetchall()
        df = pd.DataFrame(rows, columns=[
            "rowid","page","idx","text_preview","quality","verse_ref","chandas","text_type"
        ])
        if min_quality > 0 and not df.empty:
            df["below_threshold"] = (df["quality"] > 0) & (df["quality"] < min_quality)
        else:
            df["below_threshold"] = False
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        con.close()

def _quality_color(q):
    if q == 0:   return "#6b7280"
    if q < 0.3:  return "#ef4444"
    if q < 0.6:  return "#f59e0b"
    return "#22c55e"

def _launch_translation(doc, engine, min_quality, min_dev,
                         since_page, until_page, sleep_s, retranslate):
    cfg = _load_cfg()
    cfg["engine"]      = engine
    cfg["min_quality"] = min_quality
    cfg["min_dev"]     = min_dev
    cfg["paused"]      = False
    _save_cfg(cfg)

    log_path = Path("data/translate_stdout.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        PY, "scripts/translate_passages.py",
        "--doc", doc, "--engine", engine,
        "--min-quality", str(min_quality),
        "--min-dev",     str(min_dev),
        "--since-page",  str(since_page),
        "--until-page",  str(until_page),
        "--sleep",       str(sleep_s),
        "--progress",    str(PROGRESS_PATH),
        "--config",      str(CONFIG_PATH),
    ]
    if retranslate:
        cmd.append("--retranslate")

    proc = subprocess.Popen(
        cmd,
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
        cwd=Path.cwd(),
    )
    PROC_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROC_PID_PATH.write_text(str(proc.pid))
    return proc.pid


# ── Title + tabs ──────────────────────────────────────────────────────────────
st.title("Sanskrit Automaton")

tab_ingest, tab_translate, tab_live, tab_queue = st.tabs([
    "Ingest", "Translate", "Live Dashboard", "Queue"
])


# =============================================================================
# TAB 1 -- INGEST
# =============================================================================
with tab_ingest:
    st.subheader("Ingest PDFs")
    proj_ingest = st.text_input("Project prefix", value="NEWBOOK", key="proj_ingest")
    uploaded = st.file_uploader("Drop PDFs", type=["pdf"], accept_multiple_files=True)

    if uploaded:
        inbox = Path("inbox")
        inbox.mkdir(exist_ok=True)
        saved = []
        for f in uploaded:
            path = inbox / f.name
            path.write_bytes(f.getbuffer())
            saved.append(f.name)
        st.success(f"Saved {len(saved)} PDF(s) to inbox/")

    if st.button("Ingest PDFs in inbox", key="btn_ingest"):
        run_id = f"ingest-{proj_ingest}-{time.strftime('%Y%m%d-%H%M%S')}"
        pdfs   = glob.glob("inbox/*.pdf")
        if not pdfs:
            st.warning("No PDFs found in inbox/")
        else:
            for pdf in pdfs:
                code = f"{proj_ingest}-{Path(pdf).stem}"
                with st.spinner(f"Ingesting {Path(pdf).name}..."):
                    subprocess.run([
                        PY, "scripts/ingest_pdf.py",
                        "--pdf", pdf, "--doc", code, "--run-id", run_id,
                    ], check=False)
            st.success(f"Ingested {len(pdfs)} PDF(s)")

    st.divider()
    st.subheader("Corpus progress")
    proj_view = st.text_input("Filter by project prefix", value="NEWBOOK", key="proj_view")
    df = _progress_summary(proj_view)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No passages found for this prefix.")


# =============================================================================
# TAB 2 -- TRANSLATE
# =============================================================================
with tab_translate:
    st.subheader("Start a translation run")
    cfg = _load_cfg()
    running = _is_running()

    col_l, col_r = st.columns([2, 1])
    with col_l:
        proj_tr = st.text_input("Project prefix", value="NEWBOOK", key="proj_tr")
        docs    = _list_docs(proj_tr)
        doc_sel = (st.selectbox("Document", docs, key="doc_sel") if docs
                   else st.text_input("Document code", key="doc_sel_manual"))
    with col_r:
        default_idx = ENGINES.index(cfg.get("engine", DEFAULT_ENGINE)) \
                      if cfg.get("engine", DEFAULT_ENGINE) in ENGINES else 0
        engine_sel = st.selectbox(
            "AI Model", ENGINES, index=default_idx, key="engine_sel",
            help="gemini-2.5-flash = fast & cheap (default). "
                 "gemini-2.5-pro = highest quality (~17x more expensive).",
        )

    col_q, col_d, col_s = st.columns(3)
    with col_q:
        min_quality = st.slider(
            "Min OCR quality threshold", 0.0, 0.9, step=0.05,
            value=float(cfg.get("min_quality", DEFAULT_MIN_QUALITY)),
            key="min_quality_slider",
            help="Skip passages whose quality_score is below this. "
                 "0 = translate everything. 0.25 = skip bad OCR fragments.",
        )
    with col_d:
        min_dev = st.slider(
            "Min Devanagari density", 0.0, 0.3, step=0.01,
            value=float(cfg.get("min_dev", DEFAULT_MIN_DEV)),
            key="min_dev_slider",
            help="Skip passages with fewer than this fraction of Devanagari characters.",
        )
    with col_s:
        sleep_s = st.slider(
            "API sleep (s)", 0.1, 5.0, step=0.1, value=0.6, key="sleep_slider",
            help="Delay between API calls to avoid rate limits.",
        )

    pc1, pc2 = st.columns(2)
    with pc1:
        since_page = st.number_input("From page", min_value=1, value=1, key="since_page")
    with pc2:
        until_page = st.number_input("To page", min_value=1, value=999999, key="until_page")

    retranslate = st.checkbox("Re-translate existing passages", value=False, key="retranslate")

    st.divider()
    bc1, bc2, bc3 = st.columns(3)

    with bc1:
        if st.button("Start translation", disabled=running or not doc_sel, type="primary"):
            pid = _launch_translation(
                doc_sel, engine_sel, min_quality, min_dev,
                int(since_page), int(until_page), sleep_s, retranslate
            )
            st.success(f"Started (PID {pid}) -- open **Live Dashboard** tab to watch.")
            st.rerun()

    with bc2:
        if running:
            cfg2 = _load_cfg()
            paused = cfg2.get("paused", False)
            if st.button("Resume" if paused else "Pause", key="btn_pause"):
                cfg2["paused"] = not paused
                _save_cfg(cfg2)
                st.rerun()
        else:
            st.button("Pause", disabled=True, key="btn_pause_dis")

    with bc3:
        if running:
            if st.button("Stop", key="btn_stop"):
                try:
                    pid = int(PROC_PID_PATH.read_text().strip())
                    import signal
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
                PROC_PID_PATH.unlink(missing_ok=True)
                prog = _load_progress()
                if prog:
                    prog["status"] = "done"
                    PROGRESS_PATH.write_text(json.dumps(prog, ensure_ascii=False))
                st.rerun()

    if running:
        st.info("Translation is running -- see **Live Dashboard** tab for live progress.")
        st.divider()

        st.markdown("**Switch model mid-run** *(takes effect on the next verse)*")
        new_engine = st.selectbox("Switch to", ENGINES, key="live_engine_switch")
        if st.button("Apply model switch", key="btn_engine_switch"):
            cfg3 = _load_cfg()
            cfg3["engine"] = new_engine
            _save_cfg(cfg3)
            st.success(f"Will switch to **{new_engine}** on next verse.")

        st.markdown("**Adjust quality threshold mid-run**")
        cur_mq = float(_load_cfg().get("min_quality", DEFAULT_MIN_QUALITY))
        new_mq = st.slider("New min quality", 0.0, 0.9, step=0.05, value=cur_mq,
                           key="live_mq_slider")
        if st.button("Apply threshold", key="btn_mq_apply"):
            cfg4 = _load_cfg()
            cfg4["min_quality"] = new_mq
            _save_cfg(cfg4)
            st.success(f"Threshold updated to {new_mq:.2f} -- takes effect on next verse.")


# =============================================================================
# TAB 3 -- LIVE DASHBOARD
# =============================================================================
with tab_live:
    prog = _load_progress()
    is_running_now = _is_running()

    status = "idle"
    if prog is not None:
        status = prog.get("status", "idle")
        if status == "running" and not is_running_now:
            status = "done"

    badge_map = {
        "running": ("badge-running", "RUNNING"),
        "paused":  ("badge-paused",  "PAUSED"),
        "done":    ("badge-done",    "DONE"),
        "idle":    ("badge-idle",    "IDLE"),
    }
    badge_cls, badge_lbl = badge_map.get(status, ("badge-idle", "IDLE"))

    # -- Status header
    h1, h2, h3, h4 = st.columns(4)

    with h1:
        st.markdown(
            f'<span class="status-badge {badge_cls}">{badge_lbl}</span>',
            unsafe_allow_html=True,
        )
        if prog:
            st.caption(f"Doc: **{prog.get('doc','--')}**")

    with h2:
        if prog:
            done  = prog.get("verses_done", 0)
            total = prog.get("verses_total", 0)
            skip  = prog.get("skipped_quality", 0)
            errs  = prog.get("errors", 0)
            st.metric("Verses", f"{done} / {total}")
            st.caption(f"{skip} quality-skipped   {errs} errors")

    with h3:
        if prog:
            eng = prog.get("engine") or "--"
            st.metric("Model", eng.split(":")[-1] if ":" in eng else eng)
            st.caption(f"min quality: {prog.get('min_quality', 0):.2f}")

    with h4:
        if prog and prog.get("updated_at"):
            try:
                upd   = datetime.fromisoformat(prog["updated_at"].replace("Z", "+00:00"))
                age_s = int((datetime.now(timezone.utc) - upd).total_seconds())
                st.metric("Last update", f"{age_s}s ago")
            except Exception:
                pass
        if status == "running":
            st.caption("auto-refreshing every 2s")

    # -- Progress bar
    if prog and prog.get("verses_total", 0) > 0:
        frac = prog.get("verses_done", 0) / prog["verses_total"]
        st.progress(
            frac,
            text=f"{frac*100:.1f}%  ({prog.get('verses_done',0)} of {prog['verses_total']} verses)",
        )
    else:
        st.progress(0.0)

    st.divider()

    # -- Current verse (live)
    if prog and prog.get("current_text"):
        st.markdown("#### Under the hood -- current verse")

        meta_parts = []
        if prog.get("current_page") is not None:
            meta_parts.append(f"**page {prog['current_page']}.{prog.get('current_idx', 0)}**")
        if prog.get("current_quality") is not None:
            q    = float(prog["current_quality"])
            qclr = _quality_color(q)
            meta_parts.append(
                f"quality: <span style='color:{qclr}'>{q:.3f}</span>"
            )
        if prog.get("current_context_n"):
            meta_parts.append(f"context window: {prog['current_context_n']} preceding verses")
        if meta_parts:
            st.markdown("  &middot;  ".join(meta_parts), unsafe_allow_html=True)

        lc1, lc2 = st.columns(2)
        with lc1:
            st.markdown("**Sanskrit (Devanagari)**")
            san_text = prog["current_text"].replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(f'<div class="san-block">{san_text}</div>', unsafe_allow_html=True)
        with lc2:
            st.markdown("**English translation**")
            tr = (prog.get("current_translation") or "--").replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(f'<div class="en-block">{tr}</div>', unsafe_allow_html=True)
    else:
        if status == "idle":
            st.info("No active translation. Start a run from the **Translate** tab.")

    # -- Recent translations log
    if prog and prog.get("recent"):
        st.divider()
        st.markdown("#### Recent translations (newest first)")

        for entry in reversed(prog["recent"][:15]):
            q     = float(entry.get("quality", 0.0))
            qclr  = _quality_color(q)
            skip  = entry.get("skipped", False)
            ref   = f"[{entry['verse_ref']}] " if entry.get("verse_ref") else ""
            title = (
                f"p{entry.get('page')}.{entry.get('idx')}  {ref}"
                + ("  SKIPPED" if skip else "")
            )

            with st.expander(title, expanded=False):
                m1, m2, m3 = st.columns(3)
                m1.markdown(
                    f"quality: <span style='color:{qclr}'>**{q:.3f}**</span>",
                    unsafe_allow_html=True,
                )
                m2.markdown(f"engine: `{entry.get('engine','').split(':')[-1]}`")
                m3.markdown(f"chandas: {entry.get('chandas') or '--'}")

                rc1, rc2 = st.columns(2)
                with rc1:
                    t = entry.get("text", "").replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(
                        f'<div class="san-block" style="font-size:1rem">{t}</div>',
                        unsafe_allow_html=True,
                    )
                with rc2:
                    tr2 = entry.get("translation", "").replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(
                        f'<div class="en-block" style="font-size:0.95rem">{tr2}</div>',
                        unsafe_allow_html=True,
                    )

    # -- Raw process log
    log_path = Path("data/translate_stdout.log")
    if log_path.exists():
        with st.expander("Raw process log (last 40 lines)", expanded=False):
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            st.code("\n".join(lines[-40:]), language="text")

    # -- Auto-refresh while running/paused
    if status in ("running", "paused"):
        time.sleep(2)
        st.rerun()


# =============================================================================
# TAB 4 -- QUEUE
# =============================================================================
with tab_queue:
    st.subheader("Translation queue")
    st.caption("Untranslated passages -- inspect quality, skip bad OCR, manage priority.")

    cfg_q = _load_cfg()

    qc1, qc2 = st.columns([3, 1])
    with qc1:
        proj_q = st.text_input("Project prefix", value="NEWBOOK", key="proj_q")
        docs_q = _list_docs(proj_q)
        doc_q  = (st.selectbox("Document", docs_q, key="doc_q") if docs_q
                  else st.text_input("Document code", key="doc_q_manual"))
    with qc2:
        sort_by = st.selectbox(
            "Sort by",
            ["page (asc)", "quality (asc)", "quality (desc)"],
            key="q_sort",
        )
        show_mq = st.slider(
            "Highlight below quality", 0.0, 0.9, step=0.05,
            value=float(cfg_q.get("min_quality", DEFAULT_MIN_QUALITY)),
            key="q_mq",
        )

    if doc_q:
        df_q = _pending_passages(doc_q, min_quality=show_mq)

        if df_q.empty:
            st.success("No pending passages -- this document is fully translated!")
        else:
            if sort_by == "quality (asc)":
                df_q = df_q.sort_values("quality", ascending=True)
            elif sort_by == "quality (desc)":
                df_q = df_q.sort_values("quality", ascending=False)

            total_pending = len(df_q)
            below_thresh  = int(df_q["below_threshold"].sum())

            m1, m2, m3 = st.columns(3)
            m1.metric("Pending passages", total_pending)
            m2.metric("Below quality threshold", below_thresh)
            m3.metric("Would translate", total_pending - below_thresh)

            st.divider()

            current_skips = set(cfg_q.get("skip_rowids", []))

            ctrl1, ctrl2, ctrl3 = st.columns(3)
            with ctrl1:
                if st.button("Skip all below threshold", key="skip_all_low",
                             disabled=below_thresh == 0):
                    low_ids = df_q[df_q["below_threshold"]]["rowid"].tolist()
                    current_skips.update(low_ids)
                    cfg_q["skip_rowids"] = list(current_skips)
                    _save_cfg(cfg_q)
                    st.success(f"Marked {len(low_ids)} passages to skip.")
                    st.rerun()
            with ctrl2:
                if st.button("Clear all skips", key="clear_skips",
                             disabled=len(current_skips) == 0):
                    cfg_q["skip_rowids"] = []
                    _save_cfg(cfg_q)
                    st.success("All skips cleared.")
                    st.rerun()
            with ctrl3:
                st.caption(f"{len(current_skips)} passages currently marked to skip")

            st.divider()

            page_size   = 40
            total_pages = max(1, (len(df_q) + page_size - 1) // page_size)
            pg_num      = st.number_input("Page", 1, total_pages, 1, key="q_page") - 1
            df_page     = df_q.iloc[pg_num * page_size : (pg_num + 1) * page_size]

            for _, row in df_page.iterrows():
                rid          = int(row["rowid"])
                q            = float(row["quality"])
                below        = bool(row["below_threshold"])
                user_skipped = rid in current_skips

                title_parts = [
                    f"p{int(row['page'])}.{int(row['idx'])}",
                    f"  [{row['verse_ref']}]"   if row.get("verse_ref") else "",
                    f"  {row['chandas']}"        if row.get("chandas")  else "",
                    "  [below threshold]"        if below               else "",
                    "  [user-skipped]"           if user_skipped        else "",
                ]
                with st.expander("".join(title_parts), expanded=False):
                    eq1, eq2, eq3 = st.columns(3)
                    qclr = _quality_color(q)
                    eq1.markdown(
                        f"quality: <span style='color:{qclr}'>**{q:.3f}**</span>",
                        unsafe_allow_html=True,
                    )
                    eq2.markdown(f"type: `{row.get('text_type','--')}`")
                    eq3.markdown(f"rowid: `{rid}`")

                    preview = row["text_preview"].replace("<","&lt;").replace(">","&gt;")
                    st.markdown(
                        f'<div class="san-block" style="font-size:0.95rem">{preview}</div>',
                        unsafe_allow_html=True,
                    )

                    if user_skipped:
                        if st.button("Un-skip this passage", key=f"unskip_{rid}"):
                            current_skips.discard(rid)
                            cfg_q["skip_rowids"] = list(current_skips)
                            _save_cfg(cfg_q)
                            st.rerun()
                    else:
                        if st.button("Skip this passage", key=f"skip_{rid}"):
                            current_skips.add(rid)
                            cfg_q["skip_rowids"] = list(current_skips)
                            _save_cfg(cfg_q)
                            st.rerun()

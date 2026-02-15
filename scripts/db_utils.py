#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sqlite3, os, datetime, shutil, pathlib

PRAGMAS = [
    ("foreign_keys", "ON"),
    ("journal_mode", "WAL"),
    ("synchronous", "NORMAL"),
    ("temp_store", "MEMORY"),
]

BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS passages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id     INTEGER NOT NULL,
  page_no    INTEGER NOT NULL,
  idx        INTEGER NOT NULL,
  text       TEXT,
  norm       TEXT,
  sandhi     TEXT,
  morph      TEXT,
  translation TEXT,
  ents       TEXT,
  source     TEXT,
  created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(doc_id,page_no,idx),
  FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts
USING fts5(text, translation, tokenize='unicode61');

CREATE TABLE IF NOT EXISTS mt_cache(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  engine   TEXT NOT NULL,
  lang_in  TEXT NOT NULL,
  lang_out TEXT NOT NULL,
  text_hash TEXT NOT NULL,
  text     TEXT NOT NULL,
  output   TEXT NOT NULL,
  created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(engine,lang_in,lang_out,text_hash)
);

CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id  INTEGER NOT NULL,
  path    TEXT,
  page_lo INTEGER,
  page_hi INTEGER,
  sha256  TEXT,
  created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    for k, v in PRAGMAS:
        try:
            con.execute(f"PRAGMA {k}={v}")
        except sqlite3.OperationalError:
            pass
    return con

def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(BASE_SCHEMA)
    con.commit()

def ensure_doc(con: sqlite3.Connection, code: str) -> int:
    row = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()
    if row: return row[0]
    cur = con.cursor()
    cur.execute("INSERT INTO docs(code) VALUES(?)", (code,))
    con.commit()
    return cur.lastrowid

def backup_db(db_path: str) -> str:
    p = pathlib.Path(db_path)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = str(p.with_name(p.stem + f"_backup_{ts}").with_suffix(p.suffix))
    shutil.copy2(db_path, dest)
    return dest

#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_auth_role_2026_10_08.py  (2026-10-08)  AUTH_ROLE_2026_10_08

For the SRANGAM repo (run from D:\\srangam-42267, on main, after CORPUS_READER_C5_2026_10_08).
Heals the sign-in loop: a signed-in account that is not an admin, opening /auth, was sent to
/admin/tags; ProtectedRoute sent it back to /auth; and round again. The same race sent admins
to /auth and back after each sign-in, because the gate decided before has_role had answered.

  src/contexts/AuthContext.tsx         roleChecked: true once isAdmin is known for the
                                       signed-in user. A late has_role answer for a user who
                                       has meanwhile signed out is dropped. Nothing else changes.
  src/components/admin/ProtectedRoute.tsx  replaced (only if it is the known version):
                                       waits for the role; signed out goes to
                                       /auth?next=<the admin page>; signed in but not an admin
                                       sees "This area is for the site's editors" with links to
                                       /corpus and home, instead of a redirect.
  src/pages/Auth.tsx                   a signed-in visitor goes on once the role is known:
                                       to ?next=, else an admin to /admin/tags and anyone else
                                       to /corpus. <Navigate> instead of navigate() in render.
New file, delivered beside this script: src/__tests__/auth-role.test.tsx.

Anchored, all-or-nothing, marker-idempotent; keeps each file's line endings; backups
.bak_authrole_<date>.
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_auth_role_2026_10_08.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_auth_role_2026_10_08.py"
Then: npm run typecheck ; npx vitest run src/__tests__/auth-role.test.tsx ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "AUTH_ROLE_2026_10_08"
NEEDED = ["src/__tests__/auth-role.test.tsx"]

PROTECTED = "src/components/admin/ProtectedRoute.tsx"
PROTECTED_OLD_MD5 = "95780786e82a8099cb15feaf25c280a2"   # LF-normalised, the Phase N.5 version
PROTECTED_NEW = """import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isAdmin, isLoading, roleChecked } = useAuth();
  const location = useLocation();

  // AUTH_ROLE_2026_10_08: wait for the role as well as the session. Deciding while the has_role
  // answer was still on its way sent an admin to /auth and back after every sign-in.
  if (isLoading || (user && !roleChecked)) {
    return (
      <div className="min-h-screen flex items-center justify-center" role="status" aria-label="Checking access">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Phase N.5 \u2014 admin-only gate (server-backed via has_role RPC).
  if (!user) {
    // AUTH_ROLE_2026_10_08: after signing in, come back to the admin page that was asked for.
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/auth?next=${next}`} replace />;
  }

  // AUTH_ROLE_2026_10_08: a signed-in account that is not an admin is told so here. Sending it to
  // /auth looped: /auth sends a signed-in user on to /admin/tags, which sent it back to /auth.
  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md text-center space-y-3">
          <h1 className="text-xl font-semibold">This area is for the site's editors</h1>
          <p className="text-muted-foreground">You are signed in, but this account is not an editor's.</p>
          <p className="flex justify-center gap-6">
            <Link to="/corpus" className="text-primary hover:underline">Read the working corpus</Link>
            <Link to="/" className="text-primary hover:underline">Home</Link>
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
"""

EDITS = {
    "src/contexts/AuthContext.tsx": [
        ("react import",
         'import React, { createContext, useContext, useEffect, useState } from "react";\n',
         'import React, { createContext, useContext, useEffect, useRef, useState } from "react";\n'),
        ("interface",
         '  isAdmin: boolean;\n'
         '  isLoading: boolean;\n',
         '  isAdmin: boolean;\n'
         '  /** ' + MARK + ': true once isAdmin is known for the signed-in user (always true signed out). */\n'
         '  roleChecked: boolean;\n'
         '  isLoading: boolean;\n'),
        ("state",
         '  const [isAdmin, setIsAdmin] = useState(false);\n',
         '  const [isAdmin, setIsAdmin] = useState(false);\n'
         '  // ' + MARK + ': whose role isAdmin holds, and who is signed in now. Gates wait for\n'
         '  // roleChecked instead of reading a role that is still on its way; a late answer for a\n'
         '  // user who has meanwhile signed out is dropped.\n'
         '  const [roleFor, setRoleFor] = useState<string | null>(null);\n'
         '  const currentUid = useRef<string | null>(null);\n'),
        ("role answer",
         '    if (error) console.warn("has_role RPC failed", error);\n'
         '    setIsAdmin(data === true);\n',
         '    if (error) console.warn("has_role RPC failed", error);\n'
         '    if (currentUid.current !== userId) return;   // ' + MARK + '\n'
         '    setIsAdmin(data === true);\n'
         '    setRoleFor(userId);\n'),
        ("listener user",
         '\n        setSession(session);\n'
         '        setUser(session?.user ?? null);\n',
         '\n        setSession(session);\n'
         '        setUser(session?.user ?? null);\n'
         '        currentUid.current = session?.user?.id ?? null;   // ' + MARK + '\n'),
        ("signed out",
         '          setIsAdmin(false);\n',
         '          setIsAdmin(false);\n'
         '          setRoleFor(null);   // ' + MARK + '\n'),
        ("initial session",
         '\n      setSession(session);\n'
         '      setUser(session?.user ?? null);\n',
         '\n      setSession(session);\n'
         '      setUser(session?.user ?? null);\n'
         '      currentUid.current = session?.user?.id ?? null;   // ' + MARK + '\n'),
        ("value",
         '        isAdmin,\n'
         '        isLoading,\n',
         '        isAdmin,\n'
         '        roleChecked: !user || roleFor === user.id,   // ' + MARK + '\n'
         '        isLoading,\n'),
    ],
    "src/pages/Auth.tsx": [
        ("router import",
         'import { useNavigate, useSearchParams } from "react-router-dom";\n',
         'import { Navigate, useSearchParams } from "react-router-dom";\n'),
        ("auth hook",
         '  const { signIn, signUp, user } = useAuth();\n'
         '  const navigate = useNavigate();\n',
         '  const { signIn, signUp, user, isAdmin, roleChecked } = useAuth();   // ' + MARK + '\n'),
        ("comment",
         '  // path on this site is followed; without it the destination is /admin/tags, as before.\n',
         '  // path on this site is followed; without it an admin goes to /admin/tags and anyone else to\n'
         '  // /corpus (' + MARK + ').\n'),
        ("redirect",
         '  // Redirect if already logged in\n'
         '  if (user) {\n'
         '    navigate(next ?? "/admin/tags");\n'
         '    return null;\n'
         '  }\n',
         '  // Redirect if already logged in. ' + MARK + ': only once the role is known, so that an\n'
         '  // account that is not an admin goes to the corpus, not to /admin and back here. <Navigate>\n'
         '  // is the rendered form of navigate(), which React does not want called during render.\n'
         '  if (user) {\n'
         '    if (!roleChecked) {\n'
         '      return (\n'
         '        <div className="min-h-screen flex items-center justify-center" role="status" aria-label="Signing in">\n'
         '          <Loader2 className="h-8 w-8 animate-spin text-primary" />\n'
         '        </div>\n'
         '      );\n'
         '    }\n'
         '    return <Navigate to={next ?? (isAdmin ? "/admin/tags" : "/corpus")} replace />;\n'
         '  }\n'),
        ("after sign-in",
         '      await signIn(email, password);\n'
         '      navigate(next ?? "/admin/tags");\n',
         '      await signIn(email, password);\n'
         '      // ' + MARK + ': the redirect above takes over once the session and the role are known.\n'),
    ],
}


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("src/App.tsx").exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    problems = ["new file missing: %s (deliver it first)" % f for f in NEEDED if not Path(f).exists()]
    if "CORPUS_READER_C5_2026_10_08" not in Path("src/pages/Auth.tsx").read_text(encoding="utf-8"):
        problems.append("src/pages/Auth.tsx lacks CORPUS_READER_C5_2026_10_08: apply that patch first")
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []

    p = Path(PROTECTED)
    if not p.exists():
        problems.append("%s not found" % PROTECTED)
    else:
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (PROTECTED, MARK))
        elif hashlib.md5(src.encode("utf-8")).hexdigest() != PROTECTED_OLD_MD5:
            problems.append("%s is not the version this patch replaces" % PROTECTED)
        else:
            todo.append((p, PROTECTED_NEW.replace("\n", nl).encode("utf-8")))

    for rel, edits in EDITS.items():
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))

    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to patch: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_authrole_" + stamp))
        t = p.with_name(p.name + ".tmp_authrole"); t.write_bytes(data); os.replace(t, p)
        print("patched %s" % p)
    print("Next: npm run typecheck ; npx vitest run src/__tests__/auth-role.test.tsx ; npm run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())

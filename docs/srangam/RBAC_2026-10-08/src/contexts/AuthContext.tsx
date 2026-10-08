import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isAdmin: boolean;
  /** AUTH_ROLE_2026_10_08: true once isAdmin is known for the signed-in user (always true signed out). */
  roleChecked: boolean;
  /** RBAC_RESEARCHERS_2026_10_08: the signed-in user's own roles (my_roles()); [] signed out. */
  roles: string[];
  /** RBAC_RESEARCHERS_2026_10_08: may invite researchers and set who reads the corpus. */
  isSuperAdmin: boolean;
  /** RBAC_RESEARCHERS_2026_10_08: an invited fellow researcher. */
  isResearcher: boolean;
  /** RBAC_RESEARCHERS_2026_10_08: ask the database again (after accepting an invitation). */
  refreshRoles: () => Promise<void>;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  /** redirectPath: where the confirmation email brings the new account back to (a path on this site). */
  signUp: (email: string, password: string, redirectPath?: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  // AUTH_ROLE_2026_10_08: whose role isAdmin holds, and who is signed in now. Gates wait for
  // roleChecked instead of reading a role that is still on its way; a late answer for a
  // user who has meanwhile signed out is dropped.
  const [roleFor, setRoleFor] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>([]);   // RBAC_RESEARCHERS_2026_10_08
  const currentUid = useRef<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  const checkAdminRole = async (userId: string) => {
    // Phase M.2: role checks go through SECURITY DEFINER RPC, not direct
    // table reads. Returns only a boolean — no row exposure, no enumeration.
    // RBAC_RESEARCHERS_2026_10_08: my_roles() (C7) returns the caller's own roles, asked at the same
    // time. Until C7 is applied it does not exist, and the roles follow has_role alone.
    const [{ data, error }, mine] = await Promise.all([
      supabase.rpc("has_role", {
        _user_id: userId,
        _role: "admin",
      }),
      (async (): Promise<{ data: unknown; error: unknown }> => {
        try {
          // Not in the generated types until Lovable regenerates them after C7.
          const db = supabase as unknown as { rpc: (fn: string) => PromiseLike<{ data: unknown; error: unknown }> };
          return await db.rpc("my_roles");
        } catch (e) {
          return { data: null, error: e };
        }
      })(),
    ]);
    if (error) console.warn("has_role RPC failed", error);
    if (currentUid.current !== userId) return;   // AUTH_ROLE_2026_10_08
    const admin = data === true;
    const list: string[] = Array.isArray(mine.data)
      ? mine.data.filter((r: unknown): r is string => typeof r === "string")
      : admin ? ["admin"] : [];
    setIsAdmin(admin);
    setRoles(list);
    setRoleFor(userId);
  };

  const refreshRoles = async () => {
    const uid = currentUid.current;   // RBAC_RESEARCHERS_2026_10_08
    if (uid) await checkAdminRole(uid);
  };

  useEffect(() => {
    // Set up auth state listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        currentUid.current = session?.user?.id ?? null;   // AUTH_ROLE_2026_10_08
        
        if (session?.user) {
          // Defer admin check to avoid blocking auth state change
          setTimeout(() => {
            checkAdminRole(session.user.id);
          }, 0);
        } else {
          setIsAdmin(false);
          setRoleFor(null);   // AUTH_ROLE_2026_10_08
          setRoles([]);       // RBAC_RESEARCHERS_2026_10_08
        }
        
        setIsLoading(false);
      }
    );

    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      currentUid.current = session?.user?.id ?? null;   // AUTH_ROLE_2026_10_08
      
      if (session?.user) {
        checkAdminRole(session.user.id);
      }
      
      setIsLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      toast({
        title: "Sign in failed",
        description: error.message,
        variant: "destructive",
      });
      throw error;
    }

    toast({
      title: "Welcome back!",
      description: "Successfully signed in.",
    });
  };

  const signUp = async (email: string, password: string, redirectPath?: string) => {
    // RBAC_RESEARCHERS_2026_10_08: the confirmation email brings a reader or an invited researcher
    // back to the page they came from; without one, to /admin/tags as before.
    const path = redirectPath && redirectPath.startsWith("/") && !redirectPath.startsWith("//")
      ? redirectPath
      : "/admin/tags";
    const redirectUrl = `${window.location.origin}${path}`;

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectUrl,
      },
    });

    if (error) {
      toast({
        title: "Sign up failed",
        description: error.message,
        variant: "destructive",
      });
      throw error;
    }

    // RBAC_RESEARCHERS_2026_10_08: say what happens next. With a session the account is signed in
    // already; without one the address must be confirmed first.
    toast(data?.session
      ? { title: "Account created!", description: "You are signed in." }
      : { title: "Account created!", description: "Check your email: open the link in it to confirm your address, then sign in." });
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();

    if (error) {
      toast({
        title: "Sign out failed",
        description: error.message,
        variant: "destructive",
      });
      throw error;
    }

    toast({
      title: "Signed out",
      description: "Successfully signed out.",
    });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isAdmin,
        roleChecked: !user || roleFor === user.id,   // AUTH_ROLE_2026_10_08
        // RBAC_RESEARCHERS_2026_10_08: only roles known to belong to this user count.
        roles: user && roleFor === user.id ? roles : [],
        isSuperAdmin: !!user && roleFor === user.id && roles.includes("super_admin"),
        isResearcher: !!user && roleFor === user.id && roles.includes("researcher"),
        refreshRoles,
        isLoading,
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

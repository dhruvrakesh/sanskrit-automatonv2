import { useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { safeNext } from "@/lib/safeNext";   // CORPUS_READER_C5_2026_10_08
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2 } from "lucide-react";

export default function Auth() {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { signIn, signUp, user, isAdmin, roleChecked } = useAuth();   // AUTH_ROLE_2026_10_08
  // CORPUS_READER_C5_2026_10_08: ?next=/corpus... brings a reader back to the page they came from. Only a
  // path on this site is followed; without it an admin goes to /admin/tags and anyone else to
  // /corpus (AUTH_ROLE_2026_10_08).
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  // RBAC_RESEARCHERS_2026_10_08: an invited researcher comes here from /invite/<token>, and goes
  // back there; ?tab=signup opens the sign-up form for someone who has no account yet.
  const invite = !!next && next.startsWith("/invite/");
  const reader = !!next && (next.startsWith("/corpus") || invite);
  const startTab = params.get("tab") === "signup" ? "signup" : "login";

  // Redirect if already logged in. AUTH_ROLE_2026_10_08: only once the role is known, so that an
  // account that is not an admin goes to the corpus, not to /admin and back here. <Navigate>
  // is the rendered form of navigate(), which React does not want called during render.
  if (user) {
    if (!roleChecked) {
      return (
        <div className="min-h-screen flex items-center justify-center" role="status" aria-label="Signing in">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }
    return <Navigate to={next ?? (isAdmin ? "/admin/tags" : "/corpus")} replace />;
  }

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      await signIn(email, password);
      // AUTH_ROLE_2026_10_08: the redirect above takes over once the session and the role are known.
    } catch (error) {
      // Error is handled by AuthContext
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      await signUp(email, password, next ?? undefined);   // RBAC_RESEARCHERS_2026_10_08
      // After signup, switch to login tab
      setPassword("");
    } catch (error) {
      // Error is handled by AuthContext
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">{reader ? "Srangam" : "Srangam Admin"}</CardTitle>
          <CardDescription className="text-center">
            {invite
              ? "Sign in, or create an account, with the email address your invitation was sent to"
              : reader ? "Sign in to read the working corpus" : "Sign in to manage content"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue={startTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">Login</TabsTrigger>
              <TabsTrigger value="signup">Sign Up</TabsTrigger>
            </TabsList>
            
            <TabsContent value="login">
              <form onSubmit={handleSignIn} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-email">Email</Label>
                  <Input
                    id="login-email"
                    type="email"
                    placeholder={reader ? "you@example.com" : "admin@example.com"}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="login-password">Password</Label>
                  <Input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Sign In
                </Button>
              </form>
            </TabsContent>
            
            <TabsContent value="signup">
              <form onSubmit={handleSignUp} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="signup-email">Email</Label>
                  <Input
                    id="signup-email"
                    type="email"
                    placeholder={reader ? "you@example.com" : "admin@example.com"}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-password">Password</Label>
                  <Input
                    id="signup-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                    minLength={6}
                  />
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create Account
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

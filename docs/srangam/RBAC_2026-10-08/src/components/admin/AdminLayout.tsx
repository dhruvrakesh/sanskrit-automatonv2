import React from "react";
import { Outlet, useLocation } from "react-router-dom";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  Upload,
  Tags,
  Network,
  Languages,
  BarChart3,
  LogOut,
  User,
  FileText,
  BookOpen,
  GitBranch,
  Database,
  HeartPulse,
  Map as MapIcon,
  UserPlus,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { NavLink } from "@/components/NavLink";

const adminNavItems = [
  {
    title: "Dashboard",
    url: "/admin",
    icon: LayoutDashboard,
  },
  {
    title: "Articles",
    url: "/admin/articles",
    icon: FileText,
  },
  {
    title: "Import Articles",
    url: "/admin/import",
    icon: Upload,
  },
  {
    title: "GitHub Sync",
    url: "/admin/github-sync",
    icon: GitBranch,
  },
  {
    title: "Tag Management",
    url: "/admin/tags",
    icon: Tags,
  },
  {
    title: "Cross-References",
    url: "/admin/cross-refs",
    icon: Network,
  },
  {
    title: "Cultural Terms",
    url: "/admin/cultural-terms",
    icon: Languages,
  },
  {
    title: "Purana References",
    url: "/admin/purana-refs",
    icon: BookOpen,
  },
  {
    title: "Analytics",
    url: "/admin/analytics",
    icon: BarChart3,
  },
  {
    title: "Context Management",
    url: "/admin/context",
    icon: Database,
  },
  {
    title: "Data Health",
    url: "/admin/data-health",
    icon: HeartPulse,
  },
  {
    title: "Geography & Media",
    url: "/admin/geography-media",
    icon: MapIcon,
  },
  {
    title: "Corpus Correlations",
    url: "/admin/corpus-correlations",
    icon: Network,
  },
  // RBAC_RESEARCHERS_2026_10_08: invitations and roles, for the super admin only.
  {
    title: "Researchers",
    url: "/admin/researchers",
    icon: UserPlus,
    superOnly: true,
  },
];

export function AdminLayout() {
  const location = useLocation();
  const { user, isAdmin, isSuperAdmin, signOut } = useAuth();   // RBAC_RESEARCHERS_2026_10_08

  return (
    <ErrorBoundary>
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <Sidebar className="border-r border-border" collapsible="icon">
            <SidebarContent>
              <SidebarGroup>
                <SidebarGroupLabel>Admin Panel</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {adminNavItems.filter((item) => !item.superOnly || isSuperAdmin).map((item) => {
                      const isActive = location.pathname === item.url;
                      return (
                        <SidebarMenuItem key={item.title}>
                          <SidebarMenuButton asChild isActive={isActive}>
                            <NavLink
                              to={item.url}
                              end
                              className="flex items-center gap-3"
                              activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                            >
                              <item.icon className="h-4 w-4" />
                              <span>{item.title}</span>
                            </NavLink>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      );
                    })}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            </SidebarContent>
          </Sidebar>

          <main className="flex-1 w-full">
            {/* Sidebar trigger visible on mobile/collapsed state */}
            <div className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
              <div className="flex min-w-0 items-center gap-2">
                <SidebarTrigger className="mr-2" />
                <h1 className="truncate text-base font-semibold text-foreground sm:text-lg">
                  Admin Dashboard
                </h1>
              </div>
              
              {/* RBAC_RESEARCHERS_2026_10_08: the email and the button label give way on a phone. */}
              <div className="flex shrink-0 items-center gap-2 sm:gap-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <User className="hidden h-4 w-4 sm:block" />
                  <span className="hidden truncate max-w-[150px] sm:inline" title={user?.email ?? undefined}>{user?.email}</span>
                  {isAdmin && (
                    <span className="whitespace-nowrap px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs font-medium">
                      {isSuperAdmin ? "Super admin" : "Admin"}
                    </span>
                  )}
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => signOut()}
                  className="gap-2"
                  aria-label="Sign Out"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Sign Out</span>
                </Button>
              </div>
            </div>

            <div className="p-6">
              <ErrorBoundary>
                <Outlet />
              </ErrorBoundary>
            </div>
          </main>
        </div>
      </SidebarProvider>
    </ErrorBoundary>
  );
}

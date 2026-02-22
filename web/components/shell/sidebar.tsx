"use client";

/**
 * FDA-270 [FE-016] — App Shell Sidebar
 * ======================================
 * Left navigation sidebar with:
 *   - FDA Tools logo + product name
 *   - 6 primary nav sections
 *   - Collapse toggle (icon-only mode)
 *   - Active route highlighting
 *   - User avatar + sign-out action
 */

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";

// ── Icons (inline SVG to avoid lucide-react dependency issues pre-npm) ────

function IconGrid(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>
    </svg>
  );
}
function IconFolder(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
    </svg>
  );
}
function IconSearch(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
  );
}
function IconCpu(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>
      <path d="M15 2v2M9 2v2M15 20v2M9 20v2M2 15h2M2 9h2M20 15h2M20 9h2"/>
    </svg>
  );
}
function IconFileText(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
    </svg>
  );
}
function IconSettings(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  );
}
function IconChevronLeft(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <polyline points="15 18 9 12 15 6"/>
    </svg>
  );
}
function IconLogOut(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
      <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
    </svg>
  );
}

// ── Nav items ─────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { href: "/dashboard",  label: "Dashboard",  Icon: IconGrid,     section: "main" },
  { href: "/projects",   label: "Projects",   Icon: IconFolder,   section: "main" },
  { href: "/research",   label: "Research",   Icon: IconSearch,   section: "main" },
  { href: "/agents",     label: "Agents",     Icon: IconCpu,      section: "main" },
  { href: "/documents",  label: "Documents",  Icon: IconFileText, section: "main" },
  { href: "/settings",   label: "Settings",   Icon: IconSettings, section: "footer" },
] as const;

// ── FDALogo ───────────────────────────────────────────────────────────────

function FDALogo({ collapsed }: { collapsed: boolean }) {
  return (
    <div className={cn("flex items-center gap-3 px-4 py-5 border-b border-border", collapsed && "justify-center px-0")}>
      {/* Geometric mark */}
      <div className="relative flex-shrink-0 w-8 h-8">
        <div className="absolute inset-0 rounded-md bg-[#005EA2]" />
        <div className="absolute inset-[3px] rounded-sm bg-white/20" />
        <span className="absolute inset-0 flex items-center justify-center text-white text-[10px] font-black tracking-tighter leading-none">
          FDA
        </span>
      </div>
      {!collapsed && (
        <div>
          <p className="text-sm font-semibold text-foreground leading-tight">FDA Tools</p>
          <p className="text-[10px] text-muted-foreground leading-tight uppercase tracking-widest">MDRP</p>
        </div>
      )}
    </div>
  );
}

// ── NavItem ───────────────────────────────────────────────────────────────

function NavItem({
  href,
  label,
  Icon,
  collapsed,
}: {
  href: string;
  label: string;
  Icon: React.FC<React.SVGProps<SVGSVGElement>>;
  collapsed: boolean;
}) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(href + "/");

  return (
    <Link
      href={href}
      title={collapsed ? label : undefined}
      className={cn(
        "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
        "hover:bg-accent hover:text-accent-foreground",
        isActive
          ? "bg-[#005EA2]/10 text-[#005EA2] dark:bg-[#005EA2]/20 dark:text-[#60A5FA]"
          : "text-muted-foreground",
        collapsed && "justify-center px-0 w-10 h-10 mx-auto"
      )}
    >
      <Icon
        className={cn(
          "flex-shrink-0 w-[18px] h-[18px] transition-colors",
          isActive ? "stroke-[#005EA2] dark:stroke-[#60A5FA]" : "stroke-muted-foreground group-hover:stroke-foreground"
        )}
      />
      {!collapsed && <span>{label}</span>}
      {/* Active indicator bar */}
      {isActive && !collapsed && (
        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#005EA2] dark:bg-[#60A5FA]" />
      )}
    </Link>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, signOut } = useAuth();

  const mainNav = NAV_ITEMS.filter((n) => n.section === "main");
  const footerNav = NAV_ITEMS.filter((n) => n.section === "footer");

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "??";

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-border bg-background",
        "transition-[width] duration-200 ease-in-out",
        collapsed ? "w-[60px]" : "w-[240px]"
      )}
    >
      {/* Logo */}
      <FDALogo collapsed={collapsed} />

      {/* Main nav */}
      <nav className={cn("flex-1 px-2 py-4 space-y-0.5", collapsed && "px-0 flex flex-col items-center")}>
        {mainNav.map((item) => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}
      </nav>

      {/* Footer: settings + user */}
      <div className={cn("px-2 py-4 border-t border-border space-y-0.5", collapsed && "px-0 flex flex-col items-center")}>
        {footerNav.map((item) => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}

        {/* User avatar */}
        <button
          onClick={() => signOut?.()}
          title={collapsed ? `Sign out (${user?.email})` : undefined}
          className={cn(
            "group flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm",
            "text-muted-foreground hover:bg-accent hover:text-foreground transition-all",
            collapsed && "justify-center px-0 w-10 h-10 mx-auto"
          )}
        >
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#005EA2]/20 flex items-center justify-center">
            <span className="text-[10px] font-bold text-[#005EA2] dark:text-[#60A5FA]">{initials}</span>
          </div>
          {!collapsed && (
            <span className="flex-1 truncate text-left text-xs">{user?.email ?? "User"}</span>
          )}
          {!collapsed && (
            <IconLogOut className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
          )}
        </button>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className={cn(
          "absolute -right-3 top-[72px] z-10",
          "w-6 h-6 rounded-full border border-border bg-background shadow-sm",
          "flex items-center justify-center",
          "hover:bg-accent transition-colors"
        )}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <IconChevronLeft
          className={cn("w-3 h-3 text-muted-foreground transition-transform duration-200", collapsed && "rotate-180")}
        />
      </button>
    </aside>
  );
}

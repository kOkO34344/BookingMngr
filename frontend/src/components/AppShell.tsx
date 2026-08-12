"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useApp } from "@/lib/app-context";
import { useAuth } from "@/lib/auth";
import { formatDateLong, todayIso } from "@/lib/format";

import { Button, Select, cx } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/calendar", label: "Calendar" },
  { href: "/reservations", label: "Reservations" },
  { href: "/tasks", label: "Tasks" },
  { href: "/reports", label: "Reports" },
  { href: "/properties", label: "Properties" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { properties, propertyId, setPropertyId, date, setDate } = useApp();

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="px-5 py-5">
          <p className="text-sm font-semibold tracking-tight text-slate-900">BookingMngr</p>
          <p className="text-xs text-slate-500">Property operations</p>
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {NAV.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cx(
                  "block rounded-lg px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-slate-900 font-medium text-white"
                    : "text-slate-600 hover:bg-slate-100",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-100 px-4 py-3">
          <p className="truncate text-xs text-slate-500">
            Signed in as <span className="font-medium text-slate-700">{user?.username}</span>
          </p>
          <Button variant="ghost" size="sm" className="mt-1 -ml-2" onClick={logout}>
            Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
          <p className="text-sm font-medium text-slate-700">{formatDateLong(date)}</p>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value || todayIso())}
              className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              aria-label="Working date"
            />
            <Select
              aria-label="Property"
              className="w-48"
              value={propertyId ?? ""}
              onChange={(event) =>
                setPropertyId(event.target.value ? Number(event.target.value) : undefined)
              }
            >
              <option value="">All properties</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </Select>
          </div>
        </header>

        {/* Mobile nav */}
        <nav className="scroll-thin flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2 md:hidden">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cx(
                "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm",
                pathname.startsWith(item.href)
                  ? "bg-slate-900 text-white"
                  : "text-slate-600",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}

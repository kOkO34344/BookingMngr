"use client";

import type { ReactNode } from "react";

import { Button } from "./ui";

export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto p-4">
      <div className="absolute inset-0 bg-slate-900/25" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        className={`relative my-8 w-full ${wide ? "max-w-3xl" : "max-w-lg"} rounded-xl border border-slate-200 bg-white shadow-xl`}
      >
        <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </header>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

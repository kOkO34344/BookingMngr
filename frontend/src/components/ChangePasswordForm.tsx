"use client";

import { useState, type FormEvent } from "react";

import { api, ApiError } from "@/lib/api";

import { Button, ErrorNote, Field, Input } from "./ui";

/** Mirrors MIN_PASSWORD_LENGTH in backend/app/schemas/auth.py. */
const MIN_LENGTH = 10;

export function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    // Caught here rather than at the API so the user is told before a round trip.
    if (next !== repeat) {
      setError("The new passwords do not match.");
      return;
    }
    if (next.length < MIN_LENGTH) {
      setError(`New password must be at least ${MIN_LENGTH} characters.`);
      return;
    }

    setSaving(true);
    try {
      await api.auth.changePassword(current, next);
      setStatus("Password updated.");
      setCurrent("");
      setNext("");
      setRepeat("");
      setTimeout(onDone, 900);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change password");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <ErrorNote message={error} />}
      {status && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {status}
        </p>
      )}

      <Field label="Current password">
        <Input
          type="password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
        />
      </Field>
      <Field label="New password" hint={`At least ${MIN_LENGTH} characters`}>
        <Input
          type="password"
          autoComplete="new-password"
          required
          value={next}
          onChange={(event) => setNext(event.target.value)}
        />
      </Field>
      <Field label="Repeat new password">
        <Input
          type="password"
          autoComplete="new-password"
          required
          value={repeat}
          onChange={(event) => setRepeat(event.target.value)}
        />
      </Field>

      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={saving}>
          {saving ? "Saving…" : "Change password"}
        </Button>
      </div>
    </form>
  );
}

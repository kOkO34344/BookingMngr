"use client";

import Link from "next/link";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import {
  formatDate,
  formatMoney,
  RESERVATION_STATUS_LABELS,
  SOURCE_LABELS,
} from "@/lib/format";
import type { Reservation, ReservationStatus } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

import { PaymentStatusBadge, ReservationStatusBadge } from "./badges";
import { Button, ErrorNote, Select, Spinner } from "./ui";

const STATUSES = Object.keys(RESERVATION_STATUS_LABELS) as ReservationStatus[];

/** Slide-over with reservation details and the two or three actions worth having inline. */
export function ReservationSidePanel({
  reservationId,
  onClose,
  onChanged,
}: {
  reservationId: number;
  onClose: () => void;
  onChanged?: (reservation: Reservation) => void;
}) {
  const { data, loading, error, setData } = useAsync(
    () => api.reservations.get(reservationId),
    [reservationId],
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function changeStatus(status: ReservationStatus) {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await api.reservations.update(reservationId, { status });
      setData(updated);
      onChanged?.(updated);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not update");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div
        className="absolute inset-0 bg-slate-900/20"
        onClick={onClose}
        aria-hidden
      />
      <aside className="relative flex h-full w-full max-w-sm flex-col overflow-y-auto border-l border-slate-200 bg-white shadow-xl">
        <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Reservation details</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </header>

        <div className="space-y-4 p-4">
          {loading && <Spinner />}
          {error && <ErrorNote message={error} />}
          {saveError && <ErrorNote message={saveError} />}

          {data && (
            <>
              <div>
                <p className="text-lg font-semibold text-slate-900">
                  {data.guest_display_name}
                </p>
                <p className="text-sm text-slate-500">
                  {data.property_name} · Unit {data.unit_name}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <ReservationStatusBadge status={data.status} />
                <PaymentStatusBadge status={data.payment_status} />
              </div>

              <dl className="space-y-2 text-sm">
                <Row label="Stay">
                  {formatDate(data.check_in_date)} → {formatDate(data.check_out_date)} (
                  {data.nights} night{data.nights === 1 ? "" : "s"})
                </Row>
                <Row label="Guests">{data.number_of_guests}</Row>
                <Row label="Channel">{SOURCE_LABELS[data.source]}</Row>
                <Row label="Reference">{data.source_reference ?? "—"}</Row>
                <Row label="Gross">{formatMoney(data.gross_amount, data.currency)}</Row>
                <Row label="Fees">{formatMoney(data.fees_amount, data.currency)}</Row>
                <Row label="Net payout">
                  <span className="font-semibold">
                    {formatMoney(data.net_payout_amount, data.currency)}
                  </span>
                </Row>
                <Row label="Payout date">{formatDate(data.payout_date)}</Row>
              </dl>

              {data.notes && (
                <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                  {data.notes}
                </p>
              )}

              <div className="space-y-2 border-t border-slate-100 pt-4">
                <label className="block text-xs font-medium text-slate-600">
                  Change status
                </label>
                <Select
                  value={data.status}
                  disabled={saving}
                  onChange={(event) => changeStatus(event.target.value as ReservationStatus)}
                >
                  {STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {RESERVATION_STATUS_LABELS[status]}
                    </option>
                  ))}
                </Select>

                <Link
                  href={`/reservations/${data.id}`}
                  className="block rounded-lg border border-slate-300 px-3 py-1.5 text-center text-sm text-slate-700 hover:bg-slate-50"
                >
                  Open full record
                </Link>
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right text-slate-800">{children}</dd>
    </div>
  );
}

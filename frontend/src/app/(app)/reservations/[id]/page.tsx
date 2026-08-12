"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { SourceTag } from "@/components/badges";
import {
  Button,
  Card,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import {
  formatDate,
  formatMoney,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  RESERVATION_STATUS_LABELS,
} from "@/lib/format";
import type { PaymentStatus, ReservationStatus } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

export default function ReservationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const reservationId = Number(params.id);

  const { data, loading, error, setData } = useAsync(
    () => api.reservations.get(reservationId),
    [reservationId],
  );

  const [form, setForm] = useState({
    status: "confirmed" as ReservationStatus,
    payment_status: "pending" as PaymentStatus,
    check_in_date: "",
    check_out_date: "",
    gross_amount: "",
    fees_amount: "",
    net_payout_amount: "",
    payout_date: "",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!data) return;
    setForm({
      status: data.status,
      payment_status: data.payment_status,
      check_in_date: data.check_in_date,
      check_out_date: data.check_out_date,
      gross_amount: data.gross_amount,
      fees_amount: data.fees_amount,
      net_payout_amount: data.net_payout_amount,
      payout_date: data.payout_date ?? "",
      notes: data.notes ?? "",
    });
  }, [data]);

  async function save() {
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const updated = await api.reservations.update(reservationId, {
        ...form,
        payout_date: form.payout_date || null,
        notes: form.notes || null,
      });
      setData(updated);
      setSaved(true);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this reservation? Prefer changing status to canceled.")) {
      return;
    }
    try {
      await api.reservations.remove(reservationId);
      router.push("/reservations");
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not delete");
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorNote message={error} />;
  if (!data) return null;

  return (
    <>
      <PageHeader
        title={data.guest_display_name ?? "Reservation"}
        description={`${data.property_name} · Unit ${data.unit_name} · ${data.nights} night(s)`}
        action={
          <Link href="/reservations" className="text-sm text-slate-600 underline">
            Back to list
          </Link>
        }
      />

      {saveError && <ErrorNote message={saveError} />}
      {saved && (
        <p className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Saved.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Booking" className="lg:col-span-2">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Check-in">
              <Input
                type="date"
                value={form.check_in_date}
                onChange={(event) =>
                  setForm({ ...form, check_in_date: event.target.value })
                }
              />
            </Field>
            <Field label="Check-out">
              <Input
                type="date"
                value={form.check_out_date}
                onChange={(event) =>
                  setForm({ ...form, check_out_date: event.target.value })
                }
              />
            </Field>
            <Field label="Status">
              <Select
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as ReservationStatus })
                }
              >
                {(Object.keys(RESERVATION_STATUS_LABELS) as ReservationStatus[]).map(
                  (status) => (
                    <option key={status} value={status}>
                      {RESERVATION_STATUS_LABELS[status]}
                    </option>
                  ),
                )}
              </Select>
            </Field>
            <Field label="Payment status">
              <Select
                value={form.payment_status}
                onChange={(event) =>
                  setForm({
                    ...form,
                    payment_status: event.target.value as PaymentStatus,
                  })
                }
              >
                {(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[]).map((status) => (
                  <option key={status} value={status}>
                    {PAYMENT_STATUS_LABELS[status]}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field label="Notes" className="mt-3">
            <Textarea
              value={form.notes}
              onChange={(event) => setForm({ ...form, notes: event.target.value })}
            />
          </Field>

          <div className="mt-4 flex justify-between">
            <Button variant="danger" onClick={remove}>
              Delete
            </Button>
            <Button variant="primary" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Payout">
            <div className="space-y-3">
              <Field label="Gross amount">
                <Input
                  type="number"
                  step="0.01"
                  value={form.gross_amount}
                  onChange={(event) =>
                    setForm({ ...form, gross_amount: event.target.value })
                  }
                />
              </Field>
              <Field label="Platform fees">
                <Input
                  type="number"
                  step="0.01"
                  value={form.fees_amount}
                  onChange={(event) =>
                    setForm({ ...form, fees_amount: event.target.value })
                  }
                />
              </Field>
              <Field label="Net payout">
                <Input
                  type="number"
                  step="0.01"
                  value={form.net_payout_amount}
                  onChange={(event) =>
                    setForm({ ...form, net_payout_amount: event.target.value })
                  }
                />
              </Field>
              <Field label="Payout date">
                <Input
                  type="date"
                  value={form.payout_date}
                  onChange={(event) =>
                    setForm({ ...form, payout_date: event.target.value })
                  }
                />
              </Field>
            </div>
          </Card>

          <Card title="Source">
            <div className="space-y-2 text-sm text-slate-600">
              <SourceTag source={data.source} />
              <p>Reference: {data.source_reference ?? "—"}</p>
              <p>
                Payment method:{" "}
                {data.payment_method ? PAYMENT_METHOD_LABELS[data.payment_method] : "—"}
              </p>
              <p>Guests: {data.number_of_guests}</p>
              <p>
                Current net: {formatMoney(data.net_payout_amount, data.currency)} (paid out{" "}
                {formatDate(data.payout_date)})
              </p>
              <p className="text-xs text-slate-400">
                Created {formatDate(data.created_at)} · updated{" "}
                {formatDate(data.updated_at)}
              </p>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

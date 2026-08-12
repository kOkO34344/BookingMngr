"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { api, ApiError } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import {
  addDays,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  RESERVATION_STATUS_LABELS,
  SOURCE_LABELS,
  todayIso,
} from "@/lib/format";
import type {
  PaymentMethod,
  PaymentStatus,
  Reservation,
  ReservationSource,
  ReservationStatus,
  Unit,
} from "@/lib/types";

import { Button, ErrorNote, Field, Input, Select, Textarea } from "./ui";

const PAYMENT_METHODS: PaymentMethod[] = [
  "airbnb_payout",
  "booking_payout",
  "cash",
  "bank_transfer",
  "card",
];

/** Default channel → payment method, matching how the money usually arrives. */
const DEFAULT_METHOD: Record<ReservationSource, PaymentMethod> = {
  airbnb: "airbnb_payout",
  booking: "booking_payout",
  phone: "cash",
  whatsapp: "cash",
  email: "bank_transfer",
};

interface FormValues {
  property_id: string;
  unit_id: string;
  guest_name: string;
  check_in_date: string;
  check_out_date: string;
  number_of_guests: string;
  source: ReservationSource;
  source_reference: string;
  status: ReservationStatus;
  gross_amount: string;
  fees_amount: string;
  net_payout_amount: string;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  notes: string;
}

function initialValues(propertyId?: number): FormValues {
  return {
    property_id: propertyId ? String(propertyId) : "",
    unit_id: "",
    guest_name: "",
    check_in_date: todayIso(),
    check_out_date: addDays(todayIso(), 1),
    number_of_guests: "2",
    source: "phone",
    source_reference: "",
    status: "confirmed",
    gross_amount: "",
    fees_amount: "0",
    net_payout_amount: "",
    payment_method: "cash",
    payment_status: "pending",
    notes: "",
  };
}

/** Create form for the manual channels (phone / WhatsApp / email) — and OTAs if needed. */
export function ReservationForm({
  onCreated,
  onCancel,
}: {
  onCreated: (reservation: Reservation) => void;
  onCancel: () => void;
}) {
  const { properties, propertyId } = useApp();
  const [values, setValues] = useState<FormValues>(() => initialValues(propertyId));
  const [units, setUnits] = useState<Unit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selectedPropertyId = values.property_id
    ? Number(values.property_id)
    : properties[0]?.id;

  useEffect(() => {
    if (!selectedPropertyId) return;
    let active = true;
    api.units
      .listForProperty(selectedPropertyId)
      .then((result) => {
        if (active) setUnits(result);
      })
      .catch(() => setUnits([]));
    return () => {
      active = false;
    };
  }, [selectedPropertyId]);

  const impliedNet = useMemo(() => {
    const gross = Number(values.gross_amount || 0);
    const fees = Number(values.fees_amount || 0);
    if (Number.isNaN(gross) || Number.isNaN(fees)) return "";
    return (gross - fees).toFixed(2);
  }, [values.gross_amount, values.fees_amount]);

  function set<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.reservations.create({
        property_id: Number(values.property_id || selectedPropertyId),
        unit_id: Number(values.unit_id),
        guest_name: values.guest_name || null,
        check_in_date: values.check_in_date,
        check_out_date: values.check_out_date,
        number_of_guests: Number(values.number_of_guests),
        source: values.source,
        source_reference: values.source_reference || null,
        status: values.status,
        gross_amount: values.gross_amount || "0",
        fees_amount: values.fees_amount || "0",
        net_payout_amount: values.net_payout_amount || impliedNet || "0",
        payment_method: values.payment_method,
        payment_status: values.payment_status,
        notes: values.notes || null,
      });
      onCreated(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create reservation");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <ErrorNote message={error} />}

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Property">
          <Select
            required
            value={values.property_id || String(selectedPropertyId ?? "")}
            onChange={(event) => {
              set("property_id", event.target.value);
              set("unit_id", "");
            }}
          >
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Unit">
          <Select
            required
            value={values.unit_id}
            onChange={(event) => set("unit_id", event.target.value)}
          >
            <option value="">Select a unit…</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name_or_number}
                {unit.unit_type ? ` · ${unit.unit_type}` : ""}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Guest name">
          <Input
            value={values.guest_name}
            onChange={(event) => set("guest_name", event.target.value)}
            placeholder="e.g. Maria Petrova"
          />
        </Field>

        <Field label="Number of guests">
          <Input
            type="number"
            min={1}
            value={values.number_of_guests}
            onChange={(event) => set("number_of_guests", event.target.value)}
          />
        </Field>

        <Field label="Check-in">
          <Input
            type="date"
            required
            value={values.check_in_date}
            onChange={(event) => {
              set("check_in_date", event.target.value);
              if (event.target.value >= values.check_out_date) {
                set("check_out_date", addDays(event.target.value, 1));
              }
            }}
          />
        </Field>

        <Field label="Check-out">
          <Input
            type="date"
            required
            value={values.check_out_date}
            min={addDays(values.check_in_date, 1)}
            onChange={(event) => set("check_out_date", event.target.value)}
          />
        </Field>

        <Field label="Channel">
          <Select
            value={values.source}
            onChange={(event) => {
              const source = event.target.value as ReservationSource;
              set("source", source);
              set("payment_method", DEFAULT_METHOD[source]);
            }}
          >
            {(Object.keys(SOURCE_LABELS) as ReservationSource[]).map((source) => (
              <option key={source} value={source}>
                {SOURCE_LABELS[source]}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Reference" hint="Confirmation code, or a note about the call">
          <Input
            value={values.source_reference}
            onChange={(event) => set("source_reference", event.target.value)}
            placeholder="HMABC123 / 'called on WhatsApp'"
          />
        </Field>

        <Field label="Status">
          <Select
            value={values.status}
            onChange={(event) => set("status", event.target.value as ReservationStatus)}
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
            value={values.payment_status}
            onChange={(event) =>
              set("payment_status", event.target.value as PaymentStatus)
            }
          >
            {(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[]).map((status) => (
              <option key={status} value={status}>
                {PAYMENT_STATUS_LABELS[status]}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Gross amount" hint="Total paid by the guest">
          <Input
            type="number"
            step="0.01"
            min="0"
            value={values.gross_amount}
            onChange={(event) => set("gross_amount", event.target.value)}
          />
        </Field>

        <Field label="Platform fees">
          <Input
            type="number"
            step="0.01"
            min="0"
            value={values.fees_amount}
            onChange={(event) => set("fees_amount", event.target.value)}
          />
        </Field>

        <Field label="Net payout" hint={`Defaults to gross − fees (${impliedNet || "0.00"})`}>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={values.net_payout_amount}
            placeholder={impliedNet}
            onChange={(event) => set("net_payout_amount", event.target.value)}
          />
        </Field>

        <Field label="Payment method">
          <Select
            value={values.payment_method}
            onChange={(event) =>
              set("payment_method", event.target.value as PaymentMethod)
            }
          >
            {PAYMENT_METHODS.map((method) => (
              <option key={method} value={method}>
                {PAYMENT_METHOD_LABELS[method]}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <Field label="Notes">
        <Textarea
          value={values.notes}
          onChange={(event) => set("notes", event.target.value)}
          placeholder="Late arrival, extra bed, parking…"
        />
      </Field>

      <div className="flex justify-end gap-2">
        <Button type="button" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={submitting}>
          {submitting ? "Saving…" : "Create reservation"}
        </Button>
      </div>
    </form>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";

import { Modal } from "@/components/Modal";
import { ReservationForm } from "@/components/ReservationForm";
import {
  PaymentStatusBadge,
  ReservationStatusBadge,
  SourceTag,
} from "@/components/badges";
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import {
  formatDate,
  formatMoney,
  RESERVATION_STATUS_LABELS,
  SOURCE_LABELS,
} from "@/lib/format";
import type { ReservationSource, ReservationStatus } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

export default function ReservationsPage() {
  const { propertyId } = useApp();

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [status, setStatus] = useState<ReservationStatus | "">("");
  const [source, setSource] = useState<ReservationSource | "">("");
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);

  const reservations = useAsync(
    () =>
      api.reservations.list({
        property_id: propertyId,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        status: status || undefined,
        source: source || undefined,
        search: search || undefined,
        limit: 200,
      }),
    [propertyId, fromDate, toDate, status, source, search],
  );

  return (
    <>
      <PageHeader
        title="Reservations"
        description="Every booking, whichever channel it came from."
        action={
          <Button variant="primary" onClick={() => setShowForm(true)}>
            Add reservation
          </Button>
        }
      />

      <Card className="mb-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="From">
            <Input
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </Field>
          <Field label="To">
            <Input
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </Field>
          <Field label="Status">
            <Select
              value={status}
              onChange={(event) => setStatus(event.target.value as ReservationStatus | "")}
            >
              <option value="">Any status</option>
              {(Object.keys(RESERVATION_STATUS_LABELS) as ReservationStatus[]).map((s) => (
                <option key={s} value={s}>
                  {RESERVATION_STATUS_LABELS[s]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Channel">
            <Select
              value={source}
              onChange={(event) => setSource(event.target.value as ReservationSource | "")}
            >
              <option value="">Any channel</option>
              {(Object.keys(SOURCE_LABELS) as ReservationSource[]).map((s) => (
                <option key={s} value={s}>
                  {SOURCE_LABELS[s]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Search" hint="Guest, reference or notes">
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Petrova, HMABC…"
            />
          </Field>
        </div>
      </Card>

      {reservations.error && <ErrorNote message={reservations.error} />}

      <Card padded={false}>
        {reservations.loading && <Spinner />}
        {reservations.data && reservations.data.items.length === 0 && (
          <div className="p-4">
            <EmptyState>No reservations match these filters.</EmptyState>
          </div>
        )}
        {reservations.data && reservations.data.items.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Guest</Th>
                <Th>Property / unit</Th>
                <Th>Stay</Th>
                <Th>Channel</Th>
                <Th>Status</Th>
                <Th className="text-right">Net payout</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {reservations.data.items.map((reservation) => (
                <tr key={reservation.id} className="hover:bg-slate-50">
                  <Td>
                    <span className="font-medium text-slate-900">
                      {reservation.guest_display_name}
                    </span>
                    <span className="block text-xs text-slate-400">
                      {reservation.source_reference ?? "—"}
                    </span>
                  </Td>
                  <Td>
                    {reservation.property_name}
                    <span className="block text-xs text-slate-400">
                      Unit {reservation.unit_name}
                    </span>
                  </Td>
                  <Td className="whitespace-nowrap">
                    {formatDate(reservation.check_in_date)} →{" "}
                    {formatDate(reservation.check_out_date)}
                    <span className="block text-xs text-slate-400">
                      {reservation.nights} night{reservation.nights === 1 ? "" : "s"}
                    </span>
                  </Td>
                  <Td>
                    <SourceTag source={reservation.source} />
                  </Td>
                  <Td>
                    <div className="flex flex-col items-start gap-1">
                      <ReservationStatusBadge status={reservation.status} />
                      <PaymentStatusBadge status={reservation.payment_status} />
                    </div>
                  </Td>
                  <Td className="text-right font-medium tabular-nums">
                    {formatMoney(reservation.net_payout_amount, reservation.currency)}
                  </Td>
                  <Td className="text-right">
                    <Link
                      href={`/reservations/${reservation.id}`}
                      className="text-sm text-slate-600 underline hover:text-slate-900"
                    >
                      Open
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {reservations.data && (
        <p className="mt-2 text-xs text-slate-500">
          Showing {reservations.data.items.length} of {reservations.data.total}.
        </p>
      )}

      {showForm && (
        <Modal title="New reservation" wide onClose={() => setShowForm(false)}>
          <ReservationForm
            onCancel={() => setShowForm(false)}
            onCreated={() => {
              setShowForm(false);
              reservations.reload();
            }}
          />
        </Modal>
      )}
    </>
  );
}

"use client";

import { useEffect, useState } from "react";

import { CalendarGrid, SourceLegend } from "@/components/CalendarGrid";
import { ReservationSidePanel } from "@/components/ReservationSidePanel";
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  PageHeader,
  Select,
  Spinner,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import { MONTH_NAMES, parseIsoDate } from "@/lib/format";
import { useAsync } from "@/lib/use-async";

export default function CalendarPage() {
  const { properties, propertyId, setPropertyId, date } = useApp();
  const initial = parseIsoDate(date);

  const [year, setYear] = useState(initial.getFullYear());
  const [month, setMonth] = useState(initial.getMonth() + 1);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // The calendar is per-property; fall back to the first one.
  const activePropertyId = propertyId ?? properties[0]?.id;

  useEffect(() => {
    const parsed = parseIsoDate(date);
    setYear(parsed.getFullYear());
    setMonth(parsed.getMonth() + 1);
  }, [date]);

  const calendar = useAsync(async () => {
    if (!activePropertyId) return null;
    return api.reservations.calendar(activePropertyId, year, month);
  }, [activePropertyId, year, month]);

  function shiftMonth(delta: number) {
    const next = new Date(year, month - 1 + delta, 1);
    setYear(next.getFullYear());
    setMonth(next.getMonth() + 1);
  }

  return (
    <>
      <PageHeader
        title="Calendar"
        description="One row per unit. Blocks are coloured by booking channel."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Select
              aria-label="Property"
              className="w-44"
              value={activePropertyId ?? ""}
              onChange={(event) => setPropertyId(Number(event.target.value))}
            >
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </Select>
            <Button size="sm" onClick={() => shiftMonth(-1)} aria-label="Previous month">
              ←
            </Button>
            <Select
              aria-label="Month"
              className="w-32"
              value={month}
              onChange={(event) => setMonth(Number(event.target.value))}
            >
              {MONTH_NAMES.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Year"
              className="w-24"
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
            >
              {Array.from({ length: 5 }, (_, i) => initial.getFullYear() - 2 + i).map(
                (value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ),
              )}
            </Select>
            <Button size="sm" onClick={() => shiftMonth(1)} aria-label="Next month">
              →
            </Button>
          </div>
        }
      />

      <div className="mb-3">
        <SourceLegend />
      </div>

      {calendar.error && <ErrorNote message={calendar.error} />}

      <Card padded={false}>
        {calendar.loading && <Spinner />}
        {!calendar.loading && !activePropertyId && (
          <div className="p-4">
            <EmptyState>Create a property first to see its calendar.</EmptyState>
          </div>
        )}
        {calendar.data && (
          <CalendarGrid
            calendar={calendar.data}
            selectedReservationId={selectedId}
            onSelect={(block) => setSelectedId(block.reservation_id)}
          />
        )}
      </Card>

      {selectedId !== null && (
        <ReservationSidePanel
          reservationId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={() => calendar.reload()}
        />
      )}
    </>
  );
}

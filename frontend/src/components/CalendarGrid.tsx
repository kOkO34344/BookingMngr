"use client";

import { HousekeepingBadge } from "@/components/badges";
import { SOURCE_BLOCK_CLASSES, SOURCE_LABELS } from "@/lib/format";
import type { CalendarBlock, CalendarResponse } from "@/lib/types";

import { cx } from "./ui";

const UNIT_COL = "8rem";
const DAY_COL = "2.25rem";

/**
 * Rows = units, columns = days of the month.
 * Blocks are grid items placed explicitly over the day cells, so a stay spans
 * its nights in one continuous bar.
 */
export function CalendarGrid({
  calendar,
  onSelect,
  selectedReservationId,
}: {
  calendar: CalendarResponse;
  onSelect: (block: CalendarBlock) => void;
  selectedReservationId?: number | null;
}) {
  const days = Array.from({ length: calendar.days_in_month }, (_, i) => i + 1);
  const template = `${UNIT_COL} repeat(${calendar.days_in_month}, minmax(${DAY_COL}, 1fr))`;
  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === calendar.year && today.getMonth() + 1 === calendar.month;

  return (
    <div className="scroll-thin overflow-x-auto">
      <div className="min-w-max">
        {/* Header */}
        <div
          className="grid border-b border-slate-200 bg-slate-50"
          style={{ gridTemplateColumns: template }}
        >
          <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Unit
          </div>
          {days.map((day) => {
            const date = new Date(calendar.year, calendar.month - 1, day);
            const weekend = date.getDay() === 0 || date.getDay() === 6;
            const isToday = isCurrentMonth && today.getDate() === day;
            return (
              <div
                key={day}
                className={cx(
                  "border-l border-slate-200 py-1 text-center text-[11px] leading-tight",
                  weekend ? "bg-slate-100 text-slate-500" : "text-slate-600",
                  isToday && "bg-sky-100 font-semibold text-sky-800",
                )}
              >
                <div>{day}</div>
                <div className="text-[9px] uppercase">
                  {date.toLocaleDateString(undefined, { weekday: "narrow" })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Rows */}
        {calendar.units.map((row) => (
          <div
            key={row.unit_id}
            className="grid border-b border-slate-100"
            style={{ gridTemplateColumns: template }}
          >
            {/* Explicitly placed: every other item in this grid is pinned to row
                1, so an auto-placed label gets pushed onto a second implicit
                row and the unit name drifts below its own bookings. */}
            <div
              className="flex items-center justify-between gap-1 px-3 py-1.5"
              style={{ gridRow: 1, gridColumn: 1 }}
            >
              <span className="truncate text-sm font-medium text-slate-800">
                {row.unit_name}
              </span>
              <HousekeepingBadge status={row.housekeeping_status} />
            </div>

            {days.map((day) => {
              const date = new Date(calendar.year, calendar.month - 1, day);
              const weekend = date.getDay() === 0 || date.getDay() === 6;
              return (
                <div
                  key={day}
                  className={cx(
                    "h-9 border-l border-slate-100",
                    weekend && "bg-slate-50",
                  )}
                  // Column pinned as well: blocks occupy cells in this same row,
                  // and auto-placement would otherwise shuffle the background
                  // cells past them.
                  style={{ gridRow: 1, gridColumn: day + 1 }}
                />
              );
            })}

            {row.blocks.map((block) => (
              <button
                key={block.reservation_id}
                type="button"
                onClick={() => onSelect(block)}
                title={`${block.guest_name} · ${SOURCE_LABELS[block.source]} · ${block.check_in_date} → ${block.check_out_date}`}
                className={cx(
                  "my-1 flex items-center overflow-hidden rounded px-1.5 text-[11px] font-medium",
                  SOURCE_BLOCK_CLASSES[block.source],
                  block.status === "canceled" && "opacity-50 line-through",
                  block.continues_before && "rounded-l-none",
                  block.continues_after && "rounded-r-none",
                  selectedReservationId === block.reservation_id &&
                    "ring-2 ring-slate-900 ring-offset-1",
                )}
                style={{
                  gridRow: 1,
                  gridColumn: `${block.start_offset + 2} / span ${block.span_days}`,
                }}
              >
                <span className="truncate">{block.guest_name}</span>
              </button>
            ))}
          </div>
        ))}

        {calendar.units.length === 0 && (
          <p className="px-3 py-6 text-sm text-slate-500">
            This property has no units yet.
          </p>
        )}
      </div>
    </div>
  );
}

export function SourceLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {(Object.keys(SOURCE_LABELS) as (keyof typeof SOURCE_LABELS)[]).map((source) => (
        <span key={source} className="inline-flex items-center gap-1.5 text-xs text-slate-600">
          <span
            className={cx("h-3 w-3 rounded-sm", SOURCE_BLOCK_CLASSES[source])}
            aria-hidden
          />
          {SOURCE_LABELS[source]}
        </span>
      ))}
    </div>
  );
}

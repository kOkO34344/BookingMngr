"use client";

import Link from "next/link";
import { useMemo } from "react";

import { ReservationStatusBadge, SourceTag, TaskStatusBadge } from "@/components/badges";
import {
  Card,
  EmptyState,
  ErrorNote,
  Kpi,
  PageHeader,
  Spinner,
  cx,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import { formatDate, formatMoney, parseIsoDate, TASK_TYPE_LABELS } from "@/lib/format";
import type { PropertyBoard, Reservation, Task, TaskStatus } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

const TASK_COLUMNS: TaskStatus[] = ["scheduled", "in_progress", "completed"];

export default function DashboardPage() {
  const { date, propertyId } = useApp();
  const month = useMemo(() => parseIsoDate(date), [date]);

  const board = useAsync(
    () => api.reports.dailyBoard(date, propertyId),
    [date, propertyId],
  );
  const revenue = useAsync(
    () => api.reports.monthlyRevenue(month.getFullYear(), month.getMonth() + 1, propertyId),
    [month.getFullYear(), month.getMonth(), propertyId],
  );

  const totals = board.data?.totals;

  return (
    <>
      <PageHeader
        title="Morning overview"
        description="Arrivals, departures and the work that has to happen today."
      />

      {board.error && <ErrorNote message={board.error} />}
      {board.loading && !board.data && <Spinner />}

      {totals && (
        <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Kpi
            label="Occupancy"
            value={`${totals.occupancy_pct}%`}
            hint={`${totals.occupied_units} of ${totals.total_units} units`}
          />
          <Kpi label="Arrivals" value={totals.arrivals_count} hint="checking in today" />
          <Kpi
            label="Departures"
            value={totals.departures_count}
            hint="checking out today"
          />
          <Kpi
            label="Tasks done"
            value={`${totals.tasks_completed}/${totals.tasks_total}`}
            hint={`${totals.units_dirty} unit(s) dirty`}
          />
          <Kpi
            label="Revenue MTD"
            value={formatMoney(
              revenue.data?.total_net_payout_amount ?? null,
              revenue.data?.currency,
            )}
            hint="net payout, checked-out stays"
          />
        </div>
      )}

      <div className="space-y-6">
        {board.data?.properties.map((propertyBoard) => (
          <PropertySection key={propertyBoard.property_id} board={propertyBoard} />
        ))}
        {board.data && board.data.properties.length === 0 && (
          <EmptyState>
            No properties yet.{" "}
            <Link href="/properties" className="underline">
              Add your first property
            </Link>
            .
          </EmptyState>
        )}
      </div>
    </>
  );
}

function PropertySection({ board }: { board: PropertyBoard }) {
  return (
    <section>
      <div className="mb-3 flex flex-wrap items-baseline gap-3">
        <h2 className="text-base font-semibold text-slate-900">{board.property_name}</h2>
        <span className="text-xs text-slate-500">
          {board.kpis.occupancy_pct}% occupied · {board.kpis.in_house_count} in house ·{" "}
          {board.kpis.tasks_open} open task(s)
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={`Arrivals (${board.arrivals.length})`}>
          <ReservationList items={board.arrivals} emptyLabel="No arrivals today." />
        </Card>
        <Card title={`Departures (${board.departures.length})`}>
          <ReservationList items={board.departures} emptyLabel="No departures today." />
        </Card>
        <Card title={`In house (${board.in_house.length})`}>
          <ReservationList items={board.in_house} emptyLabel="Nobody staying over." />
        </Card>
      </div>

      <Card title="Today's tasks" className="mt-4">
        <div className="grid gap-4 md:grid-cols-3">
          {TASK_COLUMNS.map((status) => {
            const tasks = board.tasks.filter((task) => task.status === status);
            return (
              <div key={status}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {status.replace("_", " ")} ({tasks.length})
                </p>
                <div className="space-y-2">
                  {tasks.map((task) => (
                    <TaskLine key={task.id} task={task} />
                  ))}
                  {tasks.length === 0 && (
                    <p className="text-xs text-slate-400">Nothing here.</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </section>
  );
}

function ReservationList({
  items,
  emptyLabel,
}: {
  items: Reservation[];
  emptyLabel: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-400">{emptyLabel}</p>;
  }
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((reservation) => (
        <li key={reservation.id} className="flex items-center gap-3 py-2 first:pt-0">
          <span className="w-14 shrink-0 text-sm font-medium text-slate-900">
            {reservation.unit_name}
          </span>
          <div className="min-w-0 flex-1">
            <Link
              href={`/reservations/${reservation.id}`}
              className="block truncate text-sm text-slate-800 hover:underline"
            >
              {reservation.guest_display_name}
            </Link>
            <div className="mt-0.5 flex items-center gap-2">
              <SourceTag source={reservation.source} />
              <span className="text-xs text-slate-400">
                {formatDate(reservation.check_in_date)} →{" "}
                {formatDate(reservation.check_out_date)}
              </span>
            </div>
          </div>
          <ReservationStatusBadge status={reservation.status} />
        </li>
      ))}
    </ul>
  );
}

function TaskLine({ task }: { task: Task }) {
  return (
    <div
      className={cx(
        "rounded-lg border border-slate-200 p-2.5",
        task.status === "completed" && "opacity-60",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-slate-800">
          {task.unit_name ?? "Common area"} · {TASK_TYPE_LABELS[task.task_type]}
        </p>
        <TaskStatusBadge status={task.status} />
      </div>
      {task.description && (
        <p className="mt-1 line-clamp-2 text-xs text-slate-500">{task.description}</p>
      )}
      {task.assigned_to && (
        <p className="mt-1 text-xs text-slate-400">Assigned to {task.assigned_to}</p>
      )}
    </div>
  );
}

"use client";

import {
  HOUSEKEEPING_CLASSES,
  HOUSEKEEPING_LABELS,
  PAYMENT_STATUS_LABELS,
  RESERVATION_STATUS_CLASSES,
  RESERVATION_STATUS_LABELS,
  SOURCE_DOT_CLASSES,
  SOURCE_LABELS,
  TASK_PRIORITY_CLASSES,
  TASK_PRIORITY_LABELS,
  TASK_STATUS_CLASSES,
  TASK_STATUS_LABELS,
} from "@/lib/format";
import type {
  HousekeepingStatus,
  PaymentStatus,
  ReservationSource,
  ReservationStatus,
  TaskPriority,
  TaskStatus,
} from "@/lib/types";

import { Badge } from "./ui";

export function SourceTag({ source }: { source: ReservationSource }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium text-slate-700">
      <span className={`h-2 w-2 shrink-0 rounded-full ${SOURCE_DOT_CLASSES[source]}`} />
      {SOURCE_LABELS[source]}
    </span>
  );
}

export function ReservationStatusBadge({ status }: { status: ReservationStatus }) {
  return (
    <Badge className={RESERVATION_STATUS_CLASSES[status]}>
      {RESERVATION_STATUS_LABELS[status]}
    </Badge>
  );
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return <Badge className={TASK_STATUS_CLASSES[status]}>{TASK_STATUS_LABELS[status]}</Badge>;
}

export function PriorityBadge({ priority }: { priority: TaskPriority }) {
  return (
    <Badge className={TASK_PRIORITY_CLASSES[priority]}>
      {TASK_PRIORITY_LABELS[priority]}
    </Badge>
  );
}

export function HousekeepingBadge({ status }: { status: HousekeepingStatus }) {
  return <Badge className={HOUSEKEEPING_CLASSES[status]}>{HOUSEKEEPING_LABELS[status]}</Badge>;
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const classes: Record<PaymentStatus, string> = {
    pending: "bg-amber-100 text-amber-800",
    paid: "bg-emerald-100 text-emerald-800",
    partially_paid: "bg-sky-100 text-sky-800",
    refunded: "bg-slate-200 text-slate-700",
  };
  return <Badge className={classes[status]}>{PAYMENT_STATUS_LABELS[status]}</Badge>;
}

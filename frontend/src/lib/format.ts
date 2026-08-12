import type {
  HousekeepingStatus,
  PaymentMethod,
  PaymentStatus,
  ReservationSource,
  ReservationStatus,
  TaskPriority,
  TaskStatus,
  TaskType,
} from "./types";

/** Local YYYY-MM-DD (never UTC — a "day" here is the property's day). */
export function toIsoDate(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function todayIso(): string {
  return toIsoDate(new Date());
}

export function parseIsoDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function formatDate(iso: string | null, opts?: Intl.DateTimeFormatOptions): string {
  if (!iso) return "—";
  return parseIsoDate(iso.slice(0, 10)).toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    ...opts,
  });
}

export function formatDateLong(iso: string): string {
  return parseIsoDate(iso.slice(0, 10)).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function formatMoney(amount: string | number | null, currency = "EUR"): string {
  if (amount === null || amount === undefined) return "—";
  const value = typeof amount === "string" ? Number(amount) : amount;
  if (Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function addDays(iso: string, days: number): string {
  const date = parseIsoDate(iso);
  date.setDate(date.getDate() + days);
  return toIsoDate(date);
}

export const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

// --- Labels ---------------------------------------------------------------

export const SOURCE_LABELS: Record<ReservationSource, string> = {
  airbnb: "Airbnb",
  booking: "Booking.com",
  phone: "Phone",
  whatsapp: "WhatsApp",
  email: "Email",
};

export const RESERVATION_STATUS_LABELS: Record<ReservationStatus, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  in_house: "In house",
  checked_out: "Checked out",
  canceled: "Canceled",
  no_show: "No show",
};

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: "Pending",
  paid: "Paid",
  partially_paid: "Partially paid",
  refunded: "Refunded",
};

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  airbnb_payout: "Airbnb payout",
  booking_payout: "Booking.com payout",
  cash: "Cash",
  bank_transfer: "Bank transfer",
  card: "Card",
};

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  housekeeping_checkout_clean: "Checkout clean",
  housekeeping_stayover_clean: "Stayover clean",
  maintenance_issue: "Maintenance",
  inspection: "Inspection",
  other: "Other",
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  scheduled: "Scheduled",
  in_progress: "In progress",
  completed: "Completed",
  canceled: "Canceled",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

export const HOUSEKEEPING_LABELS: Record<HousekeepingStatus, string> = {
  dirty: "Dirty",
  cleaning: "Cleaning",
  clean: "Clean",
  maintenance: "Maintenance",
};

// --- Colours ---------------------------------------------------------------

/** Solid block colours for the calendar, keyed by channel. */
export const SOURCE_BLOCK_CLASSES: Record<ReservationSource, string> = {
  airbnb: "bg-[#e0565b] text-white",
  booking: "bg-[#2f6fd0] text-white",
  phone: "bg-[#0f9d76] text-white",
  whatsapp: "bg-[#16a34a] text-white",
  email: "bg-[#7c5cd6] text-white",
};

export const SOURCE_DOT_CLASSES: Record<ReservationSource, string> = {
  airbnb: "bg-[#e0565b]",
  booking: "bg-[#2f6fd0]",
  phone: "bg-[#0f9d76]",
  whatsapp: "bg-[#16a34a]",
  email: "bg-[#7c5cd6]",
};

export const RESERVATION_STATUS_CLASSES: Record<ReservationStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  confirmed: "bg-sky-100 text-sky-800",
  in_house: "bg-emerald-100 text-emerald-800",
  checked_out: "bg-slate-200 text-slate-700",
  canceled: "bg-rose-100 text-rose-700",
  no_show: "bg-rose-100 text-rose-700",
};

export const TASK_STATUS_CLASSES: Record<TaskStatus, string> = {
  scheduled: "bg-slate-200 text-slate-700",
  in_progress: "bg-sky-100 text-sky-800",
  completed: "bg-emerald-100 text-emerald-800",
  canceled: "bg-rose-100 text-rose-700",
};

export const TASK_PRIORITY_CLASSES: Record<TaskPriority, string> = {
  low: "bg-slate-100 text-slate-600",
  normal: "bg-slate-100 text-slate-700",
  high: "bg-amber-100 text-amber-800",
  urgent: "bg-rose-100 text-rose-800",
};

export const HOUSEKEEPING_CLASSES: Record<HousekeepingStatus, string> = {
  dirty: "bg-rose-100 text-rose-800",
  cleaning: "bg-amber-100 text-amber-800",
  clean: "bg-emerald-100 text-emerald-800",
  maintenance: "bg-slate-300 text-slate-800",
};

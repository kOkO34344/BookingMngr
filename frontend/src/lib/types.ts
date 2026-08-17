/**
 * Mirrors the Pydantic schemas in backend/app/schemas.
 * Keep in sync manually for now; generating from
 * /api/v1/openapi.json is the natural next step.
 */

export type PropertyType = "hotel" | "apartment_building" | "mixed";
export type UnitStatus = "active" | "inactive" | "out_of_service";
export type HousekeepingStatus = "dirty" | "cleaning" | "clean" | "maintenance";

export type ReservationSource =
  | "airbnb"
  | "booking"
  | "phone"
  | "whatsapp"
  | "email";

export type ReservationStatus =
  | "pending"
  | "confirmed"
  | "in_house"
  | "checked_out"
  | "canceled"
  | "no_show";

export type PaymentMethod =
  | "airbnb_payout"
  | "booking_payout"
  | "cash"
  | "bank_transfer"
  | "card";

export type PaymentStatus = "pending" | "paid" | "partially_paid" | "refunded";

export type TaskType =
  | "housekeeping_checkout_clean"
  | "housekeeping_stayover_clean"
  | "maintenance_issue"
  | "inspection"
  | "other";

export type TaskStatus = "scheduled" | "in_progress" | "completed" | "canceled";
export type TaskPriority = "low" | "normal" | "high" | "urgent";

export interface Property {
  id: number;
  organization_id: number;
  name: string;
  type: PropertyType;
  address: string | null;
  city: string | null;
  country: string | null;
  timezone: string;
  notes: string | null;
  is_archived: boolean;
  units_count: number;
  created_at: string;
  updated_at: string;
}

export interface Unit {
  id: number;
  property_id: number;
  name_or_number: string;
  unit_type: string | null;
  capacity: number;
  base_price: string | null;
  cleaning_duration_minutes: number;
  status: UnitStatus;
  housekeeping_status: HousekeepingStatus;
  floor: string | null;
  notes: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Guest {
  id: number;
  organization_id: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  notes: string | null;
}

export interface Reservation {
  id: number;
  property_id: number;
  unit_id: number;
  guest_id: number | null;
  guest_name: string | null;
  check_in_date: string;
  check_out_date: string;
  nights: number;
  number_of_guests: number;
  source: ReservationSource;
  source_reference: string | null;
  status: ReservationStatus;
  gross_amount: string;
  fees_amount: string;
  net_payout_amount: string;
  currency: string;
  payment_method: PaymentMethod | null;
  payment_status: PaymentStatus;
  payout_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  property_name: string | null;
  unit_name: string | null;
  guest_display_name: string | null;
}

export interface Task {
  id: number;
  property_id: number;
  unit_id: number | null;
  reservation_id: number | null;
  task_type: TaskType;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to: string | null;
  estimated_duration_minutes: number | null;
  due_date: string | null;
  completed_at: string | null;
  description: string | null;
  changes_room_status_to: HousekeepingStatus | null;
  property_name: string | null;
  unit_name: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CalendarBlock {
  reservation_id: number;
  unit_id: number;
  guest_name: string;
  source: ReservationSource;
  status: ReservationStatus;
  check_in_date: string;
  check_out_date: string;
  nights: number;
  start_offset: number;
  span_days: number;
  continues_before: boolean;
  continues_after: boolean;
}

export interface CalendarUnitRow {
  unit_id: number;
  unit_name: string;
  housekeeping_status: HousekeepingStatus;
  blocks: CalendarBlock[];
}

export interface CalendarResponse {
  property_id: number;
  year: number;
  month: number;
  days_in_month: number;
  first_day: string;
  units: CalendarUnitRow[];
}

export interface DailyBoardKpis {
  total_units: number;
  occupied_units: number;
  occupancy_pct: number;
  arrivals_count: number;
  departures_count: number;
  in_house_count: number;
  tasks_total: number;
  tasks_completed: number;
  tasks_open: number;
  units_dirty: number;
}

export interface PropertyBoard {
  property_id: number;
  property_name: string;
  arrivals: Reservation[];
  departures: Reservation[];
  in_house: Reservation[];
  tasks: Task[];
  kpis: DailyBoardKpis;
}

export interface DailyBoardResponse {
  date: string;
  properties: PropertyBoard[];
  totals: DailyBoardKpis;
  /** Net payout for stays checked out between the 1st and `date`. */
  net_payout_mtd: string;
  currency: string;
}

export interface RevenueBySource {
  source: ReservationSource;
  reservations_count: number;
  nights: number;
  gross_amount: string;
  fees_amount: string;
  net_payout_amount: string;
}

export interface PropertyRevenue {
  property_id: number;
  property_name: string;
  currency: string;
  nights: number;
  reservations_count: number;
  gross_amount: string;
  fees_amount: string;
  net_payout_amount: string;
  by_source: RevenueBySource[];
  reservations: Reservation[];
}

export interface MonthlyRevenueResponse {
  year: number;
  month: number;
  period_start: string;
  period_end: string;
  currency: string;
  properties: PropertyRevenue[];
  total_gross_amount: string;
  total_fees_amount: string;
  total_net_payout_amount: string;
  total_nights: number;
  by_source: RevenueBySource[];
}

export interface GenerateHousekeepingResponse {
  date: string;
  created: Task[];
  skipped_existing: number;
  units_marked_dirty: number[];
}

export interface CurrentUser {
  id: number;
  organization_id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

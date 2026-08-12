/**
 * Typed API client. One place that knows about URLs, auth headers and errors.
 */

import type {
  CalendarResponse,
  CurrentUser,
  DailyBoardResponse,
  GenerateHousekeepingResponse,
  Guest,
  MonthlyRevenueResponse,
  Page,
  Property,
  Reservation,
  ReservationSource,
  ReservationStatus,
  Task,
  TaskStatus,
  TaskType,
  Unit,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "bookingmngr.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}

type QueryValue = string | number | boolean | null | undefined;

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(
  path: string,
  options: RequestInit & { params?: Record<string, QueryValue> } = {},
): Promise<T> {
  const { params, ...init } = options;
  const token = getToken();

  const response = await fetch(buildUrl(path, params), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors.
        detail = body.detail
          .map((e: { loc?: string[]; msg: string }) =>
            `${e.loc?.slice(1).join(".") ?? ""} ${e.msg}`.trim(),
          )
          .join("; ");
      }
    } catch {
      /* body was not JSON — keep the generic message */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const get = <T,>(path: string, params?: Record<string, QueryValue>) =>
  request<T>(path, { method: "GET", params });

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

const patch = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });

const del = <T,>(path: string, params?: Record<string, QueryValue>) =>
  request<T>(path, { method: "DELETE", params });

// --- Endpoints -------------------------------------------------------------

export const api = {
  auth: {
    login: (username: string, password: string) =>
      post<{ access_token: string; token_type: string; expires_in: number }>(
        "/auth/login",
        { username, password },
      ),
    me: () => get<CurrentUser>("/auth/me"),
  },

  properties: {
    list: (includeArchived = false) =>
      get<Property[]>("/properties", { include_archived: includeArchived }),
    create: (body: Partial<Property>) => post<Property>("/properties", body),
    get: (id: number) => get<Property>(`/properties/${id}`),
    update: (id: number, body: Partial<Property>) =>
      patch<Property>(`/properties/${id}`, body),
    archive: (id: number) => del<{ detail: string }>(`/properties/${id}`),
  },

  units: {
    listForProperty: (propertyId: number, includeArchived = false) =>
      get<Unit[]>(`/properties/${propertyId}/units`, {
        include_archived: includeArchived,
      }),
    create: (propertyId: number, body: Partial<Unit>) =>
      post<Unit>(`/properties/${propertyId}/units`, body),
    get: (id: number) => get<Unit>(`/units/${id}`),
    update: (id: number, body: Partial<Unit>) => patch<Unit>(`/units/${id}`, body),
    archive: (id: number) => del<{ detail: string }>(`/units/${id}`),
  },

  guests: {
    list: (search?: string) => get<Guest[]>("/guests", { search }),
    create: (body: Partial<Guest>) => post<Guest>("/guests", body),
    get: (id: number) => get<Guest>(`/guests/${id}`),
    update: (id: number, body: Partial<Guest>) => patch<Guest>(`/guests/${id}`, body),
  },

  reservations: {
    list: (params: {
      property_id?: number;
      unit_id?: number;
      from_date?: string;
      to_date?: string;
      status?: ReservationStatus;
      source?: ReservationSource;
      search?: string;
      limit?: number;
      offset?: number;
    }) => get<Page<Reservation>>("/reservations", params),
    create: (body: Record<string, unknown>) => post<Reservation>("/reservations", body),
    get: (id: number) => get<Reservation>(`/reservations/${id}`),
    update: (id: number, body: Record<string, unknown>) =>
      patch<Reservation>(`/reservations/${id}`, body),
    remove: (id: number) => del<{ detail: string }>(`/reservations/${id}`),
    daily: (date: string, propertyId?: number) =>
      get<{
        date: string;
        arrivals: Reservation[];
        departures: Reservation[];
        in_house: Reservation[];
      }>("/reservations/daily", { date, property_id: propertyId }),
    calendar: (propertyId: number, year: number, month: number) =>
      get<CalendarResponse>("/reservations/calendar", {
        property_id: propertyId,
        year,
        month,
      }),
  },

  tasks: {
    list: (params: {
      date?: string;
      from_date?: string;
      to_date?: string;
      property_id?: number;
      unit_id?: number;
      status?: TaskStatus;
      task_type?: TaskType;
      assigned_to?: string;
      limit?: number;
    }) => get<Page<Task>>("/tasks", params),
    create: (body: Record<string, unknown>) => post<Task>("/tasks", body),
    get: (id: number) => get<Task>(`/tasks/${id}`),
    update: (id: number, body: Record<string, unknown>) =>
      patch<Task>(`/tasks/${id}`, body),
    remove: (id: number) => del<{ detail: string }>(`/tasks/${id}`),
    generateHousekeeping: (body: {
      date: string;
      property_id?: number;
      assigned_to?: string;
      include_stayovers?: boolean;
    }) => post<GenerateHousekeepingResponse>("/tasks/generate-housekeeping", body),
  },

  reports: {
    dailyBoard: (date: string, propertyId?: number) =>
      get<DailyBoardResponse>("/reports/daily-board", {
        date,
        property_id: propertyId,
      }),
    monthlyRevenue: (year: number, month: number, propertyId?: number) =>
      get<MonthlyRevenueResponse>("/reports/monthly-revenue", {
        year,
        month,
        property_id: propertyId,
      }),
  },
};

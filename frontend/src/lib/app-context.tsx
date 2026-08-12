"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "./api";
import { todayIso } from "./format";
import type { Property } from "./types";

const PROPERTY_KEY = "bookingmngr.propertyId";

interface AppState {
  properties: Property[];
  propertiesLoading: boolean;
  /** undefined = "All properties". */
  propertyId: number | undefined;
  setPropertyId: (id: number | undefined) => void;
  /** The working date shared by the dashboard and the task board. */
  date: string;
  setDate: (iso: string) => void;
  refreshProperties: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [propertiesLoading, setPropertiesLoading] = useState(true);
  const [propertyId, setPropertyIdState] = useState<number | undefined>(undefined);
  const [date, setDate] = useState<string>(todayIso());

  const refreshProperties = useCallback(async () => {
    setPropertiesLoading(true);
    try {
      setProperties(await api.properties.list());
    } finally {
      setPropertiesLoading(false);
    }
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem(PROPERTY_KEY);
    if (stored) setPropertyIdState(Number(stored));
    void refreshProperties();
  }, [refreshProperties]);

  const setPropertyId = useCallback((id: number | undefined) => {
    setPropertyIdState(id);
    if (id === undefined) window.localStorage.removeItem(PROPERTY_KEY);
    else window.localStorage.setItem(PROPERTY_KEY, String(id));
  }, []);

  const value = useMemo(
    () => ({
      properties,
      propertiesLoading,
      propertyId,
      setPropertyId,
      date,
      setDate,
      refreshProperties,
    }),
    [properties, propertiesLoading, propertyId, setPropertyId, date, refreshProperties],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside <AppProvider>");
  return context;
}

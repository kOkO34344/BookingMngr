"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { HousekeepingBadge } from "@/components/badges";
import {
  Button,
  Card,
  ErrorNote,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { HOUSEKEEPING_LABELS } from "@/lib/format";
import type { HousekeepingStatus, UnitStatus } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

const UNIT_STATUS_LABELS: Record<UnitStatus, string> = {
  active: "Active",
  inactive: "Inactive",
  out_of_service: "Out of service",
};

export default function UnitDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const unitId = Number(params.id);

  const unit = useAsync(() => api.units.get(unitId), [unitId]);

  const [form, setForm] = useState({
    name_or_number: "",
    unit_type: "",
    capacity: "2",
    base_price: "",
    cleaning_duration_minutes: "60",
    status: "active" as UnitStatus,
    housekeeping_status: "clean" as HousekeepingStatus,
    floor: "",
    notes: "",
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const data = unit.data;
    if (!data) return;
    setForm({
      name_or_number: data.name_or_number,
      unit_type: data.unit_type ?? "",
      capacity: String(data.capacity),
      base_price: data.base_price ?? "",
      cleaning_duration_minutes: String(data.cleaning_duration_minutes),
      status: data.status,
      housekeeping_status: data.housekeeping_status,
      floor: data.floor ?? "",
      notes: data.notes ?? "",
    });
  }, [unit.data]);

  async function save() {
    setError(null);
    setSaved(false);
    try {
      await api.units.update(unitId, {
        name_or_number: form.name_or_number,
        unit_type: form.unit_type || null,
        capacity: Number(form.capacity),
        base_price: form.base_price || null,
        cleaning_duration_minutes: Number(form.cleaning_duration_minutes),
        status: form.status,
        housekeeping_status: form.housekeeping_status,
        floor: form.floor || null,
        notes: form.notes || null,
      });
      setSaved(true);
      unit.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  /** Quick action used all day long: mark the room clean or dirty in one click. */
  async function setHousekeeping(status: HousekeepingStatus) {
    setError(null);
    try {
      const updated = await api.units.update(unitId, { housekeeping_status: status });
      unit.setData(updated);
      setForm((current) => ({ ...current, housekeeping_status: status }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update status");
    }
  }

  async function archive() {
    if (!window.confirm("Archive this unit?")) return;
    try {
      await api.units.archive(unitId);
      router.push(`/properties/${unit.data?.property_id ?? ""}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not archive");
    }
  }

  if (unit.loading) return <Spinner />;
  if (unit.error) return <ErrorNote message={unit.error} />;
  if (!unit.data) return null;

  return (
    <>
      <PageHeader
        title={`Unit ${unit.data.name_or_number}`}
        description={unit.data.unit_type ?? undefined}
        action={
          <Link
            href={`/properties/${unit.data.property_id}`}
            className="text-sm text-slate-600 underline"
          >
            Back to property
          </Link>
        }
      />

      {error && <ErrorNote message={error} />}
      {saved && (
        <p className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Saved.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Housekeeping">
          <div className="mb-3 flex items-center gap-2">
            <span className="text-sm text-slate-500">Current:</span>
            <HousekeepingBadge status={unit.data.housekeeping_status} />
          </div>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(HOUSEKEEPING_LABELS) as HousekeepingStatus[]).map((status) => (
              <Button
                key={status}
                size="sm"
                variant={unit.data?.housekeeping_status === status ? "primary" : "secondary"}
                onClick={() => setHousekeeping(status)}
              >
                {HOUSEKEEPING_LABELS[status]}
              </Button>
            ))}
          </div>
        </Card>

        <Card title="Unit details" className="lg:col-span-2">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Name or number">
              <Input
                value={form.name_or_number}
                onChange={(event) =>
                  setForm({ ...form, name_or_number: event.target.value })
                }
              />
            </Field>
            <Field label="Unit type">
              <Input
                value={form.unit_type}
                onChange={(event) => setForm({ ...form, unit_type: event.target.value })}
              />
            </Field>
            <Field label="Capacity">
              <Input
                type="number"
                min={1}
                value={form.capacity}
                onChange={(event) => setForm({ ...form, capacity: event.target.value })}
              />
            </Field>
            <Field label="Base price">
              <Input
                type="number"
                step="0.01"
                value={form.base_price}
                onChange={(event) => setForm({ ...form, base_price: event.target.value })}
              />
            </Field>
            <Field label="Cleaning duration (minutes)">
              <Input
                type="number"
                min={0}
                value={form.cleaning_duration_minutes}
                onChange={(event) =>
                  setForm({ ...form, cleaning_duration_minutes: event.target.value })
                }
              />
            </Field>
            <Field label="Floor">
              <Input
                value={form.floor}
                onChange={(event) => setForm({ ...form, floor: event.target.value })}
              />
            </Field>
            <Field label="Availability status">
              <Select
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as UnitStatus })
                }
              >
                {(Object.keys(UNIT_STATUS_LABELS) as UnitStatus[]).map((status) => (
                  <option key={status} value={status}>
                    {UNIT_STATUS_LABELS[status]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Housekeeping status">
              <Select
                value={form.housekeeping_status}
                onChange={(event) =>
                  setForm({
                    ...form,
                    housekeeping_status: event.target.value as HousekeepingStatus,
                  })
                }
              >
                {(Object.keys(HOUSEKEEPING_LABELS) as HousekeepingStatus[]).map(
                  (status) => (
                    <option key={status} value={status}>
                      {HOUSEKEEPING_LABELS[status]}
                    </option>
                  ),
                )}
              </Select>
            </Field>
          </div>

          <Field label="Notes" className="mt-3">
            <Textarea
              value={form.notes}
              onChange={(event) => setForm({ ...form, notes: event.target.value })}
            />
          </Field>

          <div className="mt-4 flex justify-between">
            <Button variant="danger" onClick={archive}>
              Archive unit
            </Button>
            <Button variant="primary" onClick={save}>
              Save changes
            </Button>
          </div>
        </Card>
      </div>
    </>
  );
}

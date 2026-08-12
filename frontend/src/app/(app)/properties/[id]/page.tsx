"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal";
import { HousekeepingBadge } from "@/components/badges";
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
  Textarea,
  Th,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { PropertyType } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

const TYPE_LABELS: Record<PropertyType, string> = {
  hotel: "Hotel",
  apartment_building: "Apartment building",
  mixed: "Mixed",
};

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const propertyId = Number(params.id);
  const { refreshProperties } = useApp();

  const property = useAsync(() => api.properties.get(propertyId), [propertyId]);
  const units = useAsync(() => api.units.listForProperty(propertyId), [propertyId]);

  const [form, setForm] = useState({
    name: "",
    type: "hotel" as PropertyType,
    address: "",
    city: "",
    country: "",
    timezone: "",
    notes: "",
  });
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUnitForm, setShowUnitForm] = useState(false);

  useEffect(() => {
    const data = property.data;
    if (!data) return;
    setForm({
      name: data.name,
      type: data.type,
      address: data.address ?? "",
      city: data.city ?? "",
      country: data.country ?? "",
      timezone: data.timezone,
      notes: data.notes ?? "",
    });
  }, [property.data]);

  async function save() {
    setError(null);
    setStatus(null);
    try {
      await api.properties.update(propertyId, {
        ...form,
        address: form.address || null,
        city: form.city || null,
        country: form.country || null,
        notes: form.notes || null,
      });
      setStatus("Saved.");
      void refreshProperties();
      property.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  async function archive() {
    if (!window.confirm("Archive this property? It stays in reports and history.")) return;
    try {
      await api.properties.archive(propertyId);
      void refreshProperties();
      router.push("/properties");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not archive");
    }
  }

  if (property.loading) return <Spinner />;
  if (property.error) return <ErrorNote message={property.error} />;

  return (
    <>
      <PageHeader
        title={property.data?.name ?? "Property"}
        description={`${property.data?.units_count ?? 0} unit(s)`}
        action={
          <Link href="/properties" className="text-sm text-slate-600 underline">
            Back to properties
          </Link>
        }
      />

      {error && <ErrorNote message={error} />}
      {status && (
        <p className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {status}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Details">
          <div className="space-y-3">
            <Field label="Name">
              <Input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </Field>
            <Field label="Type">
              <Select
                value={form.type}
                onChange={(event) =>
                  setForm({ ...form, type: event.target.value as PropertyType })
                }
              >
                {(Object.keys(TYPE_LABELS) as PropertyType[]).map((type) => (
                  <option key={type} value={type}>
                    {TYPE_LABELS[type]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Address">
              <Input
                value={form.address}
                onChange={(event) => setForm({ ...form, address: event.target.value })}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="City">
                <Input
                  value={form.city}
                  onChange={(event) => setForm({ ...form, city: event.target.value })}
                />
              </Field>
              <Field label="Country">
                <Input
                  value={form.country}
                  onChange={(event) => setForm({ ...form, country: event.target.value })}
                />
              </Field>
            </div>
            <Field label="Timezone">
              <Input
                value={form.timezone}
                onChange={(event) => setForm({ ...form, timezone: event.target.value })}
              />
            </Field>
            <Field label="Notes">
              <Textarea
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
              />
            </Field>
            <div className="flex justify-between">
              <Button variant="danger" onClick={archive}>
                Archive
              </Button>
              <Button variant="primary" onClick={save}>
                Save
              </Button>
            </div>
          </div>
        </Card>

        <Card
          title="Units"
          className="lg:col-span-2"
          padded={false}
          action={
            <Button size="sm" onClick={() => setShowUnitForm(true)}>
              Add unit
            </Button>
          }
        >
          {units.loading && <Spinner />}
          {units.data && units.data.length === 0 && (
            <div className="p-4">
              <EmptyState>No units yet.</EmptyState>
            </div>
          )}
          {units.data && units.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Unit</Th>
                  <Th>Type</Th>
                  <Th className="text-right">Capacity</Th>
                  <Th className="text-right">Base price</Th>
                  <Th>Housekeeping</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {units.data.map((unit) => (
                  <tr key={unit.id} className="hover:bg-slate-50">
                    <Td>
                      <Link
                        href={`/units/${unit.id}`}
                        className="font-medium text-slate-900 hover:underline"
                      >
                        {unit.name_or_number}
                      </Link>
                      {unit.floor && (
                        <span className="block text-xs text-slate-400">
                          Floor {unit.floor}
                        </span>
                      )}
                    </Td>
                    <Td>{unit.unit_type ?? "—"}</Td>
                    <Td className="text-right tabular-nums">{unit.capacity}</Td>
                    <Td className="text-right tabular-nums">{unit.base_price ?? "—"}</Td>
                    <Td>
                      <HousekeepingBadge status={unit.housekeeping_status} />
                    </Td>
                    <Td className="text-right">
                      <Link
                        href={`/units/${unit.id}`}
                        className="text-sm text-slate-600 underline"
                      >
                        Edit
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>

      {showUnitForm && (
        <Modal title="New unit" onClose={() => setShowUnitForm(false)}>
          <UnitForm
            propertyId={propertyId}
            onCancel={() => setShowUnitForm(false)}
            onCreated={() => {
              setShowUnitForm(false);
              units.reload();
              property.reload();
              void refreshProperties();
            }}
          />
        </Modal>
      )}
    </>
  );
}

function UnitForm({
  propertyId,
  onCreated,
  onCancel,
}: {
  propertyId: number;
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState({
    name_or_number: "",
    unit_type: "",
    capacity: "2",
    base_price: "",
    cleaning_duration_minutes: "60",
    floor: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await api.units.create(propertyId, {
        name_or_number: values.name_or_number,
        unit_type: values.unit_type || null,
        capacity: Number(values.capacity),
        base_price: values.base_price || null,
        cleaning_duration_minutes: Number(values.cleaning_duration_minutes),
        floor: values.floor || null,
        notes: values.notes || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create unit");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      {error && <ErrorNote message={error} />}
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name or number">
          <Input
            value={values.name_or_number}
            onChange={(event) =>
              setValues({ ...values, name_or_number: event.target.value })
            }
            placeholder="101 / Studio A"
            autoFocus
          />
        </Field>
        <Field label="Unit type">
          <Input
            value={values.unit_type}
            onChange={(event) => setValues({ ...values, unit_type: event.target.value })}
            placeholder="Double room"
          />
        </Field>
        <Field label="Capacity">
          <Input
            type="number"
            min={1}
            value={values.capacity}
            onChange={(event) => setValues({ ...values, capacity: event.target.value })}
          />
        </Field>
        <Field label="Base price">
          <Input
            type="number"
            step="0.01"
            value={values.base_price}
            onChange={(event) => setValues({ ...values, base_price: event.target.value })}
          />
        </Field>
        <Field label="Cleaning minutes">
          <Input
            type="number"
            min={0}
            value={values.cleaning_duration_minutes}
            onChange={(event) =>
              setValues({ ...values, cleaning_duration_minutes: event.target.value })
            }
          />
        </Field>
        <Field label="Floor">
          <Input
            value={values.floor}
            onChange={(event) => setValues({ ...values, floor: event.target.value })}
          />
        </Field>
      </div>
      <Field label="Notes">
        <Textarea
          value={values.notes}
          onChange={(event) => setValues({ ...values, notes: event.target.value })}
        />
      </Field>
      <div className="flex justify-end gap-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          variant="primary"
          onClick={submit}
          disabled={submitting || !values.name_or_number}
        >
          {submitting ? "Saving…" : "Create unit"}
        </Button>
      </div>
    </div>
  );
}

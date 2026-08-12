"use client";

import Link from "next/link";
import { useState } from "react";

import { Modal } from "@/components/Modal";
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

const TYPE_LABELS: Record<PropertyType, string> = {
  hotel: "Hotel",
  apartment_building: "Apartment building",
  mixed: "Mixed",
};

export default function PropertiesPage() {
  const { properties, propertiesLoading, refreshProperties } = useApp();
  const [showForm, setShowForm] = useState(false);

  return (
    <>
      <PageHeader
        title="Properties"
        description="Hotels and apartment buildings you manage."
        action={
          <Button variant="primary" onClick={() => setShowForm(true)}>
            Add property
          </Button>
        }
      />

      <Card padded={false}>
        {propertiesLoading && <Spinner />}
        {!propertiesLoading && properties.length === 0 && (
          <div className="p-4">
            <EmptyState>No properties yet. Add the first one to get started.</EmptyState>
          </div>
        )}
        {properties.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Type</Th>
                <Th>Location</Th>
                <Th className="text-right">Units</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {properties.map((property) => (
                <tr key={property.id} className="hover:bg-slate-50">
                  <Td>
                    <Link
                      href={`/properties/${property.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {property.name}
                    </Link>
                  </Td>
                  <Td>{TYPE_LABELS[property.type]}</Td>
                  <Td>
                    {[property.city, property.country].filter(Boolean).join(", ") || "—"}
                  </Td>
                  <Td className="text-right tabular-nums">{property.units_count}</Td>
                  <Td className="text-right">
                    <Link
                      href={`/properties/${property.id}`}
                      className="text-sm text-slate-600 underline"
                    >
                      Manage
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {showForm && (
        <Modal title="New property" onClose={() => setShowForm(false)}>
          <PropertyForm
            onCancel={() => setShowForm(false)}
            onCreated={() => {
              setShowForm(false);
              void refreshProperties();
            }}
          />
        </Modal>
      )}
    </>
  );
}

function PropertyForm({
  onCreated,
  onCancel,
}: {
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState({
    name: "",
    type: "apartment_building" as PropertyType,
    address: "",
    city: "",
    country: "",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await api.properties.create({
        ...values,
        address: values.address || null,
        city: values.city || null,
        country: values.country || null,
        notes: values.notes || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create property");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      {error && <ErrorNote message={error} />}

      <Field label="Name">
        <Input
          value={values.name}
          onChange={(event) => setValues({ ...values, name: event.target.value })}
          placeholder="Seaside Hotel"
          autoFocus
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Type">
          <Select
            value={values.type}
            onChange={(event) =>
              setValues({ ...values, type: event.target.value as PropertyType })
            }
          >
            {(Object.keys(TYPE_LABELS) as PropertyType[]).map((type) => (
              <option key={type} value={type}>
                {TYPE_LABELS[type]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Timezone">
          <Input
            value={values.timezone}
            onChange={(event) => setValues({ ...values, timezone: event.target.value })}
          />
        </Field>
        <Field label="City">
          <Input
            value={values.city}
            onChange={(event) => setValues({ ...values, city: event.target.value })}
          />
        </Field>
        <Field label="Country">
          <Input
            value={values.country}
            onChange={(event) => setValues({ ...values, country: event.target.value })}
          />
        </Field>
      </div>

      <Field label="Address">
        <Input
          value={values.address}
          onChange={(event) => setValues({ ...values, address: event.target.value })}
        />
      </Field>

      <Field label="Notes">
        <Textarea
          value={values.notes}
          onChange={(event) => setValues({ ...values, notes: event.target.value })}
        />
      </Field>

      <div className="flex justify-end gap-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="primary" onClick={submit} disabled={submitting || !values.name}>
          {submitting ? "Saving…" : "Create property"}
        </Button>
      </div>
    </div>
  );
}

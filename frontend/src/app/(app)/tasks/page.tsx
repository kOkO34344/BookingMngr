"use client";

import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal";
import { HousekeepingBadge, PriorityBadge, TaskStatusBadge } from "@/components/badges";
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
  Textarea,
  cx,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import {
  TASK_PRIORITY_LABELS,
  TASK_STATUS_LABELS,
  TASK_TYPE_LABELS,
} from "@/lib/format";
import type {
  HousekeepingStatus,
  Task,
  TaskPriority,
  TaskStatus,
  TaskType,
  Unit,
} from "@/lib/types";
import { useAsync } from "@/lib/use-async";

const BOARD_COLUMNS: TaskStatus[] = ["scheduled", "in_progress", "completed"];

export default function TasksPage() {
  const { date, setDate, propertyId } = useApp();
  const [groupBy, setGroupBy] = useState<"status" | "unit">("status");
  const [typeFilter, setTypeFilter] = useState<TaskType | "">("");
  const [banner, setBanner] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [generating, setGenerating] = useState(false);

  const tasks = useAsync(
    () =>
      api.tasks.list({
        date,
        property_id: propertyId,
        task_type: typeFilter || undefined,
        limit: 500,
      }),
    [date, propertyId, typeFilter],
  );

  async function generateCleans() {
    setGenerating(true);
    setError(null);
    setBanner(null);
    try {
      const result = await api.tasks.generateHousekeeping({
        date,
        property_id: propertyId,
      });
      setBanner(
        `Created ${result.created.length} checkout clean(s); ` +
          `${result.skipped_existing} already existed; ` +
          `${result.units_marked_dirty.length} unit(s) marked dirty.`,
      );
      tasks.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate tasks");
    } finally {
      setGenerating(false);
    }
  }

  async function updateTask(task: Task, changes: Record<string, unknown>) {
    setError(null);
    try {
      await api.tasks.update(task.id, changes);
      tasks.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update task");
    }
  }

  const items = tasks.data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Housekeeping & maintenance"
        description="The day's work board. Completing a clean can flip the unit's status."
        action={
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setShowForm(true)}>New task</Button>
            <Button variant="primary" onClick={generateCleans} disabled={generating}>
              {generating ? "Generating…" : "Generate today's checkout cleans"}
            </Button>
          </div>
        }
      />

      <Card className="mb-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Date">
            <Input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </Field>
          <Field label="Task type">
            <Select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as TaskType | "")}
            >
              <option value="">All types</option>
              {(Object.keys(TASK_TYPE_LABELS) as TaskType[]).map((type) => (
                <option key={type} value={type}>
                  {TASK_TYPE_LABELS[type]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Group by">
            <Select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value as "status" | "unit")}
            >
              <option value="status">Status</option>
              <option value="unit">Unit</option>
            </Select>
          </Field>
        </div>
      </Card>

      {banner && (
        <p className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {banner}
        </p>
      )}
      {error && <ErrorNote message={error} />}
      {tasks.error && <ErrorNote message={tasks.error} />}
      {tasks.loading && <Spinner />}

      {!tasks.loading && items.length === 0 && (
        <EmptyState>
          No tasks for this day. Use “Generate today’s checkout cleans” after the
          departures are known.
        </EmptyState>
      )}

      {items.length > 0 && groupBy === "status" && (
        <div className="grid gap-4 lg:grid-cols-3">
          {BOARD_COLUMNS.map((status) => {
            const column = items.filter((task) => task.status === status);
            return (
              <Card key={status} title={`${TASK_STATUS_LABELS[status]} (${column.length})`}>
                <div className="space-y-2">
                  {column.map((task) => (
                    <TaskCard key={task.id} task={task} onUpdate={updateTask} />
                  ))}
                  {column.length === 0 && (
                    <p className="text-xs text-slate-400">Nothing here.</p>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {items.length > 0 && groupBy === "unit" && (
        <div className="space-y-4">
          {groupByUnit(items).map(([label, group]) => (
            <Card key={label} title={label}>
              <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                {group.map((task) => (
                  <TaskCard key={task.id} task={task} onUpdate={updateTask} />
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {showForm && (
        <Modal title="New task" onClose={() => setShowForm(false)}>
          <TaskForm
            defaultDate={date}
            onCancel={() => setShowForm(false)}
            onCreated={() => {
              setShowForm(false);
              tasks.reload();
            }}
          />
        </Modal>
      )}
    </>
  );
}

function groupByUnit(tasks: Task[]): [string, Task[]][] {
  const groups = new Map<string, Task[]>();
  for (const task of tasks) {
    const key = task.unit_name ? `Unit ${task.unit_name}` : "Common areas";
    groups.set(key, [...(groups.get(key) ?? []), task]);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function TaskCard({
  task,
  onUpdate,
}: {
  task: Task;
  onUpdate: (task: Task, changes: Record<string, unknown>) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [description, setDescription] = useState(task.description ?? "");
  const [assignee, setAssignee] = useState(task.assigned_to ?? "");

  return (
    <div
      className={cx(
        "rounded-lg border border-slate-200 p-3",
        task.status === "completed" && "bg-slate-50 opacity-70",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-slate-900">
            {task.unit_name ? `Unit ${task.unit_name}` : "Common area"}
          </p>
          <p className="text-xs text-slate-500">{TASK_TYPE_LABELS[task.task_type]}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <TaskStatusBadge status={task.status} />
          <PriorityBadge priority={task.priority} />
        </div>
      </div>

      {!editing && task.description && (
        <p className="mt-2 text-sm text-slate-600">{task.description}</p>
      )}

      {editing ? (
        <div className="mt-2 space-y-2">
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description"
          />
          <Input
            value={assignee}
            onChange={(event) => setAssignee(event.target.value)}
            placeholder="Assigned to"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                onUpdate(task, {
                  description: description || null,
                  assigned_to: assignee || null,
                });
                setEditing(false);
              }}
            >
              Save
            </Button>
            <Button size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <p className="mt-2 text-xs text-slate-400">
            {task.assigned_to ? `Assigned to ${task.assigned_to}` : "Unassigned"}
            {task.estimated_duration_minutes
              ? ` · ~${task.estimated_duration_minutes} min`
              : ""}
          </p>
          {task.changes_room_status_to && (
            <p className="mt-1 text-xs text-slate-400">
              On completion sets unit to{" "}
              <HousekeepingBadge status={task.changes_room_status_to} />
            </p>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {task.status !== "completed" && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => onUpdate(task, { status: "completed" })}
              >
                Mark complete
              </Button>
            )}
            {task.status === "scheduled" && (
              <Button size="sm" onClick={() => onUpdate(task, { status: "in_progress" })}>
                Start
              </Button>
            )}
            {task.status === "completed" && (
              <Button size="sm" onClick={() => onUpdate(task, { status: "scheduled" })}>
                Reopen
              </Button>
            )}
            <Button size="sm" onClick={() => setEditing(true)}>
              Edit
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function TaskForm({
  defaultDate,
  onCreated,
  onCancel,
}: {
  defaultDate: string;
  onCreated: () => void;
  onCancel: () => void;
}) {
  const { properties, propertyId } = useApp();
  const [values, setValues] = useState({
    property_id: String(propertyId ?? properties[0]?.id ?? ""),
    unit_id: "",
    task_type: "maintenance_issue" as TaskType,
    priority: "normal" as TaskPriority,
    assigned_to: "",
    due_date: defaultDate,
    estimated_duration_minutes: "",
    description: "",
    changes_room_status_to: "" as HousekeepingStatus | "",
  });
  const [units, setUnits] = useState<Unit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selectedProperty = Number(values.property_id);

  useEffect(() => {
    if (!selectedProperty) return;
    let active = true;
    api.units
      .listForProperty(selectedProperty)
      .then((result) => active && setUnits(result))
      .catch(() => setUnits([]));
    return () => {
      active = false;
    };
  }, [selectedProperty]);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await api.tasks.create({
        property_id: selectedProperty,
        unit_id: values.unit_id ? Number(values.unit_id) : null,
        task_type: values.task_type,
        priority: values.priority,
        assigned_to: values.assigned_to || null,
        due_date: values.due_date || null,
        estimated_duration_minutes: values.estimated_duration_minutes
          ? Number(values.estimated_duration_minutes)
          : null,
        description: values.description || null,
        changes_room_status_to: values.changes_room_status_to || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create task");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      {error && <ErrorNote message={error} />}

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Property">
          <Select
            value={values.property_id}
            onChange={(event) =>
              setValues({ ...values, property_id: event.target.value, unit_id: "" })
            }
          >
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Unit" hint="Leave empty for common areas">
          <Select
            value={values.unit_id}
            onChange={(event) => setValues({ ...values, unit_id: event.target.value })}
          >
            <option value="">Common area</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name_or_number}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Type">
          <Select
            value={values.task_type}
            onChange={(event) =>
              setValues({ ...values, task_type: event.target.value as TaskType })
            }
          >
            {(Object.keys(TASK_TYPE_LABELS) as TaskType[]).map((type) => (
              <option key={type} value={type}>
                {TASK_TYPE_LABELS[type]}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Priority">
          <Select
            value={values.priority}
            onChange={(event) =>
              setValues({ ...values, priority: event.target.value as TaskPriority })
            }
          >
            {(Object.keys(TASK_PRIORITY_LABELS) as TaskPriority[]).map((priority) => (
              <option key={priority} value={priority}>
                {TASK_PRIORITY_LABELS[priority]}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Due date">
          <Input
            type="date"
            value={values.due_date}
            onChange={(event) => setValues({ ...values, due_date: event.target.value })}
          />
        </Field>

        <Field label="Assigned to">
          <Input
            value={values.assigned_to}
            onChange={(event) => setValues({ ...values, assigned_to: event.target.value })}
            placeholder="Worker or manager name"
          />
        </Field>

        <Field label="Estimated minutes">
          <Input
            type="number"
            min={0}
            value={values.estimated_duration_minutes}
            onChange={(event) =>
              setValues({ ...values, estimated_duration_minutes: event.target.value })
            }
          />
        </Field>

        <Field label="On completion set unit to">
          <Select
            value={values.changes_room_status_to}
            onChange={(event) =>
              setValues({
                ...values,
                changes_room_status_to: event.target.value as HousekeepingStatus | "",
              })
            }
          >
            <option value="">Leave unchanged</option>
            <option value="clean">Clean</option>
            <option value="dirty">Dirty</option>
            <option value="maintenance">Maintenance</option>
          </Select>
        </Field>
      </div>

      <Field label="Description">
        <Textarea
          value={values.description}
          onChange={(event) => setValues({ ...values, description: event.target.value })}
        />
      </Field>

      <div className="flex justify-end gap-2">
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="primary" onClick={submit} disabled={submitting}>
          {submitting ? "Saving…" : "Create task"}
        </Button>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";

import { SourceTag } from "@/components/badges";
import {
  Card,
  EmptyState,
  ErrorNote,
  Field,
  Kpi,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import { formatDate, formatMoney, MONTH_NAMES, parseIsoDate } from "@/lib/format";
import type { PropertyRevenue } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

export default function ReportsPage() {
  const { propertyId, date } = useApp();
  const initial = parseIsoDate(date);
  const [year, setYear] = useState(initial.getFullYear());
  const [month, setMonth] = useState(initial.getMonth() + 1);

  const revenue = useAsync(
    () => api.reports.monthlyRevenue(year, month, propertyId),
    [year, month, propertyId],
  );

  const data = revenue.data;

  return (
    <>
      <PageHeader
        title="Monthly revenue"
        description="Net payout per property and channel. A stay counts in the month it checks out."
        action={
          <div className="flex gap-2">
            <Select
              aria-label="Month"
              className="w-36"
              value={month}
              onChange={(event) => setMonth(Number(event.target.value))}
            >
              {MONTH_NAMES.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Year"
              className="w-28"
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
            >
              {Array.from({ length: 5 }, (_, i) => initial.getFullYear() - 3 + i).map(
                (value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ),
              )}
            </Select>
          </div>
        }
      />

      {revenue.error && <ErrorNote message={revenue.error} />}
      {revenue.loading && <Spinner />}

      {data && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi
              label="Net payout"
              value={formatMoney(data.total_net_payout_amount, data.currency)}
              hint="what reaches the owner"
            />
            <Kpi
              label="Gross"
              value={formatMoney(data.total_gross_amount, data.currency)}
              hint="paid by guests"
            />
            <Kpi
              label="Platform fees"
              value={formatMoney(data.total_fees_amount, data.currency)}
            />
            <Kpi label="Nights sold" value={data.total_nights} />
          </div>

          <Card title="By channel" className="mb-6">
            {data.by_source.length === 0 ? (
              <EmptyState>No checked-out stays in this month yet.</EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <Th>Channel</Th>
                    <Th className="text-right">Reservations</Th>
                    <Th className="text-right">Nights</Th>
                    <Th className="text-right">Gross</Th>
                    <Th className="text-right">Fees</Th>
                    <Th className="text-right">Net payout</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_source.map((row) => (
                    <tr key={row.source}>
                      <Td>
                        <SourceTag source={row.source} />
                      </Td>
                      <Td className="text-right tabular-nums">{row.reservations_count}</Td>
                      <Td className="text-right tabular-nums">{row.nights}</Td>
                      <Td className="text-right tabular-nums">
                        {formatMoney(row.gross_amount, data.currency)}
                      </Td>
                      <Td className="text-right tabular-nums">
                        {formatMoney(row.fees_amount, data.currency)}
                      </Td>
                      <Td className="text-right font-semibold tabular-nums">
                        {formatMoney(row.net_payout_amount, data.currency)}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <div className="space-y-6">
            {data.properties.map((property) => (
              <PropertyRevenueCard key={property.property_id} property={property} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function PropertyRevenueCard({ property }: { property: PropertyRevenue }) {
  return (
    <Card
      title={`${property.property_name} — ${formatMoney(property.net_payout_amount, property.currency)} net`}
      padded={false}
    >
      <div className="border-b border-slate-100 px-4 py-3">
        <div className="flex flex-wrap gap-4 text-xs text-slate-600">
          {property.by_source.map((row) => (
            <span key={row.source} className="inline-flex items-center gap-1.5">
              <SourceTag source={row.source} />
              <span className="font-medium">
                {formatMoney(row.net_payout_amount, property.currency)}
              </span>
              <span className="text-slate-400">({row.reservations_count})</span>
            </span>
          ))}
        </div>
      </div>

      <Table>
        <thead>
          <tr>
            <Th>Guest</Th>
            <Th>Unit</Th>
            <Th>Checked out</Th>
            <Th>Channel</Th>
            <Th className="text-right">Gross</Th>
            <Th className="text-right">Fees</Th>
            <Th className="text-right">Net</Th>
          </tr>
        </thead>
        <tbody>
          {property.reservations.map((reservation) => (
            <tr key={reservation.id} className="hover:bg-slate-50">
              <Td>
                <Link
                  href={`/reservations/${reservation.id}`}
                  className="text-slate-800 hover:underline"
                >
                  {reservation.guest_display_name}
                </Link>
              </Td>
              <Td>{reservation.unit_name}</Td>
              <Td>{formatDate(reservation.check_out_date)}</Td>
              <Td>
                <SourceTag source={reservation.source} />
              </Td>
              <Td className="text-right tabular-nums">
                {formatMoney(reservation.gross_amount, reservation.currency)}
              </Td>
              <Td className="text-right tabular-nums">
                {formatMoney(reservation.fees_amount, reservation.currency)}
              </Td>
              <Td className="text-right font-medium tabular-nums">
                {formatMoney(reservation.net_payout_amount, reservation.currency)}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

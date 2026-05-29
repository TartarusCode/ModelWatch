import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { hasBenchmarkData } from "../lib/data";
import { formatPerMillion, providerFromModelId } from "../lib/pricing";
import type { EnrichedModel } from "../types";

const columnHelper = createColumnHelper<EnrichedModel>();

interface ModelTableProps {
  models: EnrichedModel[];
}

export function ModelTable({ models }: ModelTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "name", desc: false },
  ]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [minContext, setMinContext] = useState("");
  const [benchmarkOnly, setBenchmarkOnly] = useState(false);
  const [toolsOnly, setToolsOnly] = useState(false);
  const [reasoningOnly, setReasoningOnly] = useState(false);

  const providers = useMemo(() => {
    const set = new Set(models.map((m) => providerFromModelId(m.model.id)));
    return Array.from(set).sort();
  }, [models]);

  const filteredData = useMemo(() => {
    const minCtx = minContext ? Number.parseInt(minContext, 10) : 0;
    return models.filter((row) => {
      const { model, benchmarks } = row;
      if (providerFilter && providerFromModelId(model.id) !== providerFilter) {
        return false;
      }
      if (minCtx > 0 && (model.context_length ?? 0) < minCtx) {
        return false;
      }
      if (benchmarkOnly && !hasBenchmarkData(benchmarks)) {
        return false;
      }
      if (toolsOnly && !model.supported_parameters.includes("tools")) {
        return false;
      }
      if (
        reasoningOnly &&
        !model.supported_parameters.includes("reasoning") &&
        !model.supported_parameters.includes("include_reasoning")
      ) {
        return false;
      }
      if (!globalFilter) {
        return true;
      }
      const q = globalFilter.toLowerCase();
      return (
        model.id.toLowerCase().includes(q) ||
        model.name.toLowerCase().includes(q)
      );
    });
  }, [
    models,
    providerFilter,
    minContext,
    benchmarkOnly,
    toolsOnly,
    reasoningOnly,
    globalFilter,
  ]);

  const columns = useMemo(
    () => [
      columnHelper.accessor((row) => row.model.name, {
        id: "name",
        header: "Model",
        cell: (info) => (
          <Link to={`/models/${encodeURIComponent(info.row.original.model.id)}`}>
            {info.getValue()}
          </Link>
        ),
      }),
      columnHelper.accessor((row) => providerFromModelId(row.model.id), {
        id: "provider",
        header: "Provider",
      }),
      columnHelper.accessor((row) => row.model.pricing.prompt, {
        id: "prompt",
        header: "Prompt $/M",
        cell: (info) => (
          <span className="mono">{formatPerMillion(info.getValue())}</span>
        ),
      }),
      columnHelper.accessor((row) => row.model.pricing.completion, {
        id: "completion",
        header: "Completion $/M",
        cell: (info) => (
          <span className="mono">{formatPerMillion(info.getValue())}</span>
        ),
      }),
      columnHelper.accessor((row) => row.model.context_length ?? 0, {
        id: "context",
        header: "Context",
        cell: (info) => {
          const v = info.row.original.model.context_length;
          return v ? v.toLocaleString() : "—";
        },
      }),
      columnHelper.accessor(
        (row) => row.model.architecture.output_modalities.join(", "),
        {
          id: "modalities",
          header: "Output",
          cell: (info) => (
            <span className="muted">{info.getValue() || "—"}</span>
          ),
        },
      ),
      columnHelper.accessor((row) => hasBenchmarkData(row.benchmarks), {
        id: "benchmarks",
        header: "Benchmarks",
        cell: (info) =>
          info.getValue() ? (
            <span className="badge ok">Data</span>
          ) : (
            <span className="badge empty">None</span>
          ),
      }),
    ],
    [],
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <>
      <div className="filters">
        <input
          type="search"
          placeholder="Search models…"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          aria-label="Search models"
        />
        <select
          value={providerFilter}
          onChange={(e) => setProviderFilter(e.target.value)}
          aria-label="Filter by provider"
        >
          <option value="">All providers</option>
          {providers.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Min context"
          value={minContext}
          onChange={(e) => setMinContext(e.target.value)}
          aria-label="Minimum context length"
        />
        <label>
          <input
            type="checkbox"
            checked={benchmarkOnly}
            onChange={(e) => setBenchmarkOnly(e.target.checked)}
          />{" "}
          Has benchmarks
        </label>
        <label>
          <input
            type="checkbox"
            checked={toolsOnly}
            onChange={(e) => setToolsOnly(e.target.checked)}
          />{" "}
          Tools
        </label>
        <label>
          <input
            type="checkbox"
            checked={reasoningOnly}
            onChange={(e) => setReasoningOnly(e.target.checked)}
          />{" "}
          Reasoning
        </label>
      </div>
      <p className="muted" style={{ marginBottom: "0.75rem" }}>
        Showing {filteredData.length} of {models.length} models
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )}
                    {{
                      asc: " ↑",
                      desc: " ↓",
                    }[header.column.getIsSorted() as string] ?? ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

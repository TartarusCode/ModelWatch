import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { formatAaIndex, getAaSummaryScores } from "../lib/benchmarks";
import { hasBenchmarkData } from "../lib/data";
import { compareTokenPrices, providerFromModelId } from "../lib/pricing";
import {
  loadColumnVisibility,
  saveColumnVisibility,
} from "../lib/tableColumns";
import type { EnrichedModel } from "../types";
import { ColumnPicker } from "./ColumnPicker";
import { FilterChip } from "./FilterChip";
import { PriceCell } from "./PriceCell";
import { ProviderBadge } from "./ProviderBadge";

const columnHelper = createColumnHelper<EnrichedModel>();

interface ModelTableProps {
  models: EnrichedModel[];
}

export function ModelTable({ models }: ModelTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "prompt", desc: false },
  ]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [minContext, setMinContext] = useState("");
  const [benchmarkOnly, setBenchmarkOnly] = useState(false);
  const [toolsOnly, setToolsOnly] = useState(false);
  const [reasoningOnly, setReasoningOnly] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(
    loadColumnVisibility,
  );

  useEffect(() => {
    saveColumnVisibility(columnVisibility);
  }, [columnVisibility]);

  const providers = useMemo(() => {
    const set = new Set(models.map((m) => providerFromModelId(m.model.id)));
    return Array.from(set).sort();
  }, [models]);

  const filteredData = useMemo(() => {
    const minCtx = minContext
      ? Number.parseInt(minContext, 10) * 1000
      : 0;
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
        enableHiding: false,
        cell: (info) => {
          const { model } = info.row.original;
          return (
            <div className="model-cell">
              <Link
                to={`/models/${encodeURIComponent(model.id)}`}
                className="model-cell__name"
              >
                {info.getValue()}
              </Link>
              <span className="model-cell__id">{model.id}</span>
            </div>
          );
        },
      }),
      columnHelper.accessor((row) => providerFromModelId(row.model.id), {
        id: "provider",
        header: "Provider",
        cell: (info) => <ProviderBadge provider={info.getValue()} />,
      }),
      columnHelper.accessor((row) => row.model.pricing.prompt, {
        id: "prompt",
        header: "Prompt",
        sortingFn: (a, b) =>
          compareTokenPrices(
            a.original.model.pricing.prompt,
            b.original.model.pricing.prompt,
          ),
        cell: (info) => <PriceCell perToken={info.getValue()} />,
      }),
      columnHelper.accessor((row) => row.model.pricing.completion, {
        id: "completion",
        header: "Completion",
        sortingFn: (a, b) =>
          compareTokenPrices(
            a.original.model.pricing.completion,
            b.original.model.pricing.completion,
          ),
        cell: (info) => <PriceCell perToken={info.getValue()} />,
      }),
      columnHelper.accessor((row) => row.model.context_length ?? 0, {
        id: "context",
        header: "Context",
        cell: (info) => {
          const v = info.row.original.model.context_length;
          return (
            <span className="tabular-nums">
              {v ? `${(v / 1000).toFixed(0)}k` : "—"}
            </span>
          );
        },
      }),
      columnHelper.accessor(
        (row) =>
          getAaSummaryScores(row.benchmarks, row.model.id)?.intelligence ??
          null,
        {
          id: "intelligence",
          header: "Intel",
          sortingFn: (a, b) => {
            const left =
              getAaSummaryScores(a.original.benchmarks, a.original.model.id)
                ?.intelligence ?? -1;
            const right =
              getAaSummaryScores(b.original.benchmarks, b.original.model.id)
                ?.intelligence ?? -1;
            return left - right;
          },
          cell: (info) => {
            const scores = getAaSummaryScores(
              info.row.original.benchmarks,
              info.row.original.model.id,
            );
            const formatted = formatAaIndex(scores?.intelligence);
            if (!formatted) {
              return <span className="muted">—</span>;
            }
            return (
              <span
                className="tabular-nums"
                title={scores?.variantName}
              >
                {formatted}
              </span>
            );
          },
        },
      ),
      columnHelper.accessor(
        (row) =>
          getAaSummaryScores(row.benchmarks, row.model.id)?.coding ?? null,
        {
          id: "coding",
          header: "Coding",
          sortingFn: (a, b) => {
            const left =
              getAaSummaryScores(a.original.benchmarks, a.original.model.id)
                ?.coding ?? -1;
            const right =
              getAaSummaryScores(b.original.benchmarks, b.original.model.id)
                ?.coding ?? -1;
            return left - right;
          },
          cell: (info) => {
            const scores = getAaSummaryScores(
              info.row.original.benchmarks,
              info.row.original.model.id,
            );
            const formatted = formatAaIndex(scores?.coding);
            if (!formatted) {
              return <span className="muted">—</span>;
            }
            return (
              <span className="tabular-nums" title={scores?.variantName}>
                {formatted}
              </span>
            );
          },
        },
      ),
      columnHelper.accessor(
        (row) =>
          getAaSummaryScores(row.benchmarks, row.model.id)?.agentic ?? null,
        {
          id: "agentic",
          header: "Agentic",
          sortingFn: (a, b) => {
            const left =
              getAaSummaryScores(a.original.benchmarks, a.original.model.id)
                ?.agentic ?? -1;
            const right =
              getAaSummaryScores(b.original.benchmarks, b.original.model.id)
                ?.agentic ?? -1;
            return left - right;
          },
          cell: (info) => {
            const scores = getAaSummaryScores(
              info.row.original.benchmarks,
              info.row.original.model.id,
            );
            const formatted = formatAaIndex(scores?.agentic);
            if (!formatted) {
              return <span className="muted">—</span>;
            }
            return (
              <span className="tabular-nums" title={scores?.variantName}>
                {formatted}
              </span>
            );
          },
        },
      ),
    ],
    [],
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, columnVisibility },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const visibleColumnCount = table.getVisibleLeafColumns().length;

  const activeFilterCount =
    (providerFilter ? 1 : 0) +
    (minContext ? 1 : 0) +
    (benchmarkOnly ? 1 : 0) +
    (toolsOnly ? 1 : 0) +
    (reasoningOnly ? 1 : 0);

  return (
    <section className="table-panel">
      <div className="table-toolbar">
        <div className="search-field">
          <span className="search-field__icon" aria-hidden>
            ⌕
          </span>
          <input
            type="search"
            className="search-field__input"
            placeholder="Search by name or ID…"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            aria-label="Search models"
          />
        </div>
        <select
          className="select-field"
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
          className="input-field input-field--narrow"
          placeholder="Min ctx (k)"
          value={minContext}
          onChange={(e) => setMinContext(e.target.value)}
          aria-label="Minimum context in tokens"
        />
        <ColumnPicker
          visibility={columnVisibility}
          onChange={setColumnVisibility}
        />
      </div>
      <div className="filter-chips">
        <FilterChip
          label="Has benchmarks"
          active={benchmarkOnly}
          onToggle={() => setBenchmarkOnly((v) => !v)}
        />
        <FilterChip
          label="Tools"
          active={toolsOnly}
          onToggle={() => setToolsOnly((v) => !v)}
        />
        <FilterChip
          label="Reasoning"
          active={reasoningOnly}
          onToggle={() => setReasoningOnly((v) => !v)}
        />
        {activeFilterCount > 0 ? (
          <button
            type="button"
            className="filter-clear"
            onClick={() => {
              setProviderFilter("");
              setMinContext("");
              setBenchmarkOnly(false);
              setToolsOnly(false);
              setReasoningOnly(false);
            }}
          >
            Clear filters
          </button>
        ) : null}
      </div>
      <div className="table-panel__meta">
        <span>
          Showing <strong>{filteredData.length}</strong> of{" "}
          {models.length.toLocaleString()}
        </span>
        <span className="muted">Prices per 1M tokens</span>
      </div>
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className={
                      header.column.getCanSort() ? "data-table__sortable" : ""
                    }
                  >
                    <span className="th-inner">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {{
                        asc: " ↑",
                        desc: " ↓",
                      }[header.column.getIsSorted() as string] ?? null}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={visibleColumnCount} className="data-table__empty">
                  No models match your filters.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

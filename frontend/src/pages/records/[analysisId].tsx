import { AnalysisCoverageCard } from '@/components/AnalysisCoverageCard';
import { Alert, Button, Card, Input } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { clearLatestAnalysisId, saveLatestAnalysisId } from '@/lib/analysisSession';
import { apiClient } from '@/services/api';
import { DatasetSummary, InventoryItem, ManualItemInput, SourceObservation } from '@/types';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Search, X } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';

const PAGE_SIZE = 30;

type SortDir = 'asc' | 'desc';

type EnrichedObservation = SourceObservation & {
  _item_id?: number | null;
};

export default function RecordsPage() {
  const router = useRouter();
  const { analysisId } = router.query;

  const [items, setItems] = useState<InventoryItem[]>([]);
  const [datasetSummary, setDatasetSummary] = useState<DatasetSummary | null>(null);
  const [sourceObservations, setSourceObservations] = useState<SourceObservation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Edit state (operates on item snapshot level)
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [editData, setEditData] = useState<Partial<ManualItemInput>>({});

  // Sort
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Search & filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterItemName, setFilterItemName] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterSupplier, setFilterSupplier] = useState('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    if (!analysisId) return;
    fetchRecords();
  }, [analysisId]);

  // Reset page whenever filters/sort change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterItemName, filterDateFrom, filterDateTo, filterSupplier, sortDir]);

  const fetchRecords = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await apiClient.getRecords(analysisId as string);
      const normalizedItems = (response.items || []).map((item: any) => ({
        ...item,
        date: item.date || item.last_updated,
      }));
      setDatasetSummary(response.dataset_summary);
      setItems(normalizedItems);
      setSourceObservations(response.source_observations || []);
    } catch (err: any) {
      if (err.response?.status === 404) {
        clearLatestAnalysisId();
        try {
          const latest = await apiClient.getLatestAnalysis();
          if (latest.analysis_id && latest.analysis_id !== analysisId) {
            saveLatestAnalysisId(latest.analysis_id);
            await router.replace(`/records/${latest.analysis_id}`);
            return;
          }
        } catch {
          await router.replace('/');
          return;
        }
      }
      const message = err.response?.data?.message || err.message || 'Failed to fetch records';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Build lookup maps from items
  const itemIdByName = useMemo(
    () => new Map(items.map((i) => [i.item_name.toLowerCase(), i.item_id])),
    [items]
  );
  const itemByItemId = useMemo(
    () => new Map(items.map((i) => [i.item_id, i])),
    [items]
  );

  // Use sourceObservations when available, fall back to items-as-observations
  const tableData: EnrichedObservation[] = useMemo(() => {
    if (sourceObservations.length > 0) {
      return sourceObservations.map((obs) => ({
        ...obs,
        _item_id: obs.item_id ?? itemIdByName.get(obs.item_name.toLowerCase()),
      }));
    }
    // Fallback: use item snapshots
    return items.map((item) => ({
      date: item.date,
      item_id: item.item_id,
      item_name: item.item_name,
      current_stock: item.current_stock,
      unit: item.unit,
      usage_value: item.daily_usage,
      usage_period: 'daily' as const,
      lead_time_days: item.lead_time,
      price_per_unit: item.price_per_unit,
      category: item.category,
      subcategory: item.subcategory,
      supplier_name: item.supplier_name,
      seasonal_factor: item.seasonal_factor,
      manual_reorder_level: item.reorder_level,
      recent_waste_percentage: item.waste_percentage,
      _item_id: item.item_id,
    }));
  }, [sourceObservations, items, itemIdByName]);

  // Unique values for filter dropdowns
  const uniqueItemNames = useMemo(
    () => Array.from(new Set(tableData.map((r) => r.item_name))).sort(),
    [tableData]
  );
  const uniqueSuppliers = useMemo(
    () => Array.from(new Set(tableData.map((r) => r.supplier_name).filter(Boolean) as string[])).sort(),
    [tableData]
  );

  const processedRows = useMemo(() => {
    let rows = [...tableData];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      rows = rows.filter((row) =>
        [row.item_name, row.date, String(row.current_stock), row.unit,
          row.supplier_name, String(row.usage_value)]
          .some((v) => v?.toLowerCase().includes(q))
      );
    }

    if (filterItemName)  rows = rows.filter((r) => r.item_name === filterItemName);
    if (filterDateFrom)  rows = rows.filter((r) => (r.date || '') >= filterDateFrom);
    if (filterDateTo)    rows = rows.filter((r) => (r.date || '') <= filterDateTo);
    if (filterSupplier)  rows = rows.filter((r) => r.supplier_name === filterSupplier);

    rows.sort((a, b) => {
      const av = a.date || '';
      const bv = b.date || '';
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return rows;
  }, [tableData, searchQuery, filterItemName, filterDateFrom, filterDateTo, filterSupplier, sortDir]);

  const totalPages = Math.max(1, Math.ceil(processedRows.length / PAGE_SIZE));
  const pagedRows = processedRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const hasFilters = searchQuery || filterItemName || filterDateFrom || filterDateTo || filterSupplier;
  const clearAllFilters = () => {
    setSearchQuery('');
    setFilterItemName('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterSupplier('');
  };

  const handleEdit = (itemId: number | null | undefined) => {
    if (itemId == null) return;
    const item = itemByItemId.get(itemId);
    if (!item) return;
    setEditingItemId(itemId);
    setEditData({ item_name: item.item_name, current_stock: item.current_stock, unit: item.unit, date: item.date });
  };

  const handleSaveEdit = async () => {
    if (!editingItemId) return;
    try {
      await apiClient.updateRecord(analysisId as string, editingItemId, editData);
      toast.success('Record updated successfully');
      setEditingItemId(null);
      fetchRecords();
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || 'Failed to update record');
    }
  };

  const handleDelete = async (itemId: number | null | undefined) => {
    if (itemId == null) return;
    if (items.length === 1) { toast.error('Cannot delete the final remaining item'); return; }
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
      await apiClient.deleteRecord(analysisId as string, itemId);
      toast.success('Record deleted successfully');
      fetchRecords();
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || 'Failed to delete record');
    }
  };

  const totalRecords = sourceObservations.length > 0 ? sourceObservations.length : items.length;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationBar onFeatureSelect={() => {}} currentAnalysisId={analysisId as string} activeSection="records" />

      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Review Records</h1>
            <p className="text-gray-600 mt-1">
              {totalRecords} observation{totalRecords !== 1 ? 's' : ''} &middot; {items.length} unique item{items.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Link href={`/dashboard/${analysisId}`}>
            <Button variant="secondary">Back to Dashboard</Button>
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 md:px-8 py-8 space-y-4">
        {error && <Alert type="error" message={error} onClose={() => setError('')} />}

        {datasetSummary && (
          <AnalysisCoverageCard
            rowCount={datasetSummary.row_count}
            itemCount={datasetSummary.item_count}
            dateRange={datasetSummary.date_range}
          />
        )}

        {/* Search + Filters */}
        <Card className="p-4">
          {/* Search bar */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search records by name, date, stock, supplier…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>

          {/* Filter row */}
          <div className="flex flex-wrap gap-2 items-end">
            {/* Item Name */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Item Name</label>
              <select
                value={filterItemName}
                onChange={(e) => setFilterItemName(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-[140px]"
              >
                <option value="">All items</option>
                {uniqueItemNames.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Date from</label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Date to */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Date to</label>
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Supplier */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Supplier</label>
              <select
                value={filterSupplier}
                onChange={(e) => setFilterSupplier(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white min-w-[160px]"
              >
                <option value="">All suppliers</option>
                {uniqueSuppliers.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Sort date */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Sort by Date</label>
              <button
                type="button"
                onClick={() => setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))}
                className="inline-flex items-center gap-1.5 border border-blue-500 bg-blue-50 text-blue-700 rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-blue-100 transition-colors"
              >
                Date
                {sortDir === 'asc'
                  ? <ArrowUp className="w-3.5 h-3.5" />
                  : <ArrowDown className="w-3.5 h-3.5" />
                }
              </button>
            </div>

            {/* Clear filters */}
            {hasFilters && (
              <button
                type="button"
                onClick={clearAllFilters}
                className="self-end text-xs text-gray-500 hover:text-gray-700 underline pb-2"
              >
                Clear all
              </button>
            )}
          </div>

          {/* Result count */}
          <p className="mt-2 text-xs text-gray-500">
            Showing {pagedRows.length} of {processedRows.length} records
            {hasFilters && ` (filtered from ${totalRecords} total)`}
          </p>
        </Card>

        {/* Table */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="items-table">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Item Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Stock</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Daily Usage</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Supplier</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Operations</th>
                </tr>
              </thead>
              <tbody>
                {pagedRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-sm text-gray-500">
                      No records match your filters.
                    </td>
                  </tr>
                ) : pagedRows.map((row, index) => {
                  const itemId = row._item_id;
                  const isEditing = editingItemId === itemId && itemId != null;
                  return (
                    <tr key={`${row.item_name}-${row.date}-${index}`} className="border-b border-gray-200 hover:bg-gray-50">
                      {isEditing ? (
                        <>
                          <td className="px-6 py-4">
                            <Input value={editData.item_name || ''} onChange={(e) => setEditData({ ...editData, item_name: e.target.value })} />
                          </td>
                          <td className="px-6 py-4">
                            <Input type="date" value={editData.date || ''} onChange={(e) => setEditData({ ...editData, date: e.target.value })} />
                          </td>
                          <td className="px-6 py-4">
                            <Input type="number" value={editData.current_stock || 0} onChange={(e) => setEditData({ ...editData, current_stock: parseFloat(e.target.value) })} />
                          </td>
                          <td className="px-6 py-4" colSpan={3}>
                            <div className="flex gap-2">
                              <Button variant="primary" size="sm" onClick={handleSaveEdit}>Save</Button>
                              <Button variant="secondary" size="sm" onClick={() => setEditingItemId(null)}>Cancel</Button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="px-6 py-4 font-medium text-gray-900">{row.item_name}</td>
                          <td className="px-6 py-4 text-sm text-blue-600">{row.date || '-'}</td>
                          <td className="px-6 py-4 text-sm text-gray-900">{row.current_stock} {row.unit}</td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {row.usage_value != null ? `${Number(row.usage_value).toFixed(2)} ${row.usage_period ?? 'daily'}` : '-'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-700">
                            {row.supplier_name || <span className="text-gray-400">—</span>}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <div className="flex gap-2">
                              <Button variant="secondary" size="sm" onClick={() => handleEdit(itemId)}>Edit</Button>
                              <Button variant="danger" size="sm" onClick={() => handleDelete(itemId)}>Delete</Button>
                            </div>
                          </td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50">
              <p className="text-sm text-gray-600">
                Page {currentPage} of {totalPages} &nbsp;·&nbsp; {processedRows.length} records
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="px-2 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-100 disabled:cursor-not-allowed"
                >
                  «
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
                  .reduce<(number | '…')[]>((acc, p, idx, arr) => {
                    if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('…');
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((p, idx) =>
                    p === '…' ? (
                      <span key={`ellipsis-${idx}`} className="px-2 text-gray-400 text-sm">…</span>
                    ) : (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p as number)}
                        className={`px-3 py-1 text-sm rounded border transition-colors ${
                          currentPage === p
                            ? 'border-blue-500 bg-blue-500 text-white'
                            : 'border-gray-300 hover:bg-gray-100 text-gray-700'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="px-2 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-100 disabled:cursor-not-allowed"
                >
                  »
                </button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

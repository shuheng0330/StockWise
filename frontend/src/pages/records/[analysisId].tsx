import { AnalysisCoverageCard } from '@/components/AnalysisCoverageCard';
import { Alert, Button, Card, Input } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { SourceObservationTable } from '@/components/SourceObservationTable';
import { clearLatestAnalysisId, saveLatestAnalysisId } from '@/lib/analysisSession';
import { apiClient } from '@/services/api';
import { DatasetSummary, InventoryItem, ManualItemInput, RecommendedAction, SourceObservation } from '@/types';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';

type SortKey = 'date' | 'reorder_urgency_score' | 'waste_risk_score';
type SortDir = 'asc' | 'desc';

export default function RecordsPage() {
  const router = useRouter();
  const { analysisId } = router.query;
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [datasetSummary, setDatasetSummary] = useState<DatasetSummary | null>(null);
  const [sourceObservations, setSourceObservations] = useState<SourceObservation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<Partial<ManualItemInput>>({});
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const renderSortIcon = (key: SortKey) => {
    if (sortKey !== key) {
      return <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />;
    }
    return sortDir === 'asc' ? (
      <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
    );
  };

  const sortedItems = useMemo(() => {
    if (!sortKey) return items;
    return [...items].sort((a, b) => {
      let av: number | string;
      let bv: number | string;
      if (sortKey === 'date') {
        av = a.date || '';
        bv = b.date || '';
      } else {
        av = (a as any)[sortKey] ?? 0;
        bv = (b as any)[sortKey] ?? 0;
      }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [items, sortKey, sortDir]);

  const getActionColor = (action: RecommendedAction) => {
    switch (action) {
      case 'RESTOCK_NOW':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'BUY_LESS':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'DELAY_PURCHASE':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'MONITOR_CLOSELY':
        return 'bg-green-100 text-green-800 border-green-300';
    }
  };

  useEffect(() => {
    if (!analysisId) return;
    fetchRecords();
  }, [analysisId]);

  const fetchRecords = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await apiClient.getRecords(analysisId as string);

      // MAP THE DATA HERE: 
      // This creates a 'date' property if it's missing but 'last_updated' exists
      const normalizedItems = (response.items || []).map((item: any) => ({
        ...item,
        date: item.date || item.last_updated
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

  const handleEdit = (item: InventoryItem) => {
    setEditingId(item.item_id);
    setEditData({
      item_name: item.item_name,
      current_stock: item.current_stock,
      unit: item.unit,
      date: item.date,
    });
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;

    try {
      await apiClient.updateRecord(analysisId as string, editingId, editData);
      toast.success('Record updated successfully');
      setEditingId(null);
      fetchRecords();
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to update record';
      toast.error(message);
    }
  };

  const handleDelete = async (itemId: number) => {
    if (items.length === 1) {
      toast.error('Cannot delete the final remaining item');
      return;
    }

    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
      await apiClient.deleteRecord(analysisId as string, itemId);
      toast.success('Record deleted successfully');
      fetchRecords();
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to delete record';
      toast.error(message);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <NavigationBar
        onFeatureSelect={() => { }} // Not used in analysis pages
        currentAnalysisId={analysisId as string}
        activeSection="records"
      />

      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Review Records</h1>
              <p className="text-gray-600 mt-1">{items.length} current item snapshots</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href={`/dashboard/${analysisId}`}>
                <Button variant="secondary">Back to Dashboard</Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {error && (
          <Alert type="error" message={error} onClose={() => setError('')} className="mb-6" />
        )}

        {datasetSummary && (
          <AnalysisCoverageCard
            className="mb-4"
            rowCount={datasetSummary.row_count}
            itemCount={datasetSummary.item_count}
            dateRange={datasetSummary.date_range}
          />
        )}

        <SourceObservationTable
          observations={sourceObservations}
          className="mb-6"
        />

        <Card className="p-4 mb-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-gray-600 font-medium">Sort by:</span>
            {([
              { key: 'date', label: 'Date' },
            ] as { key: SortKey; label: string }[]).map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => handleSort(key)}
                className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border transition-colors ${sortKey === key
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
              >
                {label}
                {renderSortIcon(key)}
              </button>
            ))}
            {sortKey && (
              <button
                type="button"
                onClick={() => { setSortKey(null); setSortDir('desc'); }}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
              >
                Clear
              </button>
            )}
          </div>
        </Card>

        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Item Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    <button
                      type="button"
                      onClick={() => handleSort('date')}
                      className="inline-flex items-center gap-1 hover:text-blue-600"
                    >
                      Date {renderSortIcon('date')}
                    </button>
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Stock</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Unit</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Action</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Daily Usage</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900 min-w-[160px]">Recommendation</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Operations</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map((item) => (
                  <tr key={item.item_id} className="border-b border-gray-200 hover:bg-gray-50">
                    {editingId === item.item_id ? (
                      <>
                        <td className="px-6 py-4">
                          <Input
                            value={editData.item_name || ''}
                            onChange={(e) => setEditData({ ...editData, item_name: e.target.value })}
                          />
                        </td>
                        <td className="px-6 py-4">
                          <Input
                            type="date"
                            value={editData.date || ''}
                            onChange={(e) => setEditData({ ...editData, date: e.target.value })}
                          />
                        </td>
                        <td className="px-6 py-4">
                          <Input
                            type="number"
                            value={editData.current_stock || 0}
                            onChange={(e) => setEditData({ ...editData, current_stock: parseFloat(e.target.value) })}
                          />
                        </td>
                        <td className="px-6 py-4">
                          <Input
                            value={editData.unit || ''}
                            onChange={(e) => setEditData({ ...editData, unit: e.target.value })}
                          />
                        </td>
                        <td className="px-6 py-4" colSpan={4}>
                          <div className="flex gap-2">
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={handleSaveEdit}
                            >
                              Save
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setEditingId(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-6 py-4 font-medium text-gray-900">{item.item_name}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">{item.date || '-'}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.current_stock}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.unit}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.recommended_action.replace('_', ' ')}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.daily_usage.toFixed(2)}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-block whitespace-nowrap px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(item.recommended_action)}`}>
                            {item.recommended_action.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <div className="flex gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleEdit(item)}
                            >
                              Edit
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => handleDelete(item.item_id)}
                            >
                              Delete
                            </Button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}

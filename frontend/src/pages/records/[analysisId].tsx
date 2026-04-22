import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Button, Card, Alert, Input, Select } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { apiClient } from '@/services/api';
import { InventoryItem, ManualItemInput, PerishabilityLevel, UsagePeriod, RecommendedAction } from '@/types';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function RecordsPage() {
  const router = useRouter();
  const { analysisId } = router.query;

  const [items, setItems] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<ManualItemInput>>({});

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
      setItems(response.items || []);
    } catch (err: any) {
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
      category: item.category,
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

  const handleDelete = async (itemId: string) => {
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
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Review Records</h1>
              <p className="text-gray-600 mt-1">{items.length} items</p>
            </div>
            <div className="flex gap-2">
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

        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Item Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Category</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Stock</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Unit</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Action</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Daily Usage</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Recommendation</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Operations</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
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
                            value={editData.category || ''}
                            onChange={(e) => setEditData({ ...editData, category: e.target.value })}
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
                        <td className="px-6 py-4 text-sm text-gray-600">{item.category || '-'}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.current_stock}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.unit}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.recommended_action.replace('_', ' ')}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{item.daily_usage.toFixed(2)}</td>
                        <td className="px-6 py-4">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(item.recommended_action)}`}>
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

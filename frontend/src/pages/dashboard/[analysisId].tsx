import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Search, Filter, TrendingUp, AlertCircle, DollarSign, Percent } from 'lucide-react';
import { Button, Card, Input, Alert } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { apiClient } from '@/services/api';
import { AnalysisResponse, InventoryItem, RecommendedAction } from '@/types';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const router = useRouter();
  const { analysisId } = router.query;

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState<RecommendedAction | 'ALL'>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!analysisId) return;

    fetchAnalysis();
  }, [analysisId]);

  const fetchAnalysis = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await apiClient.getAnalysis(analysisId as string);
      setAnalysis(response);
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to fetch analysis';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="min-h-screen bg-gray-50 p-4 md:p-8">
        <div className="max-w-4xl mx-auto">
          <Link href="/">
            <Button variant="secondary" className="mb-6">
              ← Back to Entry
            </Button>
          </Link>
          <Alert type="error" title="Error" message={error || 'Analysis not found'} />
        </div>
      </div>
    );
  }

  const filteredItems = analysis.items.filter((item) => {
    const matchesSearch =
      item.item_name.toLowerCase().includes(search.toLowerCase()) ||
      item.category?.toLowerCase().includes(search.toLowerCase()) ||
      item.supplier_name?.toLowerCase().includes(search.toLowerCase());

    const matchesAction = actionFilter === 'ALL' || item.recommended_action === actionFilter;

    return matchesSearch && matchesAction;
  });

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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <NavigationBar
        onFeatureSelect={() => { }} // Not used in analysis pages
        currentAnalysisId={analysisId as string}
        activeSection="dashboard"
      />

      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Analysis Dashboard</h1>
              <p className="text-gray-600 mt-1">Analysis ID: {analysisId}</p>
            </div>
            <div className="flex gap-2">
              <Link href={`/records/${analysisId}`}>
                <Button variant="secondary">Review Records</Button>
              </Link>
              <Link href="/">
                <Button variant="outline">New Analysis</Button>
              </Link>
            </div>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Total Items</p>
                  <p className="text-2xl font-bold text-gray-900">{analysis.kpi_summary.item_count}</p>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Restock Now</p>
                  <p className="text-2xl font-bold text-red-600">{analysis.kpi_summary.restock_now_count}</p>
                </div>
                <AlertCircle className="w-8 h-8 text-red-200" />
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Buy Less</p>
                  <p className="text-2xl font-bold text-amber-600">{analysis.kpi_summary.buy_less_count}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-amber-200" />
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">High Waste Risk</p>
                  <p className="text-2xl font-bold text-orange-600">{analysis.kpi_summary.high_waste_risk_count}</p>
                </div>
                <Percent className="w-8 h-8 text-orange-200" />
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">At Risk Value</p>
                  <p className="text-2xl font-bold text-blue-600">
                    ${analysis.kpi_summary.inventory_value_at_risk.toFixed(0)}
                  </p>
                </div>
                <DollarSign className="w-8 h-8 text-blue-200" />
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Avg Days Cover</p>
                  <p className="text-2xl font-bold text-green-600">
                    {analysis.dataset_summary?.avg_days_of_cover?.toFixed(1) ?? "0.0"}                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-8">
        {/* Filters */}
        <Card className="p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="Search by item name, category, supplier..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Actions</option>
              <option value="RESTOCK_NOW">Restock Now</option>
              <option value="BUY_LESS">Buy Less</option>
              <option value="DELAY_PURCHASE">Delay Purchase</option>
              <option value="MONITOR_CLOSELY">Monitor Closely</option>
            </select>
          </div>
        </Card>

        {/* Results Count */}
        <div className="mb-4">
          <p className="text-gray-600">
            Showing {filteredItems.length} of {analysis.items.length} items
          </p>
        </div>

        {/* Items Table */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Item</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Category</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Stock</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Days Cover</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Urgency</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Waste Risk</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Action</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Views</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.item_id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{item.item_name}</p>
                      {item.supplier_name && (
                        <p className="text-sm text-gray-600">{item.supplier_name}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{item.category || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {item.current_stock} {item.unit}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{item.days_of_cover.toFixed(1)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded h-2">
                          <div
                            className="bg-red-500 h-full rounded"
                            style={{ width: `${Math.min(item.reorder_urgency_score, 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {item.reorder_urgency_score.toFixed(0)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded h-2">
                          <div
                            className="bg-yellow-500 h-full rounded"
                            style={{ width: `${Math.min(item.waste_risk_score, 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {item.waste_risk_score.toFixed(0)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(item.recommended_action)}`}>
                        {item.recommended_action.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className="flex gap-2">
                        <Link href={`/simulation/${analysisId}/${item.item_id}`}>
                          <Button variant="secondary" size="sm">Simulate</Button>
                        </Link>
                        <Link href={`/explanation/${analysisId}/${item.item_id}`}>
                          <Button variant="outline" size="sm">Explain</Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {filteredItems.length === 0 && (
          <Card className="p-8 text-center">
            <p className="text-gray-600">No items match your filters.</p>
          </Card>
        )}
      </div>
    </div>
  );
}

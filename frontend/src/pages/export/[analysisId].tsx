import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { Download, Printer, FileJson, FileSpreadsheet } from 'lucide-react';
import { Alert, Button, Card } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { BusinessValueSnapshotCard } from '@/components/BusinessValueSnapshotCard';
import { buildBusinessValueSnapshot } from '@/lib/businessValue';
import { apiClient } from '@/services/api';
import { saveLatestAnalysisId } from '@/lib/analysisSession';
import { AnalysisResponse, InventoryItem } from '@/types';

const CSV_COLUMNS: { key: keyof InventoryItem; label: string }[] = [
  { key: 'item_id', label: 'Item ID' },
  { key: 'date', label: 'Date' },
  { key: 'item_name', label: 'Item Name' },
  { key: 'category', label: 'Category' },
  { key: 'subcategory', label: 'Subcategory' },
  { key: 'supplier_name', label: 'Supplier' },
  { key: 'unit', label: 'Unit' },
  { key: 'current_stock', label: 'Current Stock' },
  { key: 'reorder_level', label: 'Reorder Level' },
  { key: 'daily_usage', label: 'Daily Usage' },
  { key: 'lead_time', label: 'Lead Time (days)' },
  { key: 'price_per_unit', label: 'Price per Unit' },
  { key: 'seasonal_factor', label: 'Seasonal Factor' },
  { key: 'waste_percentage', label: 'Waste %' },
  { key: 'days_of_cover', label: 'Days of Cover' },
  { key: 'inventory_value', label: 'Inventory Value' },
  { key: 'estimated_waste_cost', label: 'Estimated Waste Cost' },
  { key: 'lead_time_demand', label: 'Lead Time Demand' },
  { key: 'stock_gap_to_lead_demand', label: 'Stock Gap to Lead Demand' },
  { key: 'reorder_urgency_score', label: 'Urgency Score' },
  { key: 'waste_risk_score', label: 'Waste Risk Score' },
  { key: 'recommended_action', label: 'Recommended Action' },
];

function escapeCsv(value: unknown): string {
  if (value === null || value === undefined) return '';
  const asString = String(value);
  if (/[",\n\r]/.test(asString)) {
    return `"${asString.replace(/"/g, '""')}"`;
  }
  return asString;
}

function buildCsv(items: InventoryItem[]): string {
  const header = CSV_COLUMNS.map((c) => escapeCsv(c.label)).join(',');
  const rows = items.map((item) =>
    CSV_COLUMNS.map((c) => escapeCsv((item as any)[c.key])).join(',')
  );
  return [header, ...rows].join('\r\n');
}

function downloadBlob(content: string, type: string, fileName: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function ExportPage() {
  const router = useRouter();
  const { analysisId } = router.query;

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
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
      saveLatestAnalysisId(response.analysis_id);
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to fetch analysis';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const fileStem = useMemo(() => {
    const id = typeof analysisId === 'string' ? analysisId : 'analysis';
    const today = new Date().toISOString().slice(0, 10);
    return `stockwise-${id.slice(0, 8)}-${today}`;
  }, [analysisId]);
  const businessValueSnapshot = useMemo(
    () => (analysis ? buildBusinessValueSnapshot(analysis) : null),
    [analysis]
  );

  const handleExportCsv = () => {
    if (!analysis) return;
    const csv = buildCsv(analysis.items);
    downloadBlob(csv, 'text/csv;charset=utf-8', `${fileStem}.csv`);
    toast.success('CSV downloaded');
  };

  const handleExportJson = () => {
    if (!analysis) return;
    const json = JSON.stringify(analysis, null, 2);
    downloadBlob(json, 'application/json', `${fileStem}.json`);
    toast.success('JSON downloaded');
  };

  const handlePrint = () => {
    if (typeof window !== 'undefined') {
      window.print();
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
      <div className="min-h-screen bg-gray-50">
        <NavigationBar
          onFeatureSelect={() => { }}
          currentAnalysisId={typeof analysisId === 'string' ? analysisId : undefined}
          activeSection="export"
        />
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-8">
          <Link href="/">
            <Button variant="secondary" className="mb-6">
              ← Back
            </Button>
          </Link>
          <Alert type="error" title="Error" message={error || 'Analysis not found'} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationBar
        onFeatureSelect={() => { }}
        currentAnalysisId={analysis.analysis_id}
        activeSection="export"
      />

      <div className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-6">
          <div className="min-w-0">
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Export Analysis</h1>
            <p className="text-gray-600 mt-1 text-sm md:text-base break-all">
              Analysis ID: {analysis.analysis_id}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/dashboard/${analysis.analysis_id}`}>
              <Button variant="secondary">Back to Dashboard</Button>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <Card className="p-6 flex flex-col">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
                <FileSpreadsheet className="w-5 h-5 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">CSV Export</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              Download all {analysis.items.length} items with scores and recommended actions.
              Opens in Excel, Google Sheets, or any spreadsheet tool.
            </p>
            <Button variant="primary" data-testid="export-csv-btn" onClick={handleExportCsv} className="inline-flex items-center gap-2 justify-center">
              <Download className="w-4 h-4" />
              Download CSV
            </Button>
          </Card>

          <Card className="p-6 flex flex-col">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg">
                <FileJson className="w-5 h-5 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">JSON Export</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              Raw analysis payload including KPI summary, dataset summary, and items.
              Useful for scripting or feeding into another tool.
            </p>
            <Button variant="primary" onClick={handleExportJson} className="inline-flex items-center gap-2 justify-center">
              <Download className="w-4 h-4" />
              Download JSON
            </Button>
          </Card>

          <Card className="p-6 flex flex-col">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg">
                <Printer className="w-5 h-5 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Print / PDF</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              Generate a printable report. Use your browser's print dialog to save as PDF.
            </p>
            <Button variant="secondary" onClick={handlePrint} className="inline-flex items-center gap-2 justify-center">
              <Printer className="w-4 h-4" />
              Print / Save PDF
            </Button>
          </Card>
        </div>

        {businessValueSnapshot && <BusinessValueSnapshotCard snapshot={businessValueSnapshot} />}

        <Card className="p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Summary</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Items</p>
              <p className="text-xl font-semibold text-gray-900">{analysis.kpi_summary.item_count}</p>
            </div>
            <div>
              <p className="text-gray-500">Restock Now</p>
              <p className="text-xl font-semibold text-red-600">{analysis.kpi_summary.restock_now_count}</p>
            </div>
            <div>
              <p className="text-gray-500">Buy Less</p>
              <p className="text-xl font-semibold text-amber-600">{analysis.kpi_summary.buy_less_count}</p>
            </div>
            <div>
              <p className="text-gray-500">Value at Risk</p>
              <p className="text-xl font-semibold text-blue-600">
                ${analysis.kpi_summary.inventory_value_at_risk.toFixed(0)}
              </p>
            </div>
          </div>
        </Card>

        <Card className="overflow-hidden print:shadow-none">
          <div className="px-4 md:px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Preview</h2>
            <p className="text-sm text-gray-500">Top 20 rows</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Item</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Date</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Stock</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Days Cover</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Urgency</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Waste Risk</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">Action</th>
                </tr>
              </thead>
              <tbody>
                {analysis.items.slice(0, 20).map((item) => (
                  <tr key={item.item_id} className="border-b border-gray-100">
                    <td className="px-4 py-2 text-gray-900">{item.item_name}</td>
                    <td className="px-4 py-2 text-gray-600 whitespace-nowrap">{item.date || '-'}</td>
                    <td className="px-4 py-2 text-gray-900">
                      {item.current_stock} {item.unit}
                    </td>
                    <td className="px-4 py-2 text-gray-900">{item.days_of_cover.toFixed(1)}</td>
                    <td className="px-4 py-2 text-gray-900">{item.reorder_urgency_score}</td>
                    <td className="px-4 py-2 text-gray-900">{item.waste_risk_score}</td>
                    <td className="px-4 py-2 text-gray-900">{item.recommended_action.replace('_', ' ')}</td>
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

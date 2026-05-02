import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Upload, FileText, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';
import { Button, Alert, Card } from '@/components/common';
import { InventoryItemForm } from '@/components/InventoryItemForm';
import { NavigationBar } from '@/components/Dashboard';
import { GuidedTour, shouldAutoOpenTour } from '@/components/GuidedTour';
import { apiClient } from '@/services/api';
import { getLatestAnalysisId, recordAnalysisInHistory, saveLatestAnalysisId } from '@/lib/analysisSession';
import { ManualItemInput } from '@/types';
import { useAuth } from '@/lib/auth';
import toast from 'react-hot-toast';

interface CsvColumnSpec {
  name: string;
  required: boolean;
  type: string;
  description: string;
  example: string;
  notes?: string;
}

const CSV_COLUMNS: CsvColumnSpec[] = [
  {
    name: 'Date',
    required: true,
    type: 'YYYY-MM-DD',
    description: 'Observation date — when this snapshot was recorded.',
    example: '2026-04-15',
    notes: 'Must use four-digit year, dash separator. Other formats will be rejected.',
  },
  {
    name: 'Item_ID',
    required: false,
    type: 'integer',
    description: 'Unique numeric ID for this item. Optional — the system can assign one.',
    example: '1',
  },
  {
    name: 'Item_Name',
    required: true,
    type: 'text',
    description: 'Display name of the inventory item.',
    example: 'Fresh Milk',
    notes: 'Use a name distinct enough to identify the item in reports.',
  },
  {
    name: 'Category',
    required: false,
    type: 'text',
    description: 'High-level grouping (e.g., Dairy, Produce, Bakery).',
    example: 'Dairy',
  },
  {
    name: 'Subcategory',
    required: false,
    type: 'text',
    description: 'Specific grouping within the category.',
    example: 'Milk Products',
  },
  {
    name: 'Unit',
    required: true,
    type: 'text',
    description: 'Unit of measure for stock and usage values.',
    example: 'kg, liter, pcs, pack',
  },
  {
    name: 'Current_Stock',
    required: true,
    type: 'number ≥ 0',
    description: 'Quantity on hand right now, in the unit above.',
    example: '25.5',
    notes: 'Drives days-of-cover and urgency scoring.',
  },
  {
    name: 'Reorder_Level',
    required: false,
    type: 'number ≥ 0',
    description: 'Manual override for reorder threshold. Leave blank to auto-compute.',
    example: '10',
  },
  {
    name: 'Daily_Usage',
    required: true,
    type: 'number > 0',
    description: 'Average quantity consumed per day.',
    example: '5.2',
    notes: 'Drives demand forecasting.',
  },
  {
    name: 'Lead_Time',
    required: true,
    type: 'integer > 0',
    description: 'Days between placing a replenishment order and receiving it.',
    example: '3',
    notes: 'Longer lead times raise the urgency score.',
  },
  {
    name: 'Price_per_Unit',
    required: true,
    type: 'number ≥ 0',
    description: 'Cost paid per unit, in your local currency.',
    example: '4.50',
    notes: 'Used to compute inventory value and waste-cost exposure.',
  },
  {
    name: 'Supplier_Name',
    required: false,
    type: 'text',
    description: 'Vendor name for this item.',
    example: 'Local Farmer',
  },
  {
    name: 'Seasonal_Factor',
    required: true,
    type: 'number ≥ 0',
    description: 'Demand multiplier. 1.0 = normal, > 1.0 = peak season, < 1.0 = quieter.',
    example: '1.0',
    notes: 'Typical range: 0.8 to 1.5.',
  },
  {
    name: 'Waste_Percentage',
    required: true,
    type: '0–100',
    description: 'Percentage of stock recently wasted/spoiled.',
    example: '5',
    notes: 'Drives waste-risk scoring. Required if perishability is not provided separately.',
  },
];

export default function EntryPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [mode, setMode] = useState<'upload' | 'manual' | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showColumnDetails, setShowColumnDetails] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (loading || !user) return;
    if (shouldAutoOpenTour()) {
      setTourOpen(true);
    }
  }, [loading, user]);

  useEffect(() => {
    if (!router.isReady) return;
    const queryMode = router.query.mode;
    const value = Array.isArray(queryMode) ? queryMode[0] : queryMode;
    if (value === 'upload' || value === 'manual') {
      setMode(value);
    }
  }, [router.isReady, router.query.mode]);

  const queryBaseAnalysisId = Array.isArray(router.query.baseAnalysisId)
    ? router.query.baseAnalysisId[0]
    : router.query.baseAnalysisId;

  const getBaseAnalysisId = () => {
    return queryBaseAnalysisId || getLatestAnalysisId();
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!user) {
    return null;
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Please select a CSV file');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await apiClient.uploadCsv(file, getBaseAnalysisId());
      saveLatestAnalysisId(response.analysis_id);
      recordAnalysisInHistory({
        analysisId: response.analysis_id,
        label: file.name,
        source: 'upload',
      });
      toast.success('Analysis created successfully!');
      router.push(`/dashboard/${response.analysis_id}`);
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to upload CSV';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualSubmit = async (items: ManualItemInput[]) => {
    setIsLoading(true);
    setError('');

    try {
      const response = await apiClient.createManualAnalysis(items, getBaseAnalysisId());
      saveLatestAnalysisId(response.analysis_id);
      const previewLabel =
        items.length === 1
          ? items[0].item_name || 'Manual entry'
          : `Manual entry (${items.length} items)`;
      recordAnalysisInHistory({
        analysisId: response.analysis_id,
        label: previewLabel,
        source: 'manual',
      });
      toast.success('Analysis created successfully!');
      router.push(`/dashboard/${response.analysis_id}`);
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to create analysis';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Navigation Bar */}
      <NavigationBar
        onFeatureSelect={setMode}
        activeSection="home"
      />

      <div className="max-w-4xl mx-auto p-4 md:p-8">
        {/* Header */}
        <div className="text-center mb-8 md:mb-12 relative">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">StockWise</h1>
          <p className="text-base md:text-xl text-gray-600">Intelligent Inventory Analysis & Recommendations</p>
          <button
            type="button"
            onClick={() => setTourOpen(true)}
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 hover:underline"
            aria-label="Show quick tour"
          >
            <HelpCircle className="w-4 h-4" />
            How does StockWise work?
          </button>
        </div>

        <GuidedTour open={tourOpen} onClose={() => setTourOpen(false)} />

        {/* Mode Selection or Selected Mode */}
        {!mode ? (
          <>
            {error && (
              <div className="mb-6">
                <Alert type="error" message={error} onClose={() => setError('')} />
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* CSV Upload Option */}
              <Card className="p-8 cursor-pointer hover:shadow-lg transition">
                <button
                  data-testid="csv-upload-card"
                  onClick={() => setMode('upload')}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mb-4">
                    <Upload className="w-6 h-6 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload CSV</h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Upload your inventory CSV file for rapid analysis.
                  </p>
                  <ul className="text-gray-600 text-sm space-y-1">
                    <li>✓ Accepts standard CSV format</li>
                    <li>✓ Fast processing</li>
                    <li>✓ Bulk import capability</li>
                  </ul>
                </button>
              </Card>

              {/* Manual Entry Option */}
              <Card className="p-8 cursor-pointer hover:shadow-lg transition">
                <button
                  onClick={() => setMode('manual')}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mb-4">
                    <FileText className="w-6 h-6 text-green-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Manual Entry</h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Enter inventory items one by one for precise control.
                  </p>
                  <ul className="text-gray-600 text-sm space-y-1">
                    <li>✓ Full control over data</li>
                    <li>✓ Add, duplicate, remove items</li>
                    <li>✓ Validation guidance</li>
                  </ul>
                </button>
              </Card>
            </div>

            {/* CSV Format Help */}
            <div className="mt-12 bg-white rounded-lg p-6 shadow">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">CSV Format Requirements</h3>
                  <p className="text-gray-600 text-sm mt-1">
                    Your CSV must include these 14 columns. Required columns are flagged below.
                  </p>
                </div>
                <a
                  href="/stockwise-example-template.csv"
                  download="stockwise-example-template.csv"
                  className="inline-flex items-center justify-center whitespace-nowrap rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition"
                >
                  Download CSV Template
                </a>
              </div>

              {/* Column reference table */}
              <div className="overflow-x-auto -mx-2 sm:mx-0">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left py-2 px-3 font-semibold text-gray-700">Column</th>
                      <th className="text-left py-2 px-3 font-semibold text-gray-700">Required</th>
                      <th className="text-left py-2 px-3 font-semibold text-gray-700">Type</th>
                      <th className="text-left py-2 px-3 font-semibold text-gray-700">What it means</th>
                      {showColumnDetails && (
                        <th className="text-left py-2 px-3 font-semibold text-gray-700">Example</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {CSV_COLUMNS.map((col) => (
                      <React.Fragment key={col.name}>
                        <tr className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-2 px-3 font-mono text-xs text-gray-900 align-top whitespace-nowrap">
                            {col.name}
                          </td>
                          <td className="py-2 px-3 align-top">
                            {col.required ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700">
                                <CheckCircle2 className="w-3 h-3" />
                                Required
                              </span>
                            ) : (
                              <span className="text-xs text-gray-500">Optional</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-xs text-gray-600 align-top whitespace-nowrap">{col.type}</td>
                          <td className="py-2 px-3 text-gray-700 align-top">
                            <div>{col.description}</div>
                            {showColumnDetails && col.notes && (
                              <div className="text-xs text-gray-500 mt-1 italic">{col.notes}</div>
                            )}
                          </td>
                          {showColumnDetails && (
                            <td className="py-2 px-3 align-top font-mono text-xs text-gray-700 whitespace-nowrap">
                              {col.example}
                            </td>
                          )}
                        </tr>
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Toggle details */}
              <button
                type="button"
                onClick={() => setShowColumnDetails((v) => !v)}
                className="mt-3 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                {showColumnDetails ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Hide examples & notes
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Show examples & notes
                  </>
                )}
              </button>

              {/* Common pitfalls */}
              <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-amber-900 mb-1">Common pitfalls to avoid</p>
                    <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
                      <li>Date must be <span className="font-mono">YYYY-MM-DD</span> (e.g. <span className="font-mono">2026-04-15</span>) — not <span className="font-mono">DD/MM/YYYY</span>.</li>
                      <li>Numeric fields cannot contain currency symbols (use <span className="font-mono">4.50</span>, not <span className="font-mono">RM4.50</span>).</li>
                      <li>Empty rows or stray commas at end of lines will be rejected.</li>
                      <li>Column headers must match exactly — case-sensitive (use the template if unsure).</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : mode === 'upload' ? (
          <div className="space-y-6">
            <Button
              variant="secondary"
              onClick={() => {
                setMode(null);
                if (router.query.mode) {
                  router.replace('/', undefined, { shallow: true });
                }
              }}
            >
              ← Back
            </Button>

            {error && (
              <Alert type="error" message={error} onClose={() => setError('')} />
            )}

            <Card className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Upload CSV</h2>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-900 font-medium mb-2">Drag and drop your CSV file here</p>
                <p className="text-gray-600 text-sm mb-4">or</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  data-testid="csv-file-input"
                  onChange={handleCsvUpload}
                  disabled={isLoading}
                  className="hidden"
                />
                <Button
                  variant="primary"
                  data-testid="select-file-btn"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  loading={isLoading}
                >
                  Select CSV File
                </Button>
              </div>
            </Card>
          </div>
        ) : (
          <div className="space-y-6">
            <Button
              variant="secondary"
              onClick={() => {
                setMode(null);
                if (router.query.mode) {
                  router.replace('/', undefined, { shallow: true });
                }
              }}
            >
              ← Back
            </Button>

            {error && (
              <Alert type="error" message={error} onClose={() => setError('')} />
            )}

            <Card className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Manual Inventory Entry</h2>
              <InventoryItemForm
                onSubmit={handleManualSubmit}
                isLoading={isLoading}
                submitLabel="Create Analysis"
              />
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Upload, FileText, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, HelpCircle, MessageSquare } from 'lucide-react';
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

  const [mode, setMode] = useState<'upload' | 'manual' | 'unstructured' | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showColumnDetails, setShowColumnDetails] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [unstructuredText, setUnstructuredText] = useState('');
  const [extractedItems, setExtractedItems] = useState<any[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);

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
    if (value === 'upload' || value === 'manual' || value === 'unstructured') {
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

  // Existing handlers (unchanged)
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

  // NEW: Unstructured handlers
  const handleExtractUnstructured = async () => {
    if (!unstructuredText.trim()) {
      toast.error('Please paste some text first');
      return;
    }

    setIsExtracting(true);
    setError('');

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/api/v1/unstructured/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: unstructuredText }),
      });

      if (!res.ok) throw new Error('Extraction failed');

      const response = await res.json();

      setExtractedItems((response.extracted_items || []).map((item: any) => ({
        ...item,
        perishability_level: item.perishability_level || 'medium',
      })));
      toast.success(`Extracted ${response.count} items successfully!`);
    } catch (err: any) {
      const message = err.message || 'Extraction failed';
      setError(message);
      toast.error(message);
    } finally {
      setIsExtracting(false);
    }
  };
  
  const handleAddExtractedToAnalysis = async () => {
    if (extractedItems.length === 0) return;

    setIsLoading(true);
    setError('');

    try {
      const response = await apiClient.createManualAnalysis(extractedItems);
      saveLatestAnalysisId(response.analysis_id);

      recordAnalysisInHistory({
        analysisId: response.analysis_id,
        label: `Unstructured input (${extractedItems.length} items)`,
        source: 'unstructured' as any,   // ← Fixed TypeScript error
      });

      toast.success('Analysis created from text input!');
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
      <NavigationBar
        onFeatureSelect={(value) => {
          if (value === 'upload' || value === 'manual' || value === 'unstructured') {
            setMode(value);
          }
        }}
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

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* CSV Upload */}
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
                  <p className="text-gray-600 text-sm mb-4">Upload your inventory CSV file for rapid analysis.</p>
                  <ul className="text-gray-600 text-sm space-y-1">
                    <li>✓ Accepts standard CSV format</li>
                    <li>✓ Fast processing</li>
                    <li>✓ Bulk import capability</li>
                  </ul>
                </button>
              </Card>

              {/* Manual Entry */}
              <Card className="p-8 cursor-pointer hover:shadow-lg transition">
                <button onClick={() => setMode('manual')} className="w-full text-left">
                  <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mb-4">
                    <FileText className="w-6 h-6 text-green-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Manual Entry</h3>
                  <p className="text-gray-600 text-sm mb-4">Enter inventory items one by one for precise control.</p>
                  <ul className="text-gray-600 text-sm space-y-1">
                    <li>✓ Full control over data</li>
                    <li>✓ Add, duplicate, remove items</li>
                    <li>✓ Validation guidance</li>
                  </ul>
                </button>
              </Card>

              {/* Quick Text Input */}
              <Card className="p-8 cursor-pointer hover:shadow-lg transition">
                <button onClick={() => setMode('unstructured')} className="w-full text-left">
                  <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mb-4">
                    <MessageSquare className="w-6 h-6 text-purple-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Quick Text Input</h3>
                  <p className="text-gray-600 text-sm mb-4">Paste WhatsApp messages, supplier notes, or invoices.</p>
                  <ul className="text-gray-600 text-sm space-y-1">
                    <li>✓ AI extracts items automatically</li>
                    <li>✓ Works with messy text</li>
                    <li>✓ Real-world SME friendly</li>
                  </ul>
                </button>
              </Card>
            </div>

            {/* CSV Format Help - THIS SECTION WAS MISSING IN MY PREVIOUS VERSION */}
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
            <Button variant="secondary" onClick={() => setMode(null)}>
              ← Back
            </Button>
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}
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
        ) : mode === 'manual' ? (
          <div className="space-y-6">
            <Button variant="secondary" onClick={() => setMode(null)}>
              ← Back
            </Button>
            {error && <Alert type="error" message={error} onClose={() => setError('')} />}
            <Card className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Manual Inventory Entry</h2>
              <InventoryItemForm onSubmit={handleManualSubmit} isLoading={isLoading} submitLabel="Create Analysis" />
            </Card>
          </div>
          ) : (
          // ==================== Unstructured Mode - Improved ====================
          <div className="space-y-6">
            <Button variant="secondary" onClick={() => { setMode(null); setUnstructuredText(''); setExtractedItems([]); }}>
              ← Back
            </Button>

            {error && <Alert type="error" message={error} onClose={() => setError('')} />}

            <Card className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Quick Text Input</h2>
              <p className="text-gray-500 text-sm mb-6">Paste supplier messages or notes. AI extracts items — you fill in missing required data.</p>

              <textarea
                className="w-full h-40 p-4 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500 resize-none"
                placeholder="Example: Boss we finish the 2kg rice noodle already. Tomorrow need order more. Also milo stock low only 15 packet."
                value={unstructuredText}
                onChange={(e) => setUnstructuredText(e.target.value)}
              />

              <Button
                variant="primary"
                onClick={handleExtractUnstructured}
                disabled={isExtracting || !unstructuredText.trim()}
                loading={isExtracting}
                className="mt-4 w-full"
              >
                {isExtracting ? 'Extracting with AI...' : 'Extract Items with AI'}
              </Button>

              {extractedItems.length > 0 && (
                <div className="mt-10">
                  <h3 className="font-semibold text-lg mb-4">Review & Complete Items</h3>
                  <p className="text-sm text-gray-500 mb-4">
                    Required fields are marked <span className="text-red-500">red</span>. Please fill them before creating analysis.
                  </p>

                  <div className="overflow-x-auto">
                    <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Item Name</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Current Stock</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Unit</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-red-500 cursor-help"
                              title="Typical quantity consumed per day. Drives demand forecasting and reorder timing.">
                            Daily Usage ⓘ
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-red-500 cursor-help"
                              title="Days between placing an order and receiving stock. Used to calculate reorder points.">
                            Lead Time (days) ⓘ
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-red-500 cursor-help"
                              title="Cost of one unit. Used to calculate total inventory value and reorder cost estimates.">
                            Price per Unit ⓘ
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-red-500 cursor-help"
                              title="How quickly this item spoils. Low = dry/canned, Medium = chilled, High = fresh produce/dairy.">
                            Perishability Level ⓘ
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {extractedItems.map((item, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium">{item.item_name}</td>
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                value={item.current_stock || ''}
                                onChange={(e) => {
                                  const newItems = [...extractedItems];
                                  newItems[index].current_stock = parseFloat(e.target.value) || 0;
                                  setExtractedItems(newItems);
                                }}
                                className="w-20 border rounded px-2 py-1 text-center"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <input
                                type="text"
                                value={item.unit || ''}
                                onChange={(e) => {
                                  const newItems = [...extractedItems];
                                  newItems[index].unit = e.target.value;
                                  setExtractedItems(newItems);
                                }}
                                className="w-20 border rounded px-2 py-1 text-center"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                value={item.usage_value || ''}
                                onChange={(e) => {
                                  const newItems = [...extractedItems];
                                  newItems[index].usage_value = parseFloat(e.target.value) || 0;
                                  setExtractedItems(newItems);
                                }}
                                className="w-20 border rounded px-2 py-1 text-center"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                value={item.lead_time_days || ''}
                                onChange={(e) => {
                                  const newItems = [...extractedItems];
                                  newItems[index].lead_time_days = parseFloat(e.target.value) || 0;
                                  setExtractedItems(newItems);
                                }}
                                className="w-20 border rounded px-2 py-1 text-center"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                value={item.price_per_unit || ''}
                                onChange={(e) => {
                                  const newItems = [...extractedItems];
                                  newItems[index].price_per_unit = parseFloat(e.target.value) || 0;
                                  setExtractedItems(newItems);
                                }}
                                className="w-20 border rounded px-2 py-1 text-center"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <select
                                value={item.perishability_level || 'medium'}
                                onChange={(e) => {
                                  const newItems = [...extractedItems];
                                  newItems[index].perishability_level = e.target.value;
                                  setExtractedItems(newItems);
                                }}
                                className="border rounded px-2 py-1 text-sm"
                              >
                                <option value="low">Low – Dry/canned</option>
                                <option value="medium">Medium – Chilled</option>
                                <option value="high">High – Fresh/dairy</option>
                              </select>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <Button
                    variant="primary"
                    onClick={handleAddExtractedToAnalysis}
                    loading={isLoading}
                    disabled={extractedItems.some(item =>
                      !item.usage_value || item.usage_value <= 0 ||
                      !item.lead_time_days || item.lead_time_days <= 0 ||
                      !item.price_per_unit || item.price_per_unit <= 0 ||
                      !item.perishability_level
                    )}
                    className="mt-8 w-full"
                  >
                    Add All Items to Analysis
                  </Button>

                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
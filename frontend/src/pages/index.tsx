import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Upload, FileText, MessageSquare } from 'lucide-react';
import { Button, Alert, Card } from '@/components/common';
import { InventoryItemForm } from '@/components/InventoryItemForm';
import { NavigationBar } from '@/components/Dashboard';
import { apiClient } from '@/services/api';
import { getLatestAnalysisId, recordAnalysisInHistory, saveLatestAnalysisId } from '@/lib/analysisSession';
import { ManualItemInput } from '@/types';
import { useAuth } from '@/lib/auth';
import toast from 'react-hot-toast';

export default function EntryPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [mode, setMode] = useState<'upload' | 'manual' | 'unstructured' | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
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
      const res = await fetch('http://localhost:8000/api/v1/unstructured/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: unstructuredText }),
      });

      if (!res.ok) throw new Error('Extraction failed');

      const response = await res.json();

      setExtractedItems(response.extracted_items || []);
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
        <div className="text-center mb-8 md:mb-12">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">StockWise</h1>
          <p className="text-base md:text-xl text-gray-600">Intelligent Inventory Analysis & Recommendations</p>
        </div>

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
              <h3 className="text-lg font-semibold text-gray-900 mb-4">CSV Format Requirements</h3>
              <p className="text-gray-600 mb-4">Your CSV file should include the following columns:</p>
              <div className="bg-gray-50 p-4 rounded border border-gray-200 overflow-x-auto">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words">
                  Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage
                </pre>
              </div>
              <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <p className="text-gray-600 text-sm">
                  * All 14 columns are required. Date should be in YYYY-MM-DD format. Numeric fields must contain valid numbers.
                </p>
              </div>
              <a
                href="/stockwise-example-template.csv"
                download="stockwise-example-template.csv"
                className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition mt-6"
              >
                Download CSV Template
              </a>
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
          // Unstructured mode
          <div className="space-y-6">
            <Button variant="secondary" onClick={() => { setMode(null); setUnstructuredText(''); setExtractedItems([]); }}>
              ← Back
            </Button>

            {error && <Alert type="error" message={error} onClose={() => setError('')} />}

            <Card className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Quick Text Input</h2>
              <p className="text-gray-600 mb-6">Paste supplier WhatsApp messages, notes, or invoices below. AI will extract items automatically.</p>

              <textarea
                className="w-full h-40 p-4 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500 resize-none"
                placeholder="Example: Supplier say fresh milk price up next week. Delivery delay 2 days. We have 20L left. Eggs 5 dozen at RM 8 per dozen."
                value={unstructuredText}
                onChange={(e) => setUnstructuredText(e.target.value)}
              />

              <Button
                variant="primary"
                onClick={handleExtractUnstructured}
                disabled={isExtracting || !unstructuredText.trim()}
                loading={isExtracting}
                className="mt-6 w-full"
              >
                {isExtracting ? 'Extracting with AI...' : 'Extract Items with AI'}
              </Button>

              {extractedItems.length > 0 && (
                <div className="mt-8">
                  <h3 className="font-semibold text-lg mb-4">Extracted {extractedItems.length} items</h3>
                  <div className="max-h-80 overflow-auto border rounded-lg p-4 bg-gray-50">
                    {extractedItems.map((item, index) => (
                      <div key={index} className="py-2 border-b last:border-none flex justify-between">
                        <span className="font-medium">{item.item_name}</span>
                        <span className="text-gray-600">{item.current_stock} {item.unit}</span>
                      </div>
                    ))}
                  </div>

                  <Button
                    variant="primary"
                    onClick={handleAddExtractedToAnalysis}
                    loading={isLoading}
                    className="mt-6 w-full"
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
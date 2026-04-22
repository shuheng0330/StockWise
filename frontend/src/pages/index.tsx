import React, { useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Upload, FileText } from 'lucide-react';
import { Button, Alert, Card } from '@/components/common';
import { InventoryItemForm } from '@/components/InventoryItemForm';
import { NavigationBar } from '@/components/Dashboard';
import { apiClient } from '@/services/api';
import { saveLatestAnalysisId } from '@/lib/analysisSession';
import { ManualItemInput } from '@/types';
import toast from 'react-hot-toast';

export default function EntryPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'upload' | 'manual' | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const response = await apiClient.uploadCsv(file);
      saveLatestAnalysisId(response.analysis_id);
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
      const response = await apiClient.createManualAnalysis(items);
      saveLatestAnalysisId(response.analysis_id);
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
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">StockWise</h1>
          <p className="text-xl text-gray-600">Intelligent Inventory Analysis & Recommendations</p>
        </div>

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
              <h3 className="text-lg font-semibold text-gray-900 mb-4">CSV Format Requirements</h3>
              <p className="text-gray-600 mb-4">
                Your CSV file should include the following columns:
              </p>
              <div className="bg-gray-50 P-4 rounded border border-gray-200 overflow-x-auto">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words">
                  Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage
                </pre>
              </div>
              <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <p className="text-gray-600 text-sm">
                  * All 14 columns are required. Date should be in YYYY-MM-DD format. Numeric fields must contain valid numbers.
                </p>
              </div>
              <div className="mt-4"></div>
              <a
                href="/stockwise-example-template.csv"
                download="stockwise-example-template.csv"
                className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition"
              >
                Download CSV Template
              </a>
            </div>
          </>
        ) : mode === 'upload' ? (
          <div className="space-y-6">
            <Button
              variant="secondary"
              onClick={() => setMode(null)}
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
                  onChange={handleCsvUpload}
                  disabled={isLoading}
                  className="hidden"
                />
                <Button
                  variant="primary"
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
              onClick={() => setMode(null)}
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

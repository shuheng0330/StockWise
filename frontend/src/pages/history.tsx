import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Clock, FileText, Upload } from 'lucide-react';
import toast from 'react-hot-toast';
import { Alert, Badge, Button, Card } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import {
  AnalysisHistoryEntry,
  clearAnalysisHistory,
  getAnalysisHistory,
  subscribeToAnalysisHistory,
} from '@/lib/analysisSession';

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString();
  } catch {
    return iso;
  }
}

function sourceBadge(source: AnalysisHistoryEntry['source']) {
  if (source === 'upload') {
    return <Badge label="CSV Upload" variant="info" />;
  }
  if (source === 'manual') {
    return <Badge label="Manual Entry" variant="success" />;
  }
  return <Badge label="Entry" variant="warning" />;
}

function sourceIcon(source: AnalysisHistoryEntry['source']) {
  if (source === 'upload') {
    return <Upload className="w-5 h-5 text-blue-600" />;
  }
  if (source === 'manual') {
    return <FileText className="w-5 h-5 text-green-600" />;
  }
  return <Clock className="w-5 h-5 text-amber-600" />;
}

export default function HistoryPage() {
  const [history, setHistory] = useState<AnalysisHistoryEntry[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHistory(getAnalysisHistory());
    setHydrated(true);
    const unsubscribe = subscribeToAnalysisHistory(setHistory);
    return () => unsubscribe();
  }, []);

  const handleClear = () => {
    if (history.length === 0) return;
    if (!confirm('Clear all entry history? This cannot be undone.')) return;
    clearAnalysisHistory();
    setHistory([]);
    toast.success('History cleared');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationBar onFeatureSelect={() => { }} activeSection="history" />

      <div className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Entry History</h1>
            <p className="text-gray-600 mt-1 text-sm md:text-base">
              A log of every CSV upload and manual entry submitted from this browser.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/">
              <Button variant="secondary">New Entry</Button>
            </Link>
            <Button variant="outline" onClick={handleClear} disabled={history.length === 0}>
              Clear History
            </Button>
          </div>
        </div>

        {hydrated && history.length === 0 ? (
          <Alert
            type="info"
            title="No entries yet"
            message="Upload a CSV or submit a manual entry — each one will be logged here."
          />
        ) : (
          <div className="grid gap-3">
            {history.map((entry) => (
              <Card key={entry.analysisId} className="p-4 md:p-5">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="flex items-center justify-center w-10 h-10 bg-gray-100 rounded-lg flex-shrink-0">
                      {sourceIcon(entry.source)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-gray-900 truncate">
                          {entry.label || 'Entry'}
                        </p>
                        {sourceBadge(entry.source)}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatTimestamp(entry.createdAt)}
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

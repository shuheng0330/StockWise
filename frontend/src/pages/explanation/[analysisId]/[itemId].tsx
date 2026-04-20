import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Button, Card, Alert } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { ExplanationDrawer } from '@/components/ExplanationDrawer';
import { apiClient } from '@/services/api';
import { ExplanationResponse } from '@/types';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function ExplanationPage() {
  const router = useRouter();
  const { analysisId, itemId, simulated } = router.query;

  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [showDrawer, setShowDrawer] = useState(true);

  useEffect(() => {
    if (!analysisId || !itemId) return;
    fetchExplanation();
  }, [analysisId, itemId, simulated]);

  const fetchExplanation = async () => {
    setIsLoading(true);
    setError('');

    try {
      const request = simulated ? { simulated_order_qty: parseFloat(simulated as string) } : undefined;
      const result = await apiClient.getExplanation(
        analysisId as string,
        itemId as string,
        request
      );
      setExplanation(result);
      toast.success('Explanation loaded');
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to fetch explanation';
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
          <p className="text-gray-600">Loading explanation...</p>
        </div>
      </div>
    );
  }

  if (error || !explanation) {
    return (
      <div className="min-h-screen bg-gray-50 p-4 md:p-8">
        <div className="max-w-4xl mx-auto">
          <Link href={`/dashboard/${analysisId}`}>
            <Button variant="secondary" className="mb-6">
              ← Back to Dashboard
            </Button>
          </Link>
          <Alert type="error" title="Error" message={error || 'Explanation not found'} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <NavigationBar
        onFeatureSelect={() => {}} // Not used in analysis pages
        currentAnalysisId={analysisId as string}
        activeSection="explanation"
      />

      {showDrawer && (
        <ExplanationDrawer
          explanation={explanation}
          onClose={() => {
            setShowDrawer(false);
            router.back();
          }}
        />
      )}

      {!showDrawer && (
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-8">
          <Link href={`/dashboard/${analysisId}`}>
            <Button variant="secondary">Back to Dashboard</Button>
          </Link>
        </div>
      )}
    </div>
  );
}

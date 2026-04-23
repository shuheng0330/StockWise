import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Button, Card, Alert } from '@/components/common';
import { NavigationBar } from '@/components/Dashboard';
import { ItemSimulation } from '@/components/ItemSimulation';
import { apiClient } from '@/services/api';
import { findInventoryItemByRouteId } from '@/lib/itemIdentity';
import { buildSimulatedExplanationHref, runSimulationAndStore } from '@/lib/simulationFlow';
import { InventoryItem, SimulationResponse } from '@/types';
import Link from 'next/link';
import toast from 'react-hot-toast';

export default function SimulationPage() {
  const router = useRouter();
  const { analysisId, itemId } = router.query;

  const [item, setItem] = useState<InventoryItem | null>(null);
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!analysisId || !itemId) return;
    fetchItem();
  }, [analysisId, itemId]);

  const fetchItem = async () => {
    setIsLoading(true);
    setError('');

    try {
      const analysis = await apiClient.getAnalysis(analysisId as string);
      const foundItem = findInventoryItemByRouteId(analysis.items, itemId);

      if (!foundItem) {
        setError('Item not found');
        toast.error('Item not found');
        return;
      }

      setItem(foundItem);
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Failed to fetch item';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSimulate = async (qty: number) => {
    setIsSimulating(true);

    try {
      const result = await runSimulationAndStore(
        qty,
        (simulatedOrderQty) =>
          apiClient.simulate(
            analysisId as string,
            itemId as string,
            { simulated_order_qty: simulatedOrderQty }
          ),
        setSimulationResult
      );
      toast.success('Simulation completed');
      return result;
    } catch (err: any) {
      const message = err.response?.data?.message || err.message || 'Simulation failed';
      toast.error(message);
      throw err;
    } finally {
      setIsSimulating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading item details...</p>
        </div>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="min-h-screen bg-gray-50 p-4 md:p-8">
        <div className="max-w-4xl mx-auto">
          <Link href={`/dashboard/${analysisId}`}>
            <Button variant="secondary" className="mb-6">
              ← Back to Dashboard
            </Button>
          </Link>
          <Alert type="error" title="Error" message={error || 'Item not found'} />
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
        currentItemId={itemId as string}
        activeSection="simulation"
      />

      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Simulation</h1>
              <p className="text-gray-600 mt-1">{item.item_name}</p>
            </div>
            <Link href={`/dashboard/${analysisId}`}>
              <Button variant="secondary">Back to Dashboard</Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-8">
        <Card className="p-8">
          <ItemSimulation
            item={item}
            analysisId={analysisId as string}
            onSimulate={handleSimulate}
            isLoading={isSimulating}
          />
        </Card>

        {simulationResult && (
          <div className="mt-6">
            <Link href={buildSimulatedExplanationHref(analysisId, itemId, simulationResult.simulated_order_qty)}>
              <Button variant="primary" size="lg" className="w-full">
                Get Explanation for Simulated Result
              </Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

import React from 'react';
import { ExplanationResponse } from '@/types';
import { AlertCircle, CheckCircle, AlertTriangle, Info } from 'lucide-react';

interface ExplanationDrawerProps {
  explanation: ExplanationResponse;
  onClose: () => void;
}

export function ExplanationDrawer({ explanation, onClose }: ExplanationDrawerProps) {
  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'live':
        return 'bg-green-100 text-green-800';
      case 'mock':
        return 'bg-blue-100 text-blue-800';
      case 'fallback':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'RESTOCK_NOW':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'BUY_LESS':
        return 'text-amber-600 bg-amber-50 border-amber-200';
      case 'DELAY_PURCHASE':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'MONITOR_CLOSELY':
        return 'text-green-600 bg-green-50 border-green-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const PriorityIcon = {
    HIGH: <AlertCircle className="w-5 h-5 text-red-600" />,
    MEDIUM: <AlertTriangle className="w-5 h-5 text-yellow-600" />,
    LOW: <Info className="w-5 h-5 text-blue-600" />,
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-end md:items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b p-6 flex justify-between items-start gap-4">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">{explanation.item_name}</h2>
            <div className="flex gap-3 flex-wrap items-center">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getActionColor(explanation.recommended_action)} border`}>
                {explanation.recommended_action}
              </span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSourceBadgeColor(explanation.source)}`}>
                Source: {explanation.source.charAt(0).toUpperCase() + explanation.source.slice(1)}
              </span>
              <div className="flex items-center gap-1">
                {PriorityIcon[explanation.priority_level]}
                <span className="text-sm font-medium capitalize text-gray-700">
                  {explanation.priority_level.toLowerCase()} Priority
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Warning Flag */}
          {explanation.warning_flag && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900">Warning</p>
                <p className="text-red-800 text-sm mt-1">
                  This recommendation requires special attention. Please review carefully.
                </p>
              </div>
            </div>
          )}

          {/* Short Reason */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Quick Summary</h3>
            <p className="text-gray-700 bg-gray-50 rounded p-3 border border-gray-200">
              {explanation.short_reason}
            </p>
          </div>

          {/* Decision Explanation */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Decision Explanation</h3>
            <p className="text-gray-700 leading-relaxed">{explanation.decision_explanation}</p>
          </div>

          {/* Tradeoff Summary */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">Trade-offs to Consider</h3>
            <p className="text-blue-900 leading-relaxed">{explanation.tradeoff_summary}</p>
          </div>

          {/* Suggested Next Step */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h3 className="font-semibold text-green-900 mb-2">Suggested Next Step</h3>
            <p className="text-green-900 leading-relaxed">{explanation.suggested_next_step}</p>
          </div>

          {/* Confidence Note */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Confidence Note</h3>
            <p className="text-gray-700 text-sm italic">{explanation.confidence_note}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t p-6 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-300 text-gray-900 rounded-lg hover:bg-gray-400 font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

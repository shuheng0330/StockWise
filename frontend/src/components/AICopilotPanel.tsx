import React, { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, Bot, MessageSquare, Send, Sparkles } from 'lucide-react';

import { Alert, Button, Card } from '@/components/common';
import { AI_COPILOT_STARTER_PROMPTS, buildInitialCopilotRequest, buildNextCopilotRequest } from '@/lib/aiCopilot';
import { ChatMessage, ChatRequest, ChatResponse, ChatSimulationContext, RecommendedAction } from '@/types';


type ConversationEntry =
  | { kind: 'user'; content: string }
  | { kind: 'assistant'; response: ChatResponse };

interface AICopilotPanelProps {
  analysisId: string;
  onSendMessage: (request: ChatRequest) => Promise<ChatResponse>;
  initialPrompt?: string;
  initialSimulationContext?: ChatSimulationContext;
}

function getActionColor(action: RecommendedAction) {
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
}

function getSourceBadgeColor(source: ChatResponse['source']) {
  switch (source) {
    case 'live':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    case 'mock':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'fallback':
      return 'bg-amber-100 text-amber-800 border-amber-200';
  }
}

export function AICopilotPanel({
  analysisId,
  onSendMessage,
  initialPrompt,
  initialSimulationContext,
}: AICopilotPanelProps) {
  const [entries, setEntries] = useState<ConversationEntry[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [isSending, setIsSending] = useState(false);
  const initialPromptSent = useRef(false);

  const recentMessages = useMemo<ChatMessage[]>(
    () =>
      entries
        .map((entry) =>
          entry.kind === 'user'
            ? ({ role: 'user', content: entry.content } as const)
            : ({ role: 'assistant', content: entry.response.answer } as const)
        )
        .slice(-4),
    [entries]
  );

  const submitMessage = async (message: string, simulationContext?: ChatSimulationContext) => {
    const normalizedMessage = message.trim();
    if (!normalizedMessage) {
      return;
    }

    setIsSending(true);
    setError('');
    setEntries((current) => [...current, { kind: 'user', content: normalizedMessage }]);

    try {
      const request =
        entries.length === 0 && simulationContext
          ? buildInitialCopilotRequest(normalizedMessage, simulationContext)
          : buildNextCopilotRequest(normalizedMessage, recentMessages, simulationContext);
      const response = await onSendMessage(request);
      setEntries((current) => [...current, { kind: 'assistant', response }]);
      setDraft('');
    } catch (err: any) {
      const message = err?.response?.data?.message || err?.message || 'Unable to reach AI Copilot right now.';
      setError(message);
    } finally {
      setIsSending(false);
    }
  };

  useEffect(() => {
    if (!initialPrompt || initialPromptSent.current) {
      return;
    }
    initialPromptSent.current = true;
    submitMessage(initialPrompt, initialSimulationContext);
  }, [initialPrompt, initialSimulationContext]);

  const starterPrompts = initialSimulationContext
    ? ['What changed after my simulation?', 'Should I still order today?', 'How does this affect waste risk?']
    : AI_COPILOT_STARTER_PROMPTS;

  return (
    <Card className="overflow-hidden border border-slate-200 shadow-sm">
      <div className="bg-slate-950 text-white p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sky-300 mb-2">
              <Sparkles className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-[0.18em]">AI Copilot</span>
            </div>
            <h2 className="text-2xl font-bold">Ask StockWise what to do next</h2>
            <p className="text-slate-300 mt-2 max-w-3xl">
              Get a grounded answer from the current analysis{initialSimulationContext ? ' and your latest simulation' : ''}.
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/70 px-3 py-1.5 text-sm text-slate-300">
            <Bot className="w-4 h-4" />
            <span>Analysis {analysisId}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mt-5">
          {starterPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => submitMessage(prompt, initialSimulationContext)}
              className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-sm text-slate-100 transition hover:border-sky-400 hover:text-sky-200"
              disabled={isSending}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-[1.2fr,0.8fr]">
        <div className="space-y-4">
          {error && <Alert type="error" title="AI Copilot" message={error} />}

          {entries.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-slate-600">
              <div className="flex items-center gap-2 font-medium text-slate-900">
                <MessageSquare className="w-4 h-4" />
                <span>Start with a question or use one of the prompt chips above.</span>
              </div>
            </div>
          ) : (
            entries.map((entry, index) =>
              entry.kind === 'user' ? (
                <div key={`user-${index}`} className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">You</p>
                  <p className="mt-1 text-slate-900">{entry.content}</p>
                </div>
              ) : (
                <div key={`assistant-${index}`} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${getSourceBadgeColor(entry.response.source)}`}>
                      {entry.response.source}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700">
                      {entry.response.scope}
                    </span>
                  </div>

                  <p className="text-lg font-semibold text-slate-950">{entry.response.answer}</p>

                  {entry.response.warning_flag && (
                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 mt-0.5" />
                        <p>{entry.response.warning_flag}</p>
                      </div>
                    </div>
                  )}

                  <div className="mt-5 grid gap-5 lg:grid-cols-2">
                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Supporting Points</h3>
                      <ul className="mt-3 space-y-2 text-sm text-slate-700">
                        {entry.response.supporting_points.map((point) => (
                          <li key={point} className="rounded-lg bg-slate-50 px-3 py-2">
                            {point}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Related Items</h3>
                      <div className="mt-3 space-y-2">
                        {entry.response.related_items.map((item) => (
                          <Link
                            key={`${entry.response.answer}-${item.item_id}`}
                            href={`/simulation/${analysisId}/${item.item_id}`}
                            className="block rounded-lg border border-slate-200 bg-white px-3 py-3 transition hover:border-sky-300 hover:bg-sky-50"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="font-semibold text-slate-900">{item.item_name}</p>
                              <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${getActionColor(item.recommended_action)}`}>
                                {item.recommended_action.replace('_', ' ')}
                              </span>
                            </div>
                            <p className="mt-2 text-sm text-slate-600">{item.reason}</p>
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Suggested Follow-Ups</h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {entry.response.suggested_follow_ups.map((prompt) => (
                        <button
                          key={`${entry.response.answer}-${prompt}`}
                          type="button"
                          onClick={() => submitMessage(prompt, initialSimulationContext)}
                          className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1.5 text-sm text-slate-800 transition hover:border-sky-300 hover:bg-sky-50"
                          disabled={isSending}
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )
            )
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <label className="block text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">
            Ask a Question
          </label>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask about restocking, waste risk, delay candidates, or what changed after a simulation."
            className="mt-3 min-h-[180px] w-full resize-none rounded-lg border border-slate-300 bg-white px-3 py-3 text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200"
          />
          <div className="mt-4 flex flex-col gap-2">
            <Button
              type="button"
              onClick={() => submitMessage(draft, initialSimulationContext)}
              loading={isSending}
              className="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap"
            >
              <Send className="w-4 h-4" />
              <span>Ask AI</span>
            </Button>
            <p className="text-sm text-slate-500 text-center">
              The copilot stays inside the current analysis and won’t use outside business data.
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}

import { AlertTriangle, Bot, MessageSquare, RefreshCw, Send, Sparkles, X } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';

import { Alert, Button } from '@/components/common';
import { AI_ADVISOR_STARTER_PROMPTS, buildInitialAdvisorRequest, buildNextAdvisorRequest } from '@/lib/aiAdvisor';
import { ChatMessage, ChatRequest, ChatResponse, ChatSimulationContext, RecommendedAction } from '@/types';

const AUTO_PROMPT_DEDUPE_KEY = 'stockwise.aiAdvisor.autoPrompt';
const AUTO_PROMPT_DEDUPE_WINDOW_MS = 10_000;

type ConversationEntry =
  | { kind: 'user'; content: string }
  | { kind: 'assistant'; response: ChatResponse };

interface AIAdvisorPanelProps {
  analysisId: string;
  onSendMessage: (request: ChatRequest, options?: { refresh?: boolean }) => Promise<ChatResponse>;
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

export function AIAdvisorPanel({
  analysisId,
  onSendMessage,
  initialPrompt,
  initialSimulationContext,
}: AIAdvisorPanelProps) {
  const [entries, setEntries] = useState<ConversationEntry[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isOpen, setIsOpen] = useState(Boolean(initialPrompt));
  const [showLauncherHint, setShowLauncherHint] = useState(true);
  const initialPromptSent = useRef(false);

  const storageKey = useMemo(() => {
    const simulationKey = initialSimulationContext
      ? `${initialSimulationContext.item_id}:${initialSimulationContext.simulated_order_qty}`
      : 'analysis';
    return `stockwise.aiAdvisor.${analysisId}.${simulationKey}`;
  }, [analysisId, initialSimulationContext?.item_id, initialSimulationContext?.simulated_order_qty]);

  const autoPromptSignature = useMemo(() => {
    const normalizedInitialPrompt = initialPrompt?.trim();
    if (!normalizedInitialPrompt) {
      return '';
    }
    return `${storageKey}:${normalizedInitialPrompt}`;
  }, [initialPrompt, storageKey]);

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

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const cached = window.sessionStorage.getItem(storageKey);
    if (!cached) {
      setEntries([]);
      initialPromptSent.current = false;
      return;
    }
    try {
      const restored = JSON.parse(cached) as ConversationEntry[];
      setEntries(restored);
      initialPromptSent.current = restored.length > 0;
    } catch {
      window.sessionStorage.removeItem(storageKey);
      setEntries([]);
      initialPromptSent.current = false;
    }
  }, [storageKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (entries.length === 0) {
      window.sessionStorage.removeItem(storageKey);
      return;
    }
    window.sessionStorage.setItem(storageKey, JSON.stringify(entries));
  }, [entries, storageKey]);

  const submitMessage = async (
    message: string,
    simulationContext?: ChatSimulationContext,
    options?: { refresh?: boolean }
  ) => {
    const normalizedMessage = message.trim();
    if (!normalizedMessage) {
      return;
    }

    setIsOpen(true);
    setIsSending(true);
    setError('');
    setEntries((current) => [...current, { kind: 'user', content: normalizedMessage }]);

    try {
      const request =
        entries.length === 0 && simulationContext
          ? buildInitialAdvisorRequest(normalizedMessage, simulationContext)
          : buildNextAdvisorRequest(normalizedMessage, recentMessages, simulationContext);
      const response = await onSendMessage(request, options);
      setEntries((current) => [...current, { kind: 'assistant', response }]);
      setDraft('');
    } catch (err: any) {
      const message = err?.response?.data?.message || err?.message || 'Unable to reach AI Advisor right now.';
      setError(message);
    } finally {
      setIsSending(false);
    }
  };

  useEffect(() => {
    if (!initialPrompt || initialPromptSent.current) {
      return;
    }

    if (typeof window !== 'undefined' && autoPromptSignature) {
      try {
        const raw = window.sessionStorage.getItem(AUTO_PROMPT_DEDUPE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as { signature?: string; timestamp?: number };
          if (
            parsed.signature === autoPromptSignature
            && Number.isFinite(parsed.timestamp)
            && Date.now() - Number(parsed.timestamp) < AUTO_PROMPT_DEDUPE_WINDOW_MS
          ) {
            initialPromptSent.current = true;
            return;
          }
        }
        window.sessionStorage.setItem(
          AUTO_PROMPT_DEDUPE_KEY,
          JSON.stringify({ signature: autoPromptSignature, timestamp: Date.now() })
        );
      } catch {
        // Ignore storage parsing failures; fallback behavior is a normal auto-send.
      }
    }

    initialPromptSent.current = true;
    setIsOpen(true);
    submitMessage(initialPrompt, initialSimulationContext);
  }, [initialPrompt, initialSimulationContext, autoPromptSignature]);

  const retryAssistantResponse = (assistantIndex: number) => {
    const previousUser = [...entries]
      .slice(0, assistantIndex)
      .reverse()
      .find((entry): entry is { kind: 'user'; content: string } => entry.kind === 'user');
    if (!previousUser) {
      return;
    }
    submitMessage(previousUser.content, initialSimulationContext, { refresh: true });
  };

  const starterPrompts = initialSimulationContext
    ? ['What changed after my simulation?', 'Should I still order today?', 'How does this affect waste risk?']
    : AI_ADVISOR_STARTER_PROMPTS;

  return (
    <>
      {!isOpen && (
        <div className="fixed bottom-5 right-5 z-40 flex max-w-[calc(100vw-2.5rem)] items-end gap-3">
          {showLauncherHint && (
            <div className="relative hidden max-w-xs rounded-lg border border-slate-200 bg-white px-4 py-3 pr-9 text-sm text-slate-700 shadow-lg sm:block">
              <button
                type="button"
                onClick={() => setShowLauncherHint(false)}
                className="absolute right-2 top-2 rounded-full p-0.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                aria-label="Dismiss AI Advisor suggestion"
              >
                <X className="h-3.5 w-3.5" />
              </button>
              <p className="font-semibold text-slate-950">Need help choosing?</p>
              <p className="mt-1">Ask the AI Advisor about restocks, waste risk, or delay candidates.</p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setIsOpen(true)}
            className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-xl transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-300"
            aria-label="Open AI Advisor"
          >
            <Bot className="h-5 w-5" />
            <span>AI Advisor</span>
          </button>
        </div>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-end bg-slate-950/40 p-3 md:p-6">
          <div className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl">
            <div className="border-b border-slate-200 bg-slate-950 px-4 py-3 text-white md:px-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-sky-300">
                    <Sparkles className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">AI Advisor</span>
                  </div>
                  <h2 className="mt-0.5 text-lg font-bold md:text-xl">Ask what to do next</h2>
                  <p className="mt-0.5 text-[13px] text-slate-300 md:text-sm">
                    Grounded in this analysis{initialSimulationContext ? ' and your latest simulation' : ''}.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="rounded-full p-0.5 text-slate-300 transition hover:bg-slate-800 hover:text-white"
                  aria-label="Close AI Advisor"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => submitMessage(prompt, initialSimulationContext)}
                    className="rounded-full border border-slate-700 bg-slate-900/70 px-2.5 py-1 text-xs text-slate-100 transition hover:border-sky-400 hover:text-sky-200 sm:text-sm"
                    disabled={isSending}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto bg-slate-50 p-5 md:p-6">
              {error && <Alert type="error" title="AI Advisor" message={error} />}

              {entries.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-slate-600">
                  <div className="flex items-center gap-2 font-medium text-slate-900">
                    <MessageSquare className="h-4 w-4" />
                    <span>Start with a question or use one of the prompt chips above.</span>
                  </div>
                </div>
              ) : (
                entries.map((entry, index) =>
                  entry.kind === 'user' ? (
                    <div key={`user-${index}`} className="ml-auto max-w-[85%] rounded-lg border border-sky-200 bg-sky-50 px-4 py-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">You</p>
                      <p className="mt-1 text-slate-900">{entry.content}</p>
                    </div>
                  ) : (
                    <div key={`assistant-${index}`} className="max-w-[96%] rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                      <div className="mb-3 flex flex-wrap items-center gap-2">
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${getSourceBadgeColor(entry.response.source)}`}>
                          {entry.response.source}
                        </span>
                        <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700">
                          {entry.response.scope}
                        </span>
                        {entry.response.source === 'fallback' && (
                          <button
                            type="button"
                            onClick={() => retryAssistantResponse(index)}
                            className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700 transition hover:border-sky-300 hover:bg-sky-50"
                            disabled={isSending}
                          >
                            <RefreshCw className="h-3.5 w-3.5" />
                            Retry AI
                          </button>
                        )}
                      </div>

                      <p className="text-lg font-semibold leading-relaxed text-slate-950">{entry.response.answer}</p>

                      {entry.response.warning_flag && (
                        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-base text-amber-900">
                          <div className="flex items-start gap-2">
                            <AlertTriangle className="mt-0.5 h-4 w-4" />
                            <p>{entry.response.warning_flag}</p>
                          </div>
                        </div>
                      )}

                      <div className="mt-5 grid gap-4 md:grid-cols-2">
                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Supporting Points</h3>
                          <ul className="mt-3 space-y-2.5 text-base text-slate-700">
                            {entry.response.supporting_points.map((point) => (
                              <li key={point} className="rounded-lg bg-slate-50 px-4 py-2.5">
                                {point}
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Related Items</h3>
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
                                <p className="mt-2 text-base text-slate-600">{item.reason}</p>
                              </Link>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="mt-5">
                        <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Suggested Follow-Ups</h3>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {entry.response.suggested_follow_ups.map((prompt) => (
                            <button
                              key={`${entry.response.answer}-${prompt}`}
                              type="button"
                              onClick={() => submitMessage(prompt, initialSimulationContext)}
                              className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1.5 text-base text-slate-800 transition hover:border-sky-300 hover:bg-sky-50"
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

            <div className="border-t border-slate-200 bg-white p-3.5 md:p-4">
              <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 md:text-xs">
                Ask the AI Advisor
              </label>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask about restocking, waste risk, delay candidates, or what changed after a simulation."
                className="mt-1.5 min-h-[64px] w-full resize-none rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-200 md:min-h-[72px]"
              />
              <div className="mt-2.5 flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-slate-500 md:text-sm">
                  Stays inside the current analysis and avoids outside business data.
                </p>
                <Button
                  type="button"
                  onClick={() => submitMessage(draft, initialSimulationContext)}
                  loading={isSending}
                  className="inline-flex items-center justify-center gap-2 whitespace-nowrap"
                >
                  <Send className="h-4 w-4" />
                  <span>Ask AI</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Backward-compatible alias for older Copilot component naming.
export const AICopilotPanel = AIAdvisorPanel;

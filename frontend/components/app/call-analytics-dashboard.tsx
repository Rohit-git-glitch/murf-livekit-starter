'use client';

import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, BarChart3, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

type CallAnalytics = {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
};

interface CallAnalyticsDashboardProps {
  onBack: () => void;
}

export function CallAnalyticsDashboard({ onBack }: CallAnalyticsDashboardProps) {
  const [analytics, setAnalytics] = useState<CallAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadAnalytics = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/analytics', { cache: 'no-store' });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? 'Unable to load call analytics.');
      }

      setAnalytics(data);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to load call analytics.');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAnalytics(true);
    const intervalId = setInterval(() => {
      void loadAnalytics(false);
    }, 3000);
    return () => clearInterval(intervalId);
  }, [loadAnalytics]);

  const metrics = [
    {
      label: 'Total Calls',
      value: analytics?.total_calls,
      icon: BarChart3,
      tone: 'text-teal-700 dark:text-teal-300',
      background: 'bg-teal-50 dark:bg-teal-950/50',
    },
    {
      label: 'Successful Calls',
      value: analytics?.successful_calls,
      icon: CheckCircle2,
      tone: 'text-emerald-700 dark:text-emerald-300',
      background: 'bg-emerald-50 dark:bg-emerald-950/50',
    },
    {
      label: 'Failed Calls',
      value: analytics?.failed_calls,
      icon: XCircle,
      tone: 'text-rose-700 dark:text-rose-300',
      background: 'bg-rose-50 dark:bg-rose-950/50',
    },
  ];

  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-gradient-to-b from-teal-50 via-slate-50 to-emerald-50 p-4 text-slate-800 sm:p-6 dark:from-slate-950 dark:via-slate-900 dark:to-teal-950 dark:text-slate-100">
      <main className="w-full max-w-4xl rounded-3xl border border-teal-100 bg-white/90 p-6 shadow-xl shadow-teal-950/5 backdrop-blur-xl sm:p-8 dark:border-teal-900/50 dark:bg-slate-900/90">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <p className="mb-2 text-sm font-bold tracking-[0.2em] text-teal-700 uppercase dark:text-teal-300">
              Aarogya AI
            </p>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Call Analytics Dashboard
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Completed calls only. No caller or health information is shown.
            </p>
          </div>
          <Button variant="outline" onClick={onBack} className="shrink-0 rounded-xl">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">
            <p>{error}</p>
            <Button
              variant="outline"
              onClick={() => void loadAnalytics()}
              className="mt-4 border-rose-200 bg-white dark:border-rose-800 dark:bg-slate-900"
            >
              Try again
            </Button>
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              {metrics.map(({ label, value, icon: Icon, tone, background }) => (
                <section
                  key={label}
                  className={`rounded-2xl border border-slate-200 p-5 dark:border-slate-700 ${background}`}
                >
                  <Icon className={`mb-5 h-6 w-6 ${tone}`} />
                  <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                    {label}
                  </p>
                  <p className={`mt-1 text-4xl font-extrabold tabular-nums ${tone}`}>
                    {isLoading ? '—' : value}
                  </p>
                </section>
              ))}
            </div>
            <div className="mt-7 flex justify-end">
              <Button
                variant="outline"
                onClick={() => void loadAnalytics()}
                disabled={isLoading}
                className="rounded-xl"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

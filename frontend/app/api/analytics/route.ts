import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const ANALYTICS_API_URL = process.env.ANALYTICS_API_URL ?? 'http://127.0.0.1:8081/api/analytics';

type CallAnalytics = {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
};

function isValidAnalytics(data: unknown): data is CallAnalytics {
  if (!data || typeof data !== 'object') return false;

  const analytics = data as CallAnalytics;
  return (
    Number.isInteger(analytics.total_calls) &&
    Number.isInteger(analytics.successful_calls) &&
    Number.isInteger(analytics.failed_calls) &&
    analytics.total_calls >= 0 &&
    analytics.successful_calls >= 0 &&
    analytics.failed_calls >= 0 &&
    analytics.total_calls === analytics.successful_calls + analytics.failed_calls
  );
}

export async function GET() {
  try {
    const response = await fetch(ANALYTICS_API_URL, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5_000),
    });

    if (!response.ok) {
      throw new Error(`Analytics API returned ${response.status}`);
    }

    const analytics: unknown = await response.json();
    if (!isValidAnalytics(analytics)) {
      throw new Error('Analytics API returned an invalid response');
    }

    return NextResponse.json(analytics, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    console.error('Unable to retrieve call analytics:', error);
    return NextResponse.json(
      { error: 'Call analytics are temporarily unavailable.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}

'use client';

import type { AppConfig } from '@/app-config';
import { AarogyaHealthView } from '@/components/app/aarogya-health-view';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  return <AarogyaHealthView />;
}


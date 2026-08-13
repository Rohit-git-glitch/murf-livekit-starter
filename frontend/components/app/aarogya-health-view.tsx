'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bot,
  CheckCircle2,
  HeartPulse,
  Loader2,
  MessageSquareText,
  Mic,
  MicOff,
  PhoneOff,
  RefreshCw,
  SendHorizontal,
  ShieldAlert,
  Sparkles,
  User,
  Volume2,
  X,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import {
  type ReceivedMessage,
  SessionEvent,
  useAgent,
  useChat,
  useSessionContext,
  useSessionMessages,
  useTrackVolume,
} from '@livekit/components-react';
import { CallAnalyticsDashboard } from '@/components/app/call-analytics-dashboard';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

/* ─── Simple inline transcript panel ─── */
function TranscriptPanel({
  messages,
  agentState,
  onClose,
  onSendMessage,
}: {
  messages: ReceivedMessage[];
  agentState: string;
  onClose: () => void;
  onSendMessage?: (message: string) => Promise<void> | void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async () => {
    const trimmed = draft.trim();
    if (!trimmed || !onSendMessage || isSending) return;

    setIsSending(true);
    try {
      await onSendMessage(trimmed);
      setDraft('');
    } finally {
      setIsSending(false);
    }
  };

  const onKeyDown = async (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await handleSubmit();
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-teal-200/60 px-4 py-3 dark:border-teal-800/60">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <MessageSquareText className="h-4 w-4 text-teal-600 dark:text-teal-400" />
          Live Transcript
        </h3>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={onClose}
          className="rounded-full hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto px-4 py-3 [scrollbar-width:thin]"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center py-12 text-center">
            <MessageSquareText className="mb-3 h-8 w-8 text-slate-300 dark:text-slate-600" />
            <p className="text-sm font-medium text-slate-400 dark:text-slate-500">
              Transcript will appear here
            </p>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
              Start speaking to see the conversation.
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.from?.isLocal === true;
          return (
            <div
              key={msg.id}
              className={cn('flex gap-2.5 text-sm', isUser ? 'flex-row-reverse' : 'flex-row')}
            >
              {/* Avatar */}
              <div
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
                  isUser
                    ? 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                    : 'bg-teal-100 text-teal-700 dark:bg-teal-900/60 dark:text-teal-300'
                )}
              >
                {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
              </div>

              {/* Bubble */}
              <div
                className={cn(
                  'max-w-[85%] rounded-2xl px-3.5 py-2 text-[13px] leading-relaxed',
                  isUser
                    ? 'rounded-tr-sm bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200'
                    : 'rounded-tl-sm border border-teal-100 bg-teal-50 text-slate-800 dark:border-teal-900/40 dark:bg-teal-950/60 dark:text-slate-200'
                )}
              >
                <p className="mb-0.5 text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                  {isUser ? 'You' : 'Anisha'}
                </p>
                {msg.message}
              </div>
            </div>
          );
        })}

        {/* Thinking indicator */}
        {agentState === 'thinking' && (
          <div className="flex gap-2.5 text-sm">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/60 dark:text-teal-300">
              <Bot className="h-3.5 w-3.5" />
            </div>
            <div className="rounded-2xl rounded-tl-sm border border-teal-100 bg-teal-50 px-4 py-2.5 dark:border-teal-900/40 dark:bg-teal-950/60">
              <div className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-500 [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-500 [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-500 [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-slate-200/80 bg-white/90 p-3 dark:border-slate-800 dark:bg-slate-950/80">
        <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-900">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Type a message to Anisha..."
            className="max-h-28 min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none dark:text-slate-100 dark:placeholder:text-slate-500"
          />
          <Button
            type="button"
            size="sm"
            onClick={handleSubmit}
            disabled={isSending || draft.trim().length === 0}
            className="h-10 rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <SendHorizontal className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Aarogya Health View ─── */
export function AarogyaHealthView() {
  const session = useSessionContext();
  const agent = useAgent();
  const { send } = useChat();
  const { messages } = useSessionMessages(session);

  const [isConnecting, setIsConnecting] = useState(false);
  const [micError, setMicError] = useState(false);
  const [callEnded, setCallEnded] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);

  // Monitor LiveKit Session media errors
  useEffect(() => {
    if (!session?.internal?.emitter) return;

    const handleMediaError = (error: Error) => {
      console.warn('LiveKit MediaDevicesError:', error);
      setMicError(true);
      setIsConnecting(false);
    };

    session.internal.emitter.on(SessionEvent.MediaDevicesError, handleMediaError);
    return () => {
      session.internal.emitter.off(SessionEvent.MediaDevicesError, handleMediaError);
    };
  }, [session]);

  // Track mic volume if connected
  const micTrack = session.local?.microphoneTrack;
  const micVolume = useTrackVolume(micTrack, { fftSize: 128, smoothingTimeConstant: 0.4 });

  // Handle muted state toggle on local mic track
  const toggleMute = useCallback(() => {
    if (session.room?.localParticipant) {
      const currentMuted = isMuted;
      session.room.localParticipant.setMicrophoneEnabled(currentMuted);
      setIsMuted(!currentMuted);
    }
  }, [session, isMuted]);

  // Handle starting a call
  const handleStartCall = async () => {
    setMicError(false);
    setCallEnded(false);
    setIsConnecting(true);

    try {
      // Pre-check microphone permission if possible
      if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          // Stop pre-check stream so LiveKit can request its own track cleanly
          stream.getTracks().forEach((t) => t.stop());
        } catch (err: any) {
          console.error('Microphone access denied:', err);
          setMicError(true);
          setIsConnecting(false);
          return;
        }
      }

      await session.start();
      setIsConnecting(false);
    } catch (error: any) {
      console.error('Failed to start session:', error);
      setMicError(true);
      setIsConnecting(false);
    }
  };

  // Handle ending a call
  const handleEndCall = async () => {
    try {
      await session.end();
    } catch (e) {
      console.error('Error ending session:', e);
    } finally {
      setIsConnecting(false);
      setCallEnded(true);
      setChatOpen(false);
    }
  };

  const handleSendTextMessage = useCallback(
    async (message: string) => {
      if (!session.isConnected || !message.trim()) return;
      await send(message.trim());
    },
    [send, session.isConnected]
  );

  // Determine current agent state
  let currentState: 'ready' | 'connecting' | 'listening' | 'speaking' | 'ended' | 'mic-blocked';

  if (micError) {
    currentState = 'mic-blocked';
  } else if (session.isConnected) {
    if (agent.state === 'speaking') {
      currentState = 'speaking';
    } else {
      currentState = 'listening';
    }
  } else if (
    isConnecting ||
    session.connectionState === 'connecting' ||
    agent.state === 'connecting' ||
    agent.state === 'initializing'
  ) {
    currentState = 'connecting';
  } else if (callEnded) {
    currentState = 'ended';
  } else {
    currentState = 'ready';
  }

  if (analyticsOpen) {
    return <CallAnalyticsDashboard onBack={() => setAnalyticsOpen(false)} />;
  }

  return (
    <div className="relative flex h-svh w-full overflow-hidden bg-gradient-to-b from-teal-50/60 via-slate-50 to-emerald-50/40 text-slate-800 transition-colors duration-300 dark:from-slate-950 dark:via-slate-900 dark:to-teal-950/40 dark:text-slate-100">
      {/* Background Decorative Elements */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-teal-400/10 blur-3xl dark:bg-teal-500/10" />
        <div className="absolute top-1/3 -right-32 h-96 w-96 rounded-full bg-emerald-400/10 blur-3xl dark:bg-emerald-500/10" />
        <div className="absolute -bottom-32 left-1/4 h-96 w-96 rounded-full bg-cyan-400/10 blur-3xl dark:bg-cyan-500/10" />
      </div>

      {/* ─── LEFT: Main Content Area ─── */}
      <div
        className={cn(
          'relative z-10 flex flex-col items-center justify-between overflow-y-auto p-4 transition-all duration-300 sm:p-6 md:p-8',
          chatOpen ? 'w-full md:w-[60%] lg:w-[65%]' : 'w-full'
        )}
      >
        {/* Top Bar: Brand Badge & Transcript Toggle */}
        <header className="flex w-full max-w-4xl items-center justify-between pt-2 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-600 text-white shadow-md shadow-teal-600/20 dark:bg-teal-500">
              <HeartPulse className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                  Aarogya AI
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-0.5 text-xs font-semibold text-teal-800 dark:bg-teal-900/60 dark:text-teal-300">
                  <Sparkles className="h-3 w-3" /> Health Access
                </span>
              </div>
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                Assistant:{' '}
                <strong className="font-semibold text-teal-700 dark:text-teal-400">Anisha</strong>
              </p>
            </div>
          </div>

          {/* Transcript Toggle Button — visible during active session */}
          {!session.isConnected && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAnalyticsOpen(true)}
              className="rounded-full border-teal-200 bg-white/80 text-teal-800 shadow-xs transition-colors hover:bg-teal-50 dark:border-teal-800 dark:bg-slate-900/80 dark:text-teal-300 dark:hover:bg-teal-900/40"
            >
              <BarChart3 className="mr-1.5 h-4 w-4" />
              Analytics
            </Button>
          )}
          {session.isConnected && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setChatOpen(!chatOpen)}
              className={cn(
                'rounded-full border-teal-200 bg-white/80 text-teal-800 shadow-xs transition-colors hover:bg-teal-50 dark:border-teal-800 dark:bg-slate-900/80 dark:text-teal-300 dark:hover:bg-teal-900/40',
                chatOpen && 'border-teal-300 bg-teal-100 dark:border-teal-700 dark:bg-teal-900/60'
              )}
            >
              <MessageSquareText className="mr-1.5 h-4 w-4" />
              <span className="hidden sm:inline">
                {chatOpen ? 'Hide Transcript' : 'View Transcript'}
              </span>
              <span className="sm:hidden">{chatOpen ? 'Hide' : 'Transcript'}</span>
            </Button>
          )}
        </header>

        {/* Main Center Card */}
        <main className="my-auto flex w-full max-w-lg flex-col items-center">
          <div className="w-full rounded-3xl border border-teal-100 bg-white/85 p-6 shadow-xl shadow-teal-950/5 backdrop-blur-xl transition-all sm:p-8 dark:border-teal-900/50 dark:bg-slate-900/85">
            {/* Main Product Header & Copy */}
            <div className="mb-6 text-center sm:mb-8">
              <h1 className="mb-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
                Aarogya AI
              </h1>
              <p className="mb-1 text-base font-semibold text-teal-700 sm:text-lg dark:text-teal-300">
                Your Voice Assistant for Better Health Access
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Talk to <strong>Anisha</strong> for basic health information and guidance.
              </p>
            </div>

            {/* Dynamic 5 States Display Area */}
            <div className="flex flex-col items-center justify-center py-4">
              {/* STATE 1: READY */}
              {currentState === 'ready' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex w-full flex-col items-center text-center"
                >
                  <div className="relative mb-6 flex h-32 w-32 items-center justify-center rounded-full border border-teal-100 bg-slate-100 shadow-inner dark:border-teal-900/40 dark:bg-slate-800/80">
                    <div className="absolute inset-0 animate-pulse rounded-full bg-teal-500/10" />
                    <Mic className="h-12 w-12 text-slate-400 dark:text-slate-500" />
                  </div>

                  <div className="mb-6">
                    <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      <span className="h-2 w-2 rounded-full bg-slate-400" />
                      Agent Ready
                    </span>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                      Anisha is ready to help
                    </h2>
                  </div>

                  <Button
                    size="lg"
                    onClick={handleStartCall}
                    className="h-14 w-full rounded-2xl bg-gradient-to-r from-teal-600 to-emerald-600 text-base font-bold text-white shadow-lg shadow-teal-600/25 transition-all hover:scale-[1.01] hover:from-teal-700 hover:to-emerald-700 active:scale-[0.99]"
                  >
                    <Mic className="mr-2 h-5 w-5" />
                    Start Conversation
                  </Button>
                </motion.div>
              )}

              {/* STATE 2: CONNECTING */}
              {currentState === 'connecting' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex w-full flex-col items-center text-center"
                >
                  <div className="relative mb-6 flex h-32 w-32 items-center justify-center">
                    <div className="absolute inset-0 rounded-full border-4 border-teal-200 opacity-30 dark:border-teal-900" />
                    <div className="absolute inset-0 animate-spin rounded-full border-4 border-teal-600 border-t-transparent dark:border-teal-400" />
                    <div className="flex h-16 w-16 animate-pulse items-center justify-center rounded-full bg-teal-500/10">
                      <Activity className="h-8 w-8 text-teal-600 dark:text-teal-400" />
                    </div>
                  </div>

                  <div className="mb-6">
                    <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-teal-200/60 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700 dark:border-teal-800/60 dark:bg-teal-950/80 dark:text-teal-300">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Connecting
                    </span>
                    <h2 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">
                      Connecting to Anisha...
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Please wait a moment while we establish a secure connection.
                    </p>
                  </div>

                  <Button
                    disabled
                    size="lg"
                    className="h-14 w-full cursor-not-allowed rounded-2xl bg-teal-700/60 text-base font-semibold text-white opacity-80"
                  >
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Connecting...
                  </Button>
                </motion.div>
              )}

              {/* STATE 3: LISTENING */}
              {currentState === 'listening' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex w-full flex-col items-center text-center"
                >
                  <div className="relative mb-6 flex h-32 w-32 items-center justify-center">
                    <div className="absolute inset-0 animate-ping rounded-full bg-emerald-500/20" />
                    <div className="absolute -inset-2 animate-pulse rounded-full bg-emerald-500/10" />
                    <div className="relative flex h-24 w-24 items-center justify-center rounded-full bg-emerald-600 text-white shadow-lg shadow-emerald-600/30">
                      <Mic className="h-10 w-10 animate-bounce" />
                    </div>
                  </div>

                  <div className="mb-6">
                    <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                      Microphone Active
                    </span>
                    <h2 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">
                      Anisha is listening to you...
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Speak naturally. Anisha is listening.
                    </p>
                  </div>

                  {/* Call Control Bar */}
                  <div className="flex w-full items-center gap-3">
                    <Button
                      variant={isMuted ? 'destructive' : 'outline'}
                      onClick={toggleMute}
                      className="h-12 flex-1 rounded-xl border-slate-200 font-semibold dark:border-slate-700"
                    >
                      {isMuted ? (
                        <MicOff className="mr-2 h-4 w-4" />
                      ) : (
                        <Mic className="mr-2 h-4 w-4 text-emerald-600" />
                      )}
                      {isMuted ? 'Muted' : 'Mute Mic'}
                    </Button>

                    <Button
                      variant="destructive"
                      onClick={handleEndCall}
                      className="h-12 flex-1 rounded-xl bg-rose-600 font-semibold shadow-md shadow-rose-600/20 hover:bg-rose-700"
                    >
                      <PhoneOff className="mr-2 h-4 w-4" />
                      End Call
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* STATE 4: SPEAKING */}
              {currentState === 'speaking' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex w-full flex-col items-center text-center"
                >
                  <div className="relative mb-6 flex h-32 w-32 items-center justify-center rounded-full border-2 border-cyan-400/40 bg-gradient-to-br from-teal-500/10 via-cyan-500/10 to-emerald-500/20 shadow-lg shadow-cyan-500/10">
                    <div className="absolute inset-0 animate-ping rounded-full border border-cyan-400/30" />
                    <div className="flex h-16 w-20 items-center justify-center gap-1.5">
                      <span className="h-8 w-2 animate-[bounce_1s_infinite_100ms] rounded-full bg-cyan-500" />
                      <span className="h-12 w-2 animate-[bounce_1s_infinite_300ms] rounded-full bg-teal-500" />
                      <span className="h-16 w-2 animate-[bounce_1s_infinite_200ms] rounded-full bg-emerald-500" />
                      <span className="h-10 w-2 animate-[bounce_1s_infinite_400ms] rounded-full bg-teal-500" />
                      <span className="h-6 w-2 animate-[bounce_1s_infinite_150ms] rounded-full bg-cyan-500" />
                    </div>
                  </div>

                  <div className="mb-6">
                    <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-cyan-200 bg-cyan-100 px-3 py-1 text-xs font-semibold text-cyan-800 dark:border-cyan-800 dark:bg-cyan-950/80 dark:text-cyan-300">
                      <Volume2 className="h-3 w-3 animate-pulse" />
                      Anisha Responding
                    </span>
                    <h2 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">
                      Anisha is speaking...
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Listen to Anisha&apos;s guidance.
                    </p>
                  </div>

                  <div className="flex w-full items-center gap-3">
                    <Button
                      variant={isMuted ? 'destructive' : 'outline'}
                      onClick={toggleMute}
                      className="h-12 flex-1 rounded-xl border-slate-200 font-semibold dark:border-slate-700"
                    >
                      {isMuted ? (
                        <MicOff className="mr-2 h-4 w-4" />
                      ) : (
                        <Mic className="mr-2 h-4 w-4 text-teal-600" />
                      )}
                      {isMuted ? 'Muted' : 'Mute Mic'}
                    </Button>

                    <Button
                      variant="destructive"
                      onClick={handleEndCall}
                      className="h-12 flex-1 rounded-xl bg-rose-600 font-semibold shadow-md shadow-rose-600/20 hover:bg-rose-700"
                    >
                      <PhoneOff className="mr-2 h-4 w-4" />
                      End Call
                    </Button>
                  </div>
                </motion.div>
              )}

              {/* STATE 5: CALL ENDED */}
              {currentState === 'ended' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex w-full flex-col items-center text-center"
                >
                  <div className="relative mb-6 flex h-32 w-32 items-center justify-center rounded-full border border-teal-200 bg-teal-50 dark:border-teal-800 dark:bg-teal-950/50">
                    <CheckCircle2 className="h-16 w-16 text-teal-600 dark:text-teal-400" />
                  </div>

                  <div className="mb-6">
                    <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      Session Completed
                    </span>
                    <h2 className="mb-1 text-xl font-bold text-slate-900 dark:text-white">
                      Conversation ended
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Thank you for using Aarogya AI.
                    </p>
                  </div>

                  <Button
                    size="lg"
                    onClick={handleStartCall}
                    className="h-14 w-full rounded-2xl bg-gradient-to-r from-teal-600 to-emerald-600 text-base font-bold text-white shadow-lg shadow-teal-600/25 transition-all hover:scale-[1.01] hover:from-teal-700 hover:to-emerald-700 active:scale-[0.99]"
                  >
                    <RefreshCw className="mr-2 h-5 w-5" />
                    Start Again
                  </Button>
                </motion.div>
              )}

              {/* MICROPHONE PERMISSION ERROR STATE */}
              {currentState === 'mic-blocked' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex w-full flex-col items-center text-center"
                >
                  <div className="relative mb-6 flex h-32 w-32 items-center justify-center rounded-full border-2 border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/40">
                    <MicOff className="h-14 w-14 text-amber-600 dark:text-amber-400" />
                  </div>

                  <div className="mb-6 max-w-sm">
                    <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-amber-300/60 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800 dark:border-amber-700/60 dark:bg-amber-950/80 dark:text-amber-300">
                      <AlertCircle className="h-3.5 w-3.5" />
                      Permission Blocked
                    </span>
                    <h2 className="mb-2 text-xl font-bold text-slate-900 dark:text-white">
                      Microphone access is blocked.
                    </h2>
                    <p className="text-xs leading-relaxed text-slate-600 sm:text-sm dark:text-slate-300">
                      Please allow microphone access in your browser settings and try again.
                    </p>
                  </div>

                  <Button
                    size="lg"
                    onClick={handleStartCall}
                    className="h-14 w-full rounded-2xl bg-amber-600 text-base font-bold text-white shadow-lg shadow-amber-600/25 transition-all hover:scale-[1.01] hover:bg-amber-700 active:scale-[0.99]"
                  >
                    <RefreshCw className="mr-2 h-5 w-5" />
                    Try Again
                  </Button>
                </motion.div>
              )}
            </div>
          </div>
        </main>

        {/* Safety Disclaimer Footer */}
        <footer className="my-4 w-full max-w-lg text-center">
          <div className="inline-flex items-center justify-center gap-2 rounded-xl border border-teal-900/10 bg-teal-900/5 px-4 py-2.5 dark:border-teal-100/10 dark:bg-teal-100/5">
            <ShieldAlert className="h-4 w-4 shrink-0 text-teal-700 dark:text-teal-400" />
            <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
              For general health information. Not a replacement for a doctor.
            </p>
          </div>
        </footer>
      </div>

      {/* ─── RIGHT: Transcript Side Panel ─── */}
      <AnimatePresence>
        {chatOpen && session.isConnected && (
          <motion.aside
            key="transcript-panel"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 'auto', opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="relative z-20 h-full shrink-0 overflow-hidden border-l border-teal-200/60 bg-white/95 shadow-[-4px_0_24px_rgba(0,0,0,0.05)] backdrop-blur-xl dark:border-teal-800/50 dark:bg-slate-900/95"
          >
            <div className="h-full w-[340px] md:w-[380px] lg:w-[400px]">
              <TranscriptPanel
                messages={messages}
                agentState={agent.state}
                onClose={() => setChatOpen(false)}
                onSendMessage={handleSendTextMessage}
              />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Mobile transcript overlay (on small screens) */}
      <AnimatePresence>
        {chatOpen && session.isConnected && (
          <motion.div
            key="mobile-transcript-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/20 backdrop-blur-sm md:hidden"
            onClick={() => setChatOpen(false)}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {chatOpen && session.isConnected && (
          <motion.aside
            key="mobile-transcript-panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="fixed top-0 right-0 z-40 h-full w-[85vw] max-w-[380px] border-l border-teal-200/60 bg-white shadow-2xl md:hidden dark:border-teal-800/50 dark:bg-slate-900"
          >
            <TranscriptPanel
              messages={messages}
              agentState={agent.state}
              onClose={() => setChatOpen(false)}
              onSendMessage={handleSendTextMessage}
            />
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}

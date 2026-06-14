/**
 * useSession — manages the full turn lifecycle against the ENGLO API.
 *
 * States: idle → loading_activity → prompting → ready_to_record →
 *         recording → processing → showing_result → (loop)
 */

import { useCallback, useState } from 'react';
import {
  ActivityResponse,
  TurnResponse,
  createSession,
  endSession,
  getActivity,
  submitTurn,
} from '../api/client';
import { useAudio } from './useAudio';

export type SessionPhase =
  | 'idle'
  | 'loading'
  | 'prompting'
  | 'ready'
  | 'recording'
  | 'processing'
  | 'result'
  | 'complete'
  | 'error';

export interface SessionState {
  phase: SessionPhase;
  sessionId: string | null;
  activity: ActivityResponse | null;
  lastResult: TurnResponse | null;
  error: string | null;
}

export function useSession() {
  const audio = useAudio();

  const [state, setState] = useState<SessionState>({
    phase: 'idle',
    sessionId: null,
    activity: null,
    lastResult: null,
    error: null,
  });

  const set = (partial: Partial<SessionState>) =>
    setState((s) => ({ ...s, ...partial }));

  const start = useCallback(async () => {
    set({ phase: 'loading', error: null });
    try {
      const sid = await createSession();
      set({ sessionId: sid });
      await _loadActivity(sid);
    } catch (e) {
      set({ phase: 'error', error: String(e) });
    }
  }, []);

  const _loadActivity = async (sid: string) => {
    set({ phase: 'loading' });
    const activity = await getActivity(sid);
    set({ activity, phase: 'prompting' });
    // Play tutor prompt audio, then transition to ready
    await audio.playB64(activity.prompt_audio_b64);
    set({ phase: 'ready' });
  };

  const startRecording = useCallback(async () => {
    set({ phase: 'recording' });
    await audio.startRecording();
  }, [audio]);

  const stopAndSubmit = useCallback(async () => {
    if (!state.sessionId) return;
    set({ phase: 'processing' });

    const uri = await audio.stopRecording();
    if (!uri) {
      set({ phase: 'error', error: 'No audio recorded' });
      return;
    }

    try {
      const result = await submitTurn(state.sessionId, uri);
      set({ lastResult: result, phase: 'result' });

      // Play tutor response audio
      await audio.playB64(result.response_audio_b64);

      if (result.is_complete) {
        set({ phase: 'complete' });
        return;
      }

      if (result.step === 'repeat') {
        // Re-play the prompt and wait for another attempt
        const activity = await getActivity(state.sessionId);
        set({ activity, phase: 'prompting' });
        await audio.playB64(activity.prompt_audio_b64);
        set({ phase: 'ready' });
      } else {
        // Advance to next activity
        await _loadActivity(state.sessionId);
      }
    } catch (e) {
      set({ phase: 'error', error: String(e) });
    }
  }, [state.sessionId, audio]);

  const finish = useCallback(async () => {
    if (state.sessionId) await endSession(state.sessionId).catch(() => {});
    set({ phase: 'idle', sessionId: null, activity: null, lastResult: null });
  }, [state.sessionId]);

  return { state, start, startRecording, stopAndSubmit, finish };
}

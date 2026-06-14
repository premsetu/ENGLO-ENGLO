/**
 * ENGLO API client.
 *
 * Set API_BASE_URL to your server.  During Expo dev on a physical device,
 * use your machine's LAN IP: e.g. "http://192.168.1.10:8000"
 * On Android emulator use "http://10.0.2.2:8000".
 * On iOS simulator use "http://localhost:8000".
 */

import axios from 'axios';

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

const api = axios.create({ baseURL: API_BASE_URL, timeout: 30_000 });

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ActivityResponse {
  session_id: string;
  activity_id: string;
  activity_type: string;
  target_text: string;
  hindi_scaffold: string;
  simplicity_level: string;
  hindi_support: number;
  is_drill: boolean;
  prompt_audio_b64: string;
  lesson_title: string;
  level_name: string;
}

export interface TurnResponse {
  session_id: string;
  transcript: string;
  pronunciation_overall: number;
  pronunciation_accuracy: number;
  pronunciation_completeness: number;
  pronunciation_fluency: number;
  weak_phonemes: string[];
  verdict: 'pass' | 'partial' | 'fail';
  correction: string;
  next_spoken_line: string;
  language_mix: string;
  response_audio_b64: string;
  step: 'repeat' | 'next_activity' | 'next_lesson' | 'course_complete';
  is_complete: boolean;
}

export interface ProgressResponse {
  session_id: string;
  total_turns: number;
  pass_rate: number;
  vocab_count: number;
  summary: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function createSession(): Promise<string> {
  const { data } = await api.post<{ session_id: string }>('/api/session');
  return data.session_id;
}

export async function getActivity(sessionId: string): Promise<ActivityResponse> {
  const { data } = await api.get<ActivityResponse>(
    `/api/session/${sessionId}/activity`,
  );
  return data;
}

export async function submitTurn(
  sessionId: string,
  audioUri: string,
): Promise<TurnResponse> {
  const form = new FormData();
  form.append('audio', {
    uri: audioUri,
    type: 'audio/wav',
    name: 'turn.wav',
  } as unknown as Blob);

  const { data } = await api.post<TurnResponse>(
    `/api/session/${sessionId}/turn`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

export async function getProgress(sessionId: string): Promise<ProgressResponse> {
  const { data } = await api.get<ProgressResponse>(
    `/api/session/${sessionId}/progress`,
  );
  return data;
}

export async function endSession(sessionId: string): Promise<void> {
  await api.delete(`/api/session/${sessionId}`);
}

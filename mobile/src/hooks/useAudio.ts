/**
 * useAudio — mic recording + base64 MP3 playback via expo-av.
 *
 * record()      — start recording; returns cleanup fn
 * stopRecord()  — stop and return local file URI
 * playB64(b64)  — decode base64 MP3 and play it
 */

import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { useCallback, useRef } from 'react';

export function useAudio() {
  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);

  const requestPermission = useCallback(async () => {
    const { status } = await Audio.requestPermissionsAsync();
    if (status !== 'granted') throw new Error('Microphone permission denied');
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    await requestPermission();
    const recording = new Audio.Recording();
    await recording.prepareToRecordAsync({
      android: {
        extension: '.wav',
        outputFormat: Audio.AndroidOutputFormat.DEFAULT,
        audioEncoder: Audio.AndroidAudioEncoder.DEFAULT,
        sampleRate: 16000,
        numberOfChannels: 1,
        bitRate: 128000,
      },
      ios: {
        extension: '.wav',
        outputFormat: Audio.IOSOutputFormat.LINEARPCM,
        audioQuality: Audio.IOSAudioQuality.HIGH,
        sampleRate: 16000,
        numberOfChannels: 1,
        bitRate: 128000,
        linearPCMBitDepth: 16,
        linearPCMIsBigEndian: false,
        linearPCMIsFloat: false,
      },
      web: {},
    });
    await recording.startAsync();
    recordingRef.current = recording;
  }, [requestPermission]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    const recording = recordingRef.current;
    if (!recording) return null;
    await recording.stopAndUnloadAsync();
    recordingRef.current = null;
    return recording.getURI() ?? null;
  }, []);

  const playB64 = useCallback(async (b64: string): Promise<void> => {
    // Unload any previous sound
    if (soundRef.current) {
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }

    // Write base64 MP3 to a temp file
    const uri = FileSystem.cacheDirectory + `englo_${Date.now()}.mp3`;
    await FileSystem.writeAsStringAsync(uri, b64, {
      encoding: FileSystem.EncodingType.Base64,
    });

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
    });

    const { sound } = await Audio.Sound.createAsync({ uri });
    soundRef.current = sound;
    await sound.playAsync();

    // Wait for playback to finish
    await new Promise<void>((resolve) => {
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) resolve();
      });
    });

    // Clean up temp file
    await FileSystem.deleteAsync(uri, { idempotent: true });
  }, []);

  return { startRecording, stopRecording, playB64 };
}

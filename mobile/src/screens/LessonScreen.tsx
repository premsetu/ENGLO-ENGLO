import { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useEffect } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { RootStackParamList } from '../../App';
import { ActivityCard } from '../components/ActivityCard';
import { PronunciationBar } from '../components/PronunciationBar';
import { RecordButton } from '../components/RecordButton';
import { useSession } from '../hooks/useSession';

type Props = NativeStackScreenProps<RootStackParamList, 'Lesson'>;

export function LessonScreen({ navigation }: Props) {
  const { state, start, startRecording, stopAndSubmit, finish } = useSession();

  // Auto-start on mount
  useEffect(() => { start(); }, []);

  const handleRecordBtn = () => {
    if (state.phase === 'ready') startRecording();
    else if (state.phase === 'recording') stopAndSubmit();
  };

  const handleFinish = async () => {
    await finish();
    navigation.goBack();
  };

  if (state.phase === 'complete') {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.completeContainer}>
          <Text style={styles.completeIcon}>🎉</Text>
          <Text style={styles.completeTitle}>Course Complete!</Text>
          <Text style={styles.completeSub}>
            You've finished all L0 + L1 lessons.{'\n'}Amazing work!
          </Text>
          <TouchableOpacity style={styles.doneBtn} onPress={handleFinish}>
            <Text style={styles.doneBtnText}>Back to Home</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (state.phase === 'error') {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.completeContainer}>
          <Text style={styles.completeIcon}>⚠️</Text>
          <Text style={styles.completeTitle}>Something went wrong</Text>
          <Text style={styles.completeSub}>{state.error}</Text>
          <TouchableOpacity style={styles.doneBtn} onPress={handleFinish}>
            <Text style={styles.doneBtnText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleFinish} style={styles.backBtn}>
          <Text style={styles.backText}>✕</Text>
        </TouchableOpacity>
        <Text style={styles.lessonTitle} numberOfLines={1}>
          {state.activity?.lesson_title ?? 'Loading…'}
        </Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Loading spinner */}
        {(state.phase === 'idle' || state.phase === 'loading') && (
          <ActivityIndicator size="large" color="#f4a261" style={styles.spinner} />
        )}

        {/* Activity card */}
        {state.activity && state.phase !== 'idle' && (
          <ActivityCard activity={state.activity} />
        )}

        {/* Verdict / result */}
        {state.lastResult && state.phase === 'result' && (
          <PronunciationBar result={state.lastResult} />
        )}

        {/* Phase label */}
        {state.phase === 'prompting' && (
          <View style={styles.phaseRow}>
            <Text style={styles.phaseIcon}>🔊</Text>
            <Text style={styles.phaseText}>Listen to the tutor…</Text>
          </View>
        )}
        {state.phase === 'processing' && (
          <View style={styles.phaseRow}>
            <ActivityIndicator size="small" color="#f4a261" />
            <Text style={styles.phaseText}>Evaluating your response…</Text>
          </View>
        )}
      </ScrollView>

      {/* Record button */}
      <View style={styles.footer}>
        <RecordButton phase={state.phase} onPress={handleRecordBtn} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0d0d1f' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1e1e3a',
  },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  backText: { color: '#8888aa', fontSize: 18 },
  lessonTitle: { flex: 1, color: '#ffffff', fontSize: 15, fontWeight: '600', textAlign: 'center' },
  scroll: { flex: 1 },
  content: { paddingTop: 24, paddingBottom: 40, gap: 20 },
  spinner: { marginTop: 80 },
  phaseRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    marginTop: 8,
  },
  phaseIcon: { fontSize: 20 },
  phaseText: { color: '#8888aa', fontSize: 14 },
  footer: {
    paddingVertical: 28,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#1e1e3a',
  },
  completeContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 16,
  },
  completeIcon: { fontSize: 64 },
  completeTitle: { color: '#ffffff', fontSize: 28, fontWeight: '700' },
  completeSub: { color: '#8888aa', fontSize: 15, textAlign: 'center', lineHeight: 22 },
  doneBtn: {
    backgroundColor: '#2a9d8f',
    borderRadius: 14,
    paddingHorizontal: 32,
    paddingVertical: 14,
    marginTop: 8,
  },
  doneBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});

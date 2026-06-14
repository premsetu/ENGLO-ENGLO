import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { TurnResponse } from '../api/client';

interface Props {
  result: TurnResponse;
}

export function PronunciationBar({ result }: Props) {
  const verdict = result.verdict;
  const color =
    verdict === 'pass' ? '#2a9d8f' : verdict === 'partial' ? '#f4a261' : '#e63946';

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={[styles.verdict, { color }]}>{verdict.toUpperCase()}</Text>
        <Text style={styles.overall}>{Math.round(result.pronunciation_overall * 100)}%</Text>
      </View>

      <ScoreRow label="Accuracy" value={result.pronunciation_accuracy} />
      <ScoreRow label="Completeness" value={result.pronunciation_completeness} />
      <ScoreRow label="Fluency" value={result.pronunciation_fluency} />

      {result.weak_phonemes.length > 0 && (
        <Text style={styles.weak}>
          Watch: {result.weak_phonemes.join(' · ')}
        </Text>
      )}

      {result.correction ? (
        <Text style={styles.correction}>💬 {result.correction}</Text>
      ) : null}
    </View>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 75 ? '#2a9d8f' : pct >= 50 ? '#f4a261' : '#e63946';
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.pct, { color }]}>{pct}%</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#12122a',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    gap: 8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  verdict: {
    fontSize: 18,
    fontWeight: '700',
  },
  overall: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  rowLabel: {
    color: '#8888aa',
    fontSize: 12,
    width: 90,
  },
  track: {
    flex: 1,
    height: 6,
    backgroundColor: '#2e2e5a',
    borderRadius: 3,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 3,
  },
  pct: {
    fontSize: 12,
    fontWeight: '600',
    width: 34,
    textAlign: 'right',
  },
  weak: {
    color: '#f4a261',
    fontSize: 12,
    marginTop: 4,
  },
  correction: {
    color: '#aaaacc',
    fontSize: 13,
    fontStyle: 'italic',
    marginTop: 4,
    lineHeight: 18,
  },
});

import { NativeStackScreenProps } from '@react-navigation/native-stack';
import React from 'react';
import {
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { RootStackParamList } from '../../App';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export function HomeScreen({ navigation }: Props) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <View style={styles.hero}>
          <Text style={styles.logo}>ENGLO</Text>
          <Text style={styles.tagline}>
            Voice-first English for{'\n'}Hindi-speaking learners
          </Text>
        </View>

        <View style={styles.levelBadges}>
          {[
            { id: 'L0', name: 'Bootstrap', cefr: 'pre-A1', color: '#f4a261' },
            { id: 'L1', name: 'First Sentences', cefr: 'A1', color: '#2a9d8f' },
            { id: 'L2', name: 'Everyday', cefr: 'A2', color: '#457b9d' },
            { id: 'L3', name: 'Confident', cefr: 'B1', color: '#8338ec' },
            { id: 'L4', name: 'Fluency', cefr: 'B2', color: '#e63946' },
          ].map((lvl) => (
            <View key={lvl.id} style={[styles.badge, { borderColor: lvl.color }]}>
              <Text style={[styles.badgeId, { color: lvl.color }]}>{lvl.id}</Text>
              <Text style={styles.badgeName}>{lvl.name}</Text>
              <Text style={styles.badgeCefr}>{lvl.cefr}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity
          style={styles.startBtn}
          onPress={() => navigation.navigate('Lesson')}
          activeOpacity={0.85}
        >
          <Text style={styles.startText}>Start Learning</Text>
        </TouchableOpacity>

        <Text style={styles.hint}>
          Speak English · Get instant feedback · Progress at your own pace
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0d0d1f' },
  container: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: 'center',
    gap: 32,
  },
  hero: { alignItems: 'center', gap: 10 },
  logo: {
    color: '#ffffff',
    fontSize: 52,
    fontWeight: '800',
    letterSpacing: 6,
  },
  tagline: {
    color: '#8888aa',
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
  },
  levelBadges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  badge: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    alignItems: 'center',
    minWidth: 80,
  },
  badgeId: { fontSize: 13, fontWeight: '700' },
  badgeName: { color: '#ccccdd', fontSize: 10, marginTop: 2 },
  badgeCefr: { color: '#666688', fontSize: 10 },
  startBtn: {
    backgroundColor: '#e63946',
    borderRadius: 16,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: '#e63946',
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 6,
  },
  startText: { color: '#fff', fontSize: 18, fontWeight: '700', letterSpacing: 1 },
  hint: {
    color: '#555577',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
});

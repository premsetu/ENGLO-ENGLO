import React, { useEffect, useRef } from 'react';
import {
  Animated,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SessionPhase } from '../hooks/useSession';

interface Props {
  phase: SessionPhase;
  onPress: () => void;
}

export function RecordButton({ phase, onPress }: Props) {
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (phase === 'recording') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulse, { toValue: 1.15, duration: 600, useNativeDriver: true }),
          Animated.timing(pulse, { toValue: 1.0, duration: 600, useNativeDriver: true }),
        ]),
      ).start();
    } else {
      pulse.stopAnimation();
      pulse.setValue(1);
    }
  }, [phase, pulse]);

  const config = _config(phase);

  return (
    <View style={styles.wrapper}>
      <Animated.View style={{ transform: [{ scale: pulse }] }}>
        <TouchableOpacity
          style={[styles.btn, { backgroundColor: config.bg }]}
          onPress={onPress}
          disabled={!config.enabled}
          activeOpacity={0.8}
        >
          <Text style={styles.icon}>{config.icon}</Text>
        </TouchableOpacity>
      </Animated.View>
      <Text style={styles.label}>{config.label}</Text>
    </View>
  );
}

function _config(phase: SessionPhase) {
  switch (phase) {
    case 'ready':
      return { bg: '#e63946', icon: '🎤', label: 'Tap to speak', enabled: true };
    case 'recording':
      return { bg: '#c1121f', icon: '⏹', label: 'Tap to stop', enabled: true };
    case 'processing':
      return { bg: '#555', icon: '⏳', label: 'Processing…', enabled: false };
    case 'prompting':
      return { bg: '#457b9d', icon: '🔊', label: 'Listen…', enabled: false };
    case 'result':
      return { bg: '#2a9d8f', icon: '✓', label: 'Loading next…', enabled: false };
    default:
      return { bg: '#333', icon: '🎤', label: '', enabled: false };
  }
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: 10,
  },
  btn: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 8,
  },
  icon: {
    fontSize: 32,
  },
  label: {
    color: '#aaaacc',
    fontSize: 13,
    fontWeight: '500',
  },
});

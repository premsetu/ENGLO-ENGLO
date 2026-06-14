import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { ActivityResponse } from '../api/client';

const TYPE_LABEL: Record<string, string> = {
  listen_repeat: 'Listen & Repeat',
  translate_say: 'Translate & Say',
  prompt_respond: 'Respond',
  recall_drill: 'Recall Drill',
};

interface Props {
  activity: ActivityResponse;
}

export function ActivityCard({ activity }: Props) {
  const label = TYPE_LABEL[activity.activity_type] ?? activity.activity_type;
  const hindiPct = Math.round(activity.hindi_support * 100);

  return (
    <View style={styles.card}>
      <View style={styles.meta}>
        <Text style={styles.badge}>{label}</Text>
        <Text style={styles.level}>
          {activity.level_name} · {activity.simplicity_level} · Hindi {hindiPct}%
        </Text>
      </View>

      <Text style={styles.target}>{activity.target_text}</Text>

      <View style={styles.divider} />

      <Text style={styles.scaffold}>{activity.hindi_scaffold}</Text>

      {activity.is_drill && (
        <View style={styles.drillBadge}>
          <Text style={styles.drillText}>SRS Recall Drill</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1e1e3a',
    borderRadius: 16,
    padding: 20,
    marginHorizontal: 16,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  meta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  badge: {
    backgroundColor: '#f4a261',
    color: '#1a1a2e',
    fontSize: 12,
    fontWeight: '700',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    overflow: 'hidden',
  },
  level: {
    color: '#8888aa',
    fontSize: 11,
  },
  target: {
    color: '#ffffff',
    fontSize: 26,
    fontWeight: '600',
    lineHeight: 34,
    marginBottom: 14,
  },
  divider: {
    height: 1,
    backgroundColor: '#2e2e5a',
    marginBottom: 12,
  },
  scaffold: {
    color: '#aaaacc',
    fontSize: 15,
    lineHeight: 22,
  },
  drillBadge: {
    marginTop: 12,
    backgroundColor: '#264653',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignSelf: 'flex-start',
  },
  drillText: {
    color: '#2a9d8f',
    fontSize: 12,
    fontWeight: '600',
  },
});

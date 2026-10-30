/**
 * KnowledgeUnitCard Component
 * Displays a single knowledge unit in a card format
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Badge,
} from 'react-native';
import { KnowledgeUnit } from '../types';
import { formatDistanceToNow } from 'date-fns';
import { vi, enUS } from 'date-fns/locale';

interface Props {
  unit: KnowledgeUnit;
  onPress: (id: string) => void;
  onLongPress?: (id: string) => void;
  showActions?: boolean;
  language?: 'en' | 'vi';
}

const KNOWLEDGE_TYPE_COLORS: Record<string, string> = {
  FACT: '#3B82F6',
  QUESTION: '#F59E0B',
  ANSWER: '#10B981',
  EVENT: '#8B5CF6',
  LESSON_LEARNED: '#EC4899',
  BEST_PRACTICE: '#06B6D4',
  DOCUMENT: '#6B7280',
  SUMMARY: '#14B8A6',
};

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  PENDING: { label: 'Pending', color: '#F59E0B' },
  VERIFIED: { label: 'Verified', color: '#10B981' },
  OBSOLETE: { label: 'Obsolete', color: '#6B7280' },
  CONFLICTED: { label: 'Conflicted', color: '#EF4444' },
};

export const KnowledgeUnitCard: React.FC<Props> = ({
  unit,
  onPress,
  onLongPress,
  showActions = true,
  language = 'en',
}) => {
  const locale = language === 'vi' ? vi : enUS;
  const typeColor = KNOWLEDGE_TYPE_COLORS[unit.knowledge_type] || '#6B7280';
  const statusBadge = STATUS_BADGES[unit.status] || { label: unit.status, color: '#6B7280' };

  const confidenceColor =
    unit.confidence >= 0.8 ? '#10B981' :
    unit.confidence >= 0.6 ? '#F59E0B' :
    '#EF4444';

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => onPress(unit.knowledge_id)}
      onLongPress={() => onLongPress?.(unit.knowledge_id)}
      activeOpacity={0.7}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={[styles.typeBadge, { backgroundColor: typeColor }]}>
          <Text style={styles.typeBadgeText}>{unit.knowledge_type}</Text>
        </View>

        <View style={[styles.statusBadge, { backgroundColor: statusBadge.color }]}>
          <Text style={styles.statusBadgeText}>{statusBadge.label}</Text>
        </View>
      </View>

      {/* Content */}
      <View style={styles.content}>
        <Text style={styles.statement} numberOfLines={3}>
          {unit.statement}
        </Text>

        <View style={styles.meta}>
          <View style={styles.metaItem}>
            <Text style={styles.metaLabel}>Subject:</Text>
            <Text style={styles.metaValue}>{unit.subject}</Text>
          </View>

          <View style={styles.metaItem}>
            <Text style={styles.metaLabel}>Predicate:</Text>
            <Text style={styles.metaValue}>{unit.predicate}</Text>
          </View>

          <View style={styles.metaItem}>
            <Text style={styles.metaLabel}>Object:</Text>
            <Text style={styles.metaValue}>{unit.object}</Text>
          </View>
        </View>

        {/* Confidence & Scope */}
        <View style={styles.footer}>
          <View style={styles.confidenceContainer}>
            <Text style={styles.confidenceLabel}>Confidence:</Text>
            <View style={[styles.confidenceBar, { backgroundColor: confidenceColor }]}>
              <View
                style={[
                  styles.confidenceFill,
                  { width: `${unit.confidence * 100}%` },
                ]}
              />
            </View>
            <Text style={styles.confidenceValue}>
              {(unit.confidence * 100).toFixed(0)}%
            </Text>
          </View>

          <View style={styles.scopeContainer}>
            <Text style={styles.scopeLabel}>Scope: {unit.scope}</Text>
          </View>
        </View>

        {/* Timestamp */}
        <Text style={styles.timestamp}>
          Updated {formatDistanceToNow(new Date(unit.updated_at_utc), { locale, addSuffix: true })}
        </Text>
      </View>

      {/* Tags */}
      {unit.tags && unit.tags.length > 0 && (
        <View style={styles.tagsContainer}>
          {unit.tags.slice(0, 3).map((tag, index) => (
            <View key={index} style={styles.tag}>
              <Text style={styles.tagText}>#{tag}</Text>
            </View>
          ))}
          {unit.tags.length > 3 && (
            <Text style={styles.moreTags}>+{unit.tags.length - 3} more</Text>
          )}
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    marginHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  typeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
  },
  typeBadgeText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '500',
  },
  content: {
    marginBottom: 12,
  },
  statement: {
    fontSize: 16,
    lineHeight: 22,
    color: '#1F2937',
    marginBottom: 12,
  },
  meta: {
    marginBottom: 12,
  },
  metaItem: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  metaLabel: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
    width: 80,
  },
  metaValue: {
    fontSize: 12,
    color: '#374151',
    flex: 1,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  confidenceContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
  },
  confidenceLabel: {
    fontSize: 11,
    color: '#6B7280',
    marginRight: 6,
  },
  confidenceBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#E5E7EB',
    borderRadius: 3,
    overflow: 'hidden',
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 3,
  },
  confidenceValue: {
    fontSize: 11,
    color: '#374151',
    fontWeight: '600',
    marginLeft: 6,
    minWidth: 35,
  },
  scopeContainer: {
    marginLeft: 12,
  },
  scopeLabel: {
    fontSize: 11,
    color: '#6B7280',
  },
  timestamp: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 8,
    textAlign: 'right',
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  tag: {
    backgroundColor: '#F3F4F6',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginRight: 6,
    marginBottom: 4,
  },
  tagText: {
    fontSize: 11,
    color: '#4B5563',
  },
  moreTags: {
    fontSize: 11,
    color: '#6B7280',
    fontStyle: 'italic',
  },
});

export default KnowledgeUnitCard;
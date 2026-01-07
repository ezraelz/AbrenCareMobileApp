// components/HealthCard.js
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const HealthCard = ({
  title,
  value,
  unit,
  icon: Icon,
  subtitle,
  gradient = false,
  progress,
  variant = 'default',
  children,
  style,
}) => {
  const variantStyles = {
    default: { backgroundColor: '#f8f9fa', borderColor: '#e9ecef' },
    destructive: { backgroundColor: '#fdecea', borderColor: '#fcc5c0' },
    success: { backgroundColor: '#e6f4ea', borderColor: '#a8dab5' },
  };

  const iconStyles = {
    default: { backgroundColor: '#e3f2fd', color: '#1976d2' },
    destructive: { backgroundColor: '#ffebee', color: '#d32f2f' },
    success: { backgroundColor: '#e8f5e8', color: '#2e7d32' },
  };

  const progressColors = {
    default: '#1976d2',
    destructive: '#d32f2f',
    success: '#2e7d32',
  };

  const CardContainer = gradient ? '' : View;

  const containerProps = gradient
    ? {
        colors: ['rgba(25, 118, 210, 0.05)', 'rgba(25, 118, 210, 0.1)'],
        start: { x: 0, y: 0 },
        end: { x: 1, y: 1 },
      }
    : {};

  const renderCard = () => (
    <View style={[styles.card, variantStyles[variant], style]}>
      <View style={styles.cardHeader}>
        <View style={styles.titleContainer}>
          {Icon && (
            <View style={[styles.iconContainer, iconStyles[variant]]}>
              <Icon size={20} color={iconStyles[variant].color} />
            </View>
          )}
          <View>
            <Text style={[styles.title, { color: iconStyles[variant].color }]}>
              {title}
            </Text>
            {subtitle && (
              <Text style={styles.subtitle}>{subtitle}</Text>
            )}
          </View>
        </View>
        <View style={[styles.iconCircle, iconStyles[variant]]}>
          {Icon && <Icon size={24} color={iconStyles[variant].color} />}
        </View>
      </View>

      <View style={styles.content}>
        <View style={styles.valueContainer}>
          <Text style={[styles.value, { color: iconStyles[variant].color }]}>
            {value}
          </Text>
          {unit && <Text style={styles.unit}>{unit}</Text>}
        </View>

        {progress !== undefined && (
          <View style={styles.progressContainer}>
            <View style={styles.progressLabels}>
              <Text style={styles.progressLabel}>Progress</Text>
              <Text style={styles.progressPercentage}>
                {progress.toFixed(1)}%
              </Text>
            </View>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width: `${Math.min(progress, 100)}%`,
                    backgroundColor: progressColors[variant],
                  },
                ]}
              />
            </View>
          </View>
        )}
      </View>

      {children}
    </View>
  );

  if (gradient) {
    return (
      <CardContainer {...containerProps} style={[styles.card, style]}>
        {renderCard()}
      </CardContainer>
    );
  }

  return renderCard();
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    marginBottom: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 12,
    color: '#6c757d',
    marginTop: 2,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    marginTop: 8,
  },
  valueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
    marginBottom: 12,
  },
  value: {
    fontSize: 28,
    fontWeight: 'bold',
  },
  unit: {
    fontSize: 16,
    color: '#6c757d',
  },
  progressContainer: {
    marginTop: 8,
  },
  progressLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  progressLabel: {
    fontSize: 12,
    color: '#6c757d',
  },
  progressPercentage: {
    fontSize: 12,
    fontWeight: '600',
  },
  progressBar: {
    height: 6,
    backgroundColor: '#e9ecef',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
});

export default HealthCard;
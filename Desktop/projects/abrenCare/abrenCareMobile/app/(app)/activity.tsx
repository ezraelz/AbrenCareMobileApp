// screens/ActivityScreen.js
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { router } from 'expo-router';
import {
  ChevronLeft,
  TrendingUp,
  Footprints,
  Flame,
  Clock,
  Loader2,
  Heart,
  Moon,
  Zap,
  Target,
  Trophy,
  Battery,
  Activity as ActivityIcon,
  Users,
  ChevronRight,
  BarChart3,
  Target as TargetIcon,
} from 'lucide-react-native';

const { width } = Dimensions.get('window');

// HealthCard Component
const HealthCard = ({ 
  title, 
  value, 
  unit, 
  icon: Icon, 
  subtitle, 
  gradient = false,
  progress,
  variant = "default",
  size = "large",
  children,
  style,
}) => {
  const variantStyles = {
    default: { backgroundColor: '#ffffff' },
    destructive: { backgroundColor: 'rgba(239, 68, 68, 0.1)' },
    success: { backgroundColor: 'rgba(16, 185, 129, 0.1)' },
  };

  const iconBackground = {
    default: { backgroundColor: 'rgba(59, 130, 246, 0.1)' },
    destructive: { backgroundColor: 'rgba(239, 68, 68, 0.2)' },
    success: { backgroundColor: 'rgba(16, 185, 129, 0.2)' },
  };

  const iconColor = {
    default: '#3b82f6',
    destructive: '#ef4444',
    success: '#10b981',
  };

  return (
    <View style={[
      styles.healthCardWrapper,
      variantStyles[variant],
      gradient && styles.healthCardGradient,
      size === 'small' && styles.smallCard,
      style,
    ]}>
      <View style={styles.healthCardHeader}>
        <View style={styles.healthCardTitleSection}>
          <View style={styles.titleIconRow}>
            {Icon && <Icon size={20} color="#374151" />}
            <Text style={styles.healthCardTitle}>{title}</Text>
          </View>
          {subtitle && (
            <Text style={styles.healthCardSubtitle}>{subtitle}</Text>
          )}
        </View>
        <View style={[styles.iconCircle, iconBackground[variant]]}>
          {Icon && <Icon size={24} color={iconColor[variant]} />}
        </View>
      </View>
      
      <View style={styles.healthCardContent}>
        <View style={styles.valueUnitRow}>
          <Text style={styles.healthCardValue}>{value}</Text>
          {unit && <Text style={styles.healthCardUnit}>{unit}</Text>}
        </View>
        
        {progress !== undefined && (
          <View style={styles.progressSection}>
            <View style={styles.progressLabels}>
              <Text style={styles.progressLabel}>Progress</Text>
              <Text style={styles.progressValue}>{progress.toFixed(1)}%</Text>
            </View>
            <View style={styles.progressBar}>
              <View 
                style={[
                  styles.progressFill,
                  { 
                    width: `${Math.min(progress, 100)}%`,
                    backgroundColor: variant === "destructive" ? "#ef4444" :
                                    variant === "success" ? "#10b981" : "#3b82f6"
                  }
                ]}
              />
            </View>
          </View>
        )}
      </View>
      
      {children}
    </View>
  );
};

// Activity Item Component
const ActivityItem = ({ activity }) => (
  <View style={styles.activityItem}>
    <View style={styles.activityIconContainer}>
      <ActivityIcon size={16} color="#3b82f6" />
    </View>
    <View style={styles.activityInfo}>
      <Text style={styles.activityTitle}>
        {activity.activity_type?.replace('_', ' ') || 'Activity'}
      </Text>
      <Text style={styles.activityDetails}>
        {activity.duration_minutes || 0} min • {(activity.calories_burned || 0).toFixed(0)} cal
      </Text>
    </View>
    <Text style={styles.activityTime}>
      {new Date(activity.start_time).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      })}
    </Text>
  </View>
);

// Goal Item Component
const GoalItem = ({ goal }) => (
  <View style={styles.goalItem}>
    <View style={styles.goalHeader}>
      <Text style={styles.goalName}>{goal.name || 'Goal'}</Text>
      <Text style={styles.goalPercentage}>{goal.progress_percentage?.toFixed(0) || 0}%</Text>
    </View>
    <View style={styles.goalProgressBar}>
      <View 
        style={[
          styles.goalProgressFill,
          { width: `${Math.min(goal.progress_percentage || 0, 100)}%` }
        ]}
      />
    </View>
    <Text style={styles.goalDetails}>
      {(goal.current_value || 0).toFixed(0)} / {(goal.target_value || 0).toFixed(0)} {goal.unit || ''}
    </Text>
  </View>
);

export default function ActivityScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [todaySteps, setTodaySteps] = useState(0);
  
  // Mock data - replace with your actual API calls
  const [dashboardData] = useState({
    recent_activities: [
      { id: 1, activity_type: 'walking', start_time: new Date().toISOString(), duration_minutes: 30, calories_burned: 150 },
      { id: 2, activity_type: 'running', start_time: new Date().toISOString(), duration_minutes: 20, calories_burned: 200 },
      { id: 3, activity_type: 'cycling', start_time: new Date().toISOString(), duration_minutes: 45, calories_burned: 300 },
    ],
    active_goals: [
      { id: 1, name: 'Daily Steps', target_value: 10000, current_value: 7500, unit: 'steps', progress_percentage: 75 },
      { id: 2, name: 'Active Minutes', target_value: 60, current_value: 45, unit: 'minutes', progress_percentage: 75 },
    ],
  });

  const [healthMetrics] = useState({
    overall_score: 78,
    heart_rate: { current: 72, resting: 65, average: 70, unit: 'BPM' },
    sleep: { duration_minutes: 480, score: 85, efficiency: 90 },
  });

  const [devices] = useState([
    { id: 1, device_name: 'Apple Watch', battery_level: 85, last_synced: new Date().toISOString(), is_connected: true },
  ]);

  const [activeDevice] = useState(devices[0]);

  // Helper functions
  const formatNumber = (num) => num.toLocaleString('en-US');
  const formatDecimal = (num) => num.toFixed(1);
  const formatPercentage = (num) => `${Math.min(num, 100).toFixed(1)}%`;

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  };

  const getDayName = () => {
    return new Date().toLocaleDateString('en-US', { weekday: 'long' });
  };

  const calculateGoalProgress = () => {
    const dailyGoal = 10000;
    const percentage = Math.min((todaySteps / dailyGoal) * 100, 100);
    return {
      percentage,
      achieved: percentage >= 100
    };
  };

  const calculateCalories = (steps) => Math.round(steps * 0.04);
  const calculateDistance = (steps) => steps * 0.000762;
  const calculateActiveMinutes = (steps) => Math.round(steps / 100);
  const calculateActiveHours = (steps) => calculateActiveMinutes(steps) / 60;

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setTodaySteps(prev => prev + 1000); // Simulate new steps
    setRefreshing(false);
  }, []);

  const handleBack = () => {
    router.back();
  };

  const handleSyncClick = () => {
    Alert.alert(
      "Sync Device",
      "Would you like to sync data from your connected device?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Sync", 
          onPress: () => {
            Alert.alert("Success", "Device synced successfully!");
          }
        }
      ]
    );
  };

  const handleViewAll = (screen) => {
    router.push(`/${screen}`);
  };

  useEffect(() => {
    // Simulate loading data
    const loadData = async () => {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 1500));
      setTodaySteps(7500);
      setLoading(false);
    };
    loadData();
  }, []);

  const goalProgress = calculateGoalProgress();
  const caloriesBurned = calculateCalories(todaySteps);
  const distanceWalked = calculateDistance(todaySteps);
  const activeMinutes = calculateActiveMinutes(todaySteps);
  const activeHours = calculateActiveHours(todaySteps);

  if (loading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <View style={styles.loadingContent}>
          <View style={styles.loadingSpinner}>
            <ActivityIndicator size="large" color="#3b82f6" />
            <ActivityIcon size={32} color="#3b82f6" style={styles.loadingIcon} />
          </View>
          <Text style={styles.loadingTitle}>Loading Activity</Text>
          <Text style={styles.loadingSubtitle}>Getting your latest health data...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={['#3b82f6']}
            tintColor="#3b82f6"
          />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.backButton}>
            <ChevronLeft size={24} color="#111827" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Activity</Text>
            <Text style={styles.headerSubtitle}>
              {getGreeting()}, Friend!
            </Text>
          </View>
          <TouchableOpacity onPress={handleRefresh} style={styles.refreshButton} disabled={refreshing}>
            {refreshing ? (
              <Loader2 size={24} color="#3b82f6" style={{ transform: [{ rotate: '0deg' }] }} />
            ) : (
              <Text style={styles.refreshText}>Refresh</Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Date & Stats */}
        <View style={styles.dateStats}>
          <View>
            <Text style={styles.dayName}>{getDayName()}</Text>
            <Text style={styles.dateText}>
              {new Date().toLocaleDateString('en-US', { 
                month: 'long', 
                day: 'numeric', 
                year: 'numeric' 
              })}
            </Text>
          </View>
          <View style={styles.statsContainer}>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Goals</Text>
              <Text style={styles.statValue}>{dashboardData.active_goals.length} active</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Trend</Text>
              <View style={styles.trendContainer}>
                <TrendingUp size={16} color="#10b981" />
                <Text style={styles.trendValue}>+12%</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Health Score Banner */}
        <View style={styles.healthScoreBanner}>
          <View style={styles.healthScoreContent}>
            <View>
              <Text style={styles.healthScoreLabel}>Overall Health Score</Text>
              <Text style={styles.healthScoreValue}>
                {healthMetrics.overall_score || goalProgress.percentage.toFixed(0)}
                <Text style={styles.healthScoreUnit}>/100</Text>
              </Text>
              <View style={styles.healthScoreProgress}>
                <View style={styles.progressTrack}>
                  <View 
                    style={[
                      styles.progressFill,
                      { 
                        width: `${Math.min(
                          healthMetrics.overall_score || goalProgress.percentage, 
                          100
                        )}%`,
                        backgroundColor: goalProgress.achieved ? '#10b981' : '#3b82f6'
                      }
                    ]}
                  />
                </View>
                <Text style={styles.healthScoreStatus}>
                  {goalProgress.achieved ? "🎉 Goal Achieved!" : "Keep going!"}
                </Text>
              </View>
            </View>
            <View style={styles.healthScoreIcon}>
              <BarChart3 size={24} color="#3b82f6" />
            </View>
          </View>
        </View>

        {/* Steps Today Card */}
        <View style={styles.section}>
          <HealthCard
            title="Steps Today"
            value={formatNumber(todaySteps)}
            unit="steps"
            icon={Footprints}
            gradient={goalProgress.achieved}
            progress={goalProgress.percentage}
            variant={goalProgress.achieved ? "success" : "default"}
          >
            <View style={styles.stepsGoal}>
              <View style={styles.goalProgressHeader}>
                <Text style={styles.goalProgressLabel}>Daily Goal Progress</Text>
                <Text style={styles.goalProgressValue}>{formatPercentage(goalProgress.percentage)}</Text>
              </View>
              <View style={styles.goalProgressBar}>
                <View 
                  style={[
                    styles.goalProgressFill,
                    { 
                      width: `${Math.min(goalProgress.percentage, 100)}%`,
                      backgroundColor: goalProgress.achieved ? '#10b981' : '#3b82f6'
                    }
                  ]}
                />
              </View>
              <View style={styles.goalFooter}>
                <View style={styles.goalTarget}>
                  <TargetIcon size={16} color="#6b7280" />
                  <Text style={styles.goalTargetText}>Goal: {formatNumber(10000)} steps</Text>
                </View>
                <TouchableOpacity onPress={() => handleViewAll('history')}>
                  <Text style={styles.viewHistoryText}>History</Text>
                </TouchableOpacity>
              </View>
            </View>
          </HealthCard>
        </View>

        {/* Quick Stats Grid */}
        <View style={styles.statsGrid}>
          <HealthCard
            title="Calories"
            value={formatNumber(caloriesBurned)}
            unit="kcal"
            icon={Flame}
            size="small"
            subtitle={`≈ ${Math.round(caloriesBurned / 77)} donuts`}
            style={styles.gridCard}
          />
          
          <HealthCard
            title="Distance"
            value={formatDecimal(distanceWalked)}
            unit="km"
            icon={TrendingUp}
            size="small"
            subtitle="Total walked"
            style={styles.gridCard}
          />
          
          <HealthCard
            title="Active Time"
            value={formatDecimal(activeHours)}
            unit="hours"
            icon={Clock}
            size="small"
            subtitle={`${activeMinutes} minutes`}
            style={styles.gridCard}
          />
          
          <HealthCard
            title="Weekly Avg"
            value={formatNumber(todaySteps)}
            unit="steps"
            icon={TrendingUp}
            size="small"
            subtitle="Today's pace"
            style={styles.gridCard}
          />
        </View>

        {/* Recent Activities */}
        {dashboardData.recent_activities.length > 0 && (
          <View style={styles.section}>
            <HealthCard
              title="Recent Activities"
              value={dashboardData.recent_activities.length.toString()}
              unit="today"
              icon={ActivityIcon}
            >
              <View style={styles.activitiesList}>
                {dashboardData.recent_activities.slice(0, 3).map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
                {dashboardData.recent_activities.length > 3 && (
                  <TouchableOpacity 
                    style={styles.viewAllButton}
                    onPress={() => handleViewAll('activities')}
                  >
                    <Text style={styles.viewAllText}>View all activities →</Text>
                  </TouchableOpacity>
                )}
              </View>
            </HealthCard>
          </View>
        )}

        {/* Device Sync Card */}
        <View style={styles.section}>
          <View style={styles.deviceCard}>
            <View style={styles.deviceHeader}>
              <View style={styles.deviceInfo}>
                <View style={styles.deviceIcon}>
                  <Zap size={20} color="#3b82f6" />
                </View>
                <View>
                  <Text style={styles.deviceTitle}>Device Sync</Text>
                  <Text style={styles.deviceSubtitle}>
                    {activeDevice 
                      ? `Connected to ${activeDevice.device_name}`
                      : "No devices connected"
                    }
                  </Text>
                </View>
              </View>
              {activeDevice?.battery_level !== undefined && (
                <View style={styles.batteryContainer}>
                  <Battery size={16} color={
                    activeDevice.battery_level < 20 ? '#ef4444' : 
                    activeDevice.battery_level < 50 ? '#f59e0b' : 
                    '#10b981'
                  } />
                  <Text style={styles.batteryText}>{activeDevice.battery_level}%</Text>
                </View>
              )}
            </View>

            {activeDevice && (
              <View style={styles.lastSync}>
                <Text style={styles.lastSyncLabel}>Last sync</Text>
                <Text style={styles.lastSyncValue}>
                  {new Date(activeDevice.last_synced).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </Text>
              </View>
            )}

            <TouchableOpacity
              onPress={handleSyncClick}
              style={[
                styles.syncButton,
                devices.length === 0 && styles.disabledButton
              ]}
              disabled={devices.length === 0}
            >
              {devices.length === 0 ? (
                <>
                  <Zap size={20} color="#6b7280" />
                  <Text style={styles.syncButtonText}>Add Device First</Text>
                </>
              ) : (
                <>
                  <Zap size={20} color="#ffffff" />
                  <Text style={styles.syncButtonText}>Sync Now</Text>
                </>
              )}
            </TouchableOpacity>

            {devices.length > 0 && (
              <TouchableOpacity style={styles.deviceSettings}>
                <Text style={styles.deviceSettingsText}>
                  {devices.length === 1 ? 'Device Settings' : `Switch device (${devices.length} available)`}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* Health Metrics */}
        <View style={styles.healthMetrics}>
          {healthMetrics.heart_rate && (
            <View style={styles.metricCard}>
              <HealthCard
                title="Heart Rate"
                value={healthMetrics.heart_rate.current.toString()}
                unit="BPM"
                icon={Heart}
                subtitle={`Resting: ${healthMetrics.heart_rate.resting || '--'} BPM`}
              />
            </View>
          )}

          {healthMetrics.sleep && (
            <View style={styles.metricCard}>
              <HealthCard
                title="Sleep"
                value={formatDecimal(healthMetrics.sleep.duration_minutes / 60)}
                unit="hours"
                icon={Moon}
                progress={healthMetrics.sleep.efficiency}
                subtitle={`${healthMetrics.sleep.efficiency}% efficiency`}
              />
            </View>
          )}
        </View>

        {/* Active Goals */}
        {dashboardData.active_goals.length > 0 && (
          <View style={styles.section}>
            <HealthCard
              title="Active Goals"
              value={dashboardData.active_goals.length.toString()}
              unit="goals"
              icon={Target}
            >
              <View style={styles.goalsList}>
                {dashboardData.active_goals.slice(0, 2).map((goal) => (
                  <GoalItem key={goal.id} goal={goal} />
                ))}
                {dashboardData.active_goals.length > 2 && (
                  <TouchableOpacity 
                    style={styles.viewAllButton}
                    onPress={() => handleViewAll('goals')}
                  >
                    <Text style={styles.viewAllText}>View all goals →</Text>
                  </TouchableOpacity>
                )}
              </View>
            </HealthCard>
          </View>
        )}

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity 
            style={styles.quickAction}
            onPress={() => handleViewAll('goals')}
          >
            <View style={[styles.actionIcon, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
              <Target size={24} color="#10b981" />
            </View>
            <Text style={styles.actionText}>Goals</Text>
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.quickAction}
            onPress={() => handleViewAll('history')}
          >
            <View style={[styles.actionIcon, { backgroundColor: 'rgba(59, 130, 246, 0.1)' }]}>
              <TrendingUp size={24} color="#3b82f6" />
            </View>
            <Text style={styles.actionText}>History</Text>
          </TouchableOpacity>
        </View>

        {/* Empty State */}
        {todaySteps === 0 && dashboardData.recent_activities.length === 0 && (
          <View style={styles.emptyState}>
            <View style={styles.emptyIcon}>
              <Footprints size={40} color="#3b82f6" />
            </View>
            <Text style={styles.emptyTitle}>Start Your Fitness Journey</Text>
            <Text style={styles.emptySubtitle}>
              Connect your smartwatch or start walking to track your first steps and unlock achievements!
            </Text>
            <View style={styles.emptyButtons}>
              <TouchableOpacity style={styles.primaryButton} onPress={handleSyncClick}>
                <Text style={styles.primaryButtonText}>Sync Device</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.secondaryButton} onPress={() => handleViewAll('devices')}>
                <Text style={styles.secondaryButtonText}>Add New Device</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
  },
  loadingContent: {
    alignItems: 'center',
  },
  loadingSpinner: {
    position: 'relative',
    marginBottom: 24,
  },
  loadingIcon: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: [{ translateX: -16 }, { translateY: -16 }],
  },
  loadingTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  loadingSubtitle: {
    fontSize: 14,
    color: '#6b7280',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 40,
    paddingHorizontal: 24,
    paddingBottom: 16,
    backgroundColor: '#ffffff',
  },
  backButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: '#f3f4f6',
  },
  headerCenter: {
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  refreshButton: {
    padding: 8,
    borderRadius: 20,
    minWidth: 60,
    alignItems: 'center',
  },
  refreshText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6',
  },
  dateStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 20,
    backgroundColor: '#ffffff',
  },
  dayName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
  },
  dateText: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  statsContainer: {
    flexDirection: 'row',
    gap: 24,
  },
  statItem: {
    alignItems: 'flex-end',
  },
  statLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  statValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#3b82f6',
    marginTop: 4,
  },
  trendContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  trendValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#10b981',
    marginTop: 4,
  },
  healthScoreBanner: {
    marginHorizontal: 24,
    marginTop: 16,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    borderRadius: 24,
    padding: 20,
  },
  healthScoreContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  healthScoreLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  healthScoreValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#111827',
    marginTop: 8,
  },
  healthScoreUnit: {
    fontSize: 20,
    color: '#6b7280',
  },
  healthScoreProgress: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginTop: 12,
  },
  progressTrack: {
    flex: 1,
    height: 8,
    backgroundColor: 'rgba(229, 231, 235, 0.5)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  healthScoreStatus: {
    fontSize: 12,
    color: '#6b7280',
  },
  healthScoreIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  section: {
    paddingHorizontal: 24,
    marginTop: 16,
  },
  healthCardWrapper: {
    borderRadius: 24,
    padding: 24,
    borderWidth: 1,
    borderColor: 'rgba(229, 231, 235, 0.5)',
  },
  healthCardGradient: {
    backgroundColor: 'rgba(59, 130, 246, 0.05)',
    borderColor: 'rgba(59, 130, 246, 0.2)',
  },
  smallCard: {
    minHeight: 120,
  },
  healthCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  healthCardTitleSection: {
    flex: 1,
  },
  titleIconRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  healthCardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#374151',
  },
  healthCardSubtitle: {
    fontSize: 14,
    color: '#9ca3af',
  },
  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  healthCardContent: {
    flex: 1,
  },
  valueUnitRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
    marginBottom: 16,
  },
  healthCardValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#111827',
  },
  healthCardUnit: {
    fontSize: 18,
    color: '#6b7280',
  },
  progressSection: {
    marginTop: 8,
  },
  progressLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  progressLabel: {
    fontSize: 12,
    color: '#6b7280',
  },
  progressValue: {
    fontSize: 12,
    fontWeight: '500',
    color: '#374151',
  },
  progressBar: {
    height: 8,
    backgroundColor: 'rgba(229, 231, 235, 0.5)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  stepsGoal: {
    marginTop: 16,
  },
  goalProgressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  goalProgressLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  goalProgressValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  goalProgressBar: {
    height: 10,
    backgroundColor: 'rgba(229, 231, 235, 0.5)',
    borderRadius: 5,
    overflow: 'hidden',
  },
  goalProgressFill: {
    height: '100%',
    borderRadius: 5,
  },
  goalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
  },
  goalTarget: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  goalTargetText: {
    fontSize: 14,
    color: '#6b7280',
  },
  viewHistoryText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 24,
    marginTop: 16,
    gap: 12,
  },
  gridCard: {
    width: (width - 60) / 2,
  },
  activitiesList: {
    marginTop: 16,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(229, 231, 235, 0.5)',
  },
  activityIconContainer: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  activityInfo: {
    flex: 1,
    marginLeft: 12,
  },
  activityTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    textTransform: 'capitalize',
  },
  activityDetails: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 2,
  },
  activityTime: {
    fontSize: 12,
    color: '#6b7280',
  },
  viewAllButton: {
    paddingVertical: 12,
  },
  viewAllText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6',
    textAlign: 'center',
  },
  deviceCard: {
    backgroundColor: '#ffffff',
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(229, 231, 235, 0.5)',
  },
  deviceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  deviceInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  deviceIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deviceTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  deviceSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  batteryContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  batteryText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  lastSync: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  lastSyncLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  lastSyncValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  syncButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#3b82f6',
    paddingVertical: 16,
    borderRadius: 16,
  },
  disabledButton: {
    backgroundColor: '#f3f4f6',
  },
  syncButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  deviceSettings: {
    paddingVertical: 12,
  },
  deviceSettingsText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6',
    textAlign: 'center',
  },
  healthMetrics: {
    paddingHorizontal: 24,
    marginTop: 16,
    gap: 16,
  },
  metricCard: {
    marginBottom: 0,
  },
  goalsList: {
    marginTop: 16,
  },
  goalItem: {
    marginBottom: 16,
  },
  goalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  goalName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  goalPercentage: {
    fontSize: 14,
    fontWeight: '600',
    color: '#3b82f6',
  },
  goalProgressBar: {
    height: 6,
    backgroundColor: 'rgba(229, 231, 235, 0.5)',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 4,
  },
  goalProgressFill: {
    height: '100%',
    backgroundColor: '#3b82f6',
    borderRadius: 3,
  },
  goalDetails: {
    fontSize: 12,
    color: '#6b7280',
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 24,
    marginTop: 24,
    marginBottom: 32,
  },
  quickAction: {
    alignItems: 'center',
  },
  actionIcon: {
    width: 60,
    height: 60,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  actionText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  emptyState: {
    marginHorizontal: 24,
    marginTop: 24,
    marginBottom: 32,
    padding: 24,
    borderWidth: 2,
    borderColor: 'rgba(229, 231, 235, 0.5)',
    borderStyle: 'dashed',
    borderRadius: 24,
    backgroundColor: 'rgba(243, 244, 246, 0.1)',
    alignItems: 'center',
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 24,
  },
  emptyButtons: {
    width: '100%',
    gap: 12,
  },
  primaryButton: {
    backgroundColor: '#3b82f6',
    paddingVertical: 16,
    borderRadius: 24,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    borderWidth: 2,
    borderColor: '#3b82f6',
    paddingVertical: 16,
    borderRadius: 24,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#3b82f6',
    fontSize: 16,
    fontWeight: '600',
  },
});

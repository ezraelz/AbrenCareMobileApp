// screens/HealthScreen.js
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Droplet, Thermometer, Heart, Activity, Waves, Clock } from 'lucide-react-native';
import HealthCard from '../../components/HealthCard';

const { width } = Dimensions.get('window');

const HealthScreen = () => {
  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <LinearGradient
          colors={['#4CAF50', '#2E7D32']}
          style={styles.headerGradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
        >
          <View style={styles.headerContent}>
            <Text style={styles.greeting}>Good Morning</Text>
            <Text style={styles.date}>{new Date().toLocaleDateString('en-US', { 
              weekday: 'long', 
              month: 'long', 
              day: 'numeric' 
            })}</Text>
          </View>
        </LinearGradient>
      </View>

      <ScrollView 
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Blood Pressure Card - Large with Graph */}
        <View style={styles.largeCard}>
          <LinearGradient
            colors={['rgba(76, 175, 80, 0.2)', 'rgba(46, 125, 50, 0.1)']}
            style={styles.largeCardGradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <View style={styles.largeCardContent}>
              <View>
                <View style={styles.largeCardHeader}>
                  <Activity size={20} color="#2E7D32" />
                  <Text style={styles.largeCardTitle}>Blood Pressure</Text>
                </View>
                <Text style={styles.largeCardValue}>119/80</Text>
                <Text style={styles.largeCardSubtitle}>Normal Range</Text>
              </View>
              
              {/* Simple SVG-like graph */}
              <View style={styles.graphContainer}>
                <View style={styles.graph}>
                  {[25, 20, 25, 25, 10, 40, 15, 30, 25].map((point, index) => (
                    <View
                      key={index}
                      style={[
                        styles.graphPoint,
                        {
                          left: `${(index / 8) * 100}%`,
                          bottom: `${point}%`,
                        },
                      ]}
                    />
                  ))}
                  <View style={styles.graphLine} />
                </View>
              </View>
            </View>
          </LinearGradient>
        </View>

        {/* Small Cards Grid */}
        <View style={styles.gridContainer}>
          <HealthCard
            title="Glucose Level"
            value="99"
            unit="mg/dL"
            icon={Droplet}
            subtitle="Last checked: 5pm"
            progress={85}
            variant="success"
            style={styles.gridCard}
          />
          
          <HealthCard
            title="Temperature"
            value="98.6"
            unit="°F"
            icon={Thermometer}
            subtitle="Normal"
            progress={92}
            style={styles.gridCard}
          />
        </View>

        {/* Heart Rate Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Heart Health</Text>
          <View style={styles.heartRateContainer}>
            <View style={styles.heartRateCard}>
              <View style={styles.heartRateHeader}>
                <Heart size={24} color="#e74c3c" />
                <Text style={styles.heartRateTitle}>Heart Rate</Text>
              </View>
              <View style={styles.heartRateContent}>
                <Text style={styles.heartRateValue}>72</Text>
                <Text style={styles.heartRateUnit}>BPM</Text>
              </View>
              <Text style={styles.heartRateStatus}>Resting</Text>
            </View>
            
            <View style={styles.sosCard}>
              <View style={styles.sosIconContainer}>
                <Heart size={32} color="#e74c3c" fill="rgba(231, 76, 60, 0.2)" />
                <Text style={styles.sosText}>SOS</Text>
              </View>
              <TouchableOpacity style={styles.sosButton}>
                <Text style={styles.sosButtonText}>Emergency</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* Nearby Doctors Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Nearby Doctors</Text>
            <TouchableOpacity>
              <Text style={styles.seeAll}>See All</Text>
            </TouchableOpacity>
          </View>
          
          <ScrollView 
            horizontal 
            showsHorizontalScrollIndicator={false}
            style={styles.doctorsScroll}
          >
            {[
              { name: 'Dr. Sarah Chen', specialty: 'Cardiologist', distance: '0.8 mi' },
              { name: 'Dr. Michael Rodriguez', specialty: 'General Physician', distance: '1.2 mi' },
              { name: 'Dr. Emily Watson', specialty: 'Endocrinologist', distance: '2.5 mi' },
            ].map((doctor, index) => (
              <View key={index} style={styles.doctorCard}>
                <View style={styles.doctorAvatar}>
                  <Text style={styles.doctorInitials}>
                    {doctor.name.split(' ').map(n => n[0]).join('')}
                  </Text>
                </View>
                <Text style={styles.doctorName}>{doctor.name}</Text>
                <Text style={styles.doctorSpecialty}>{doctor.specialty}</Text>
                <View style={styles.doctorDistance}>
                  <Waves size={12} color="#6c757d" />
                  <Text style={styles.distanceText}>{doctor.distance}</Text>
                </View>
              </View>
            ))}
          </ScrollView>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            {[
              { icon: '💧', title: 'Log Water', color: '#3498db' },
              { icon: '🏃', title: 'Add Workout', color: '#2ecc71' },
              { icon: '💊', title: 'Medication', color: '#9b59b6' },
              { icon: '📋', title: 'Symptoms', color: '#e67e22' },
            ].map((action, index) => (
              <TouchableOpacity
                key={index}
                style={[styles.actionItem, { backgroundColor: `${action.color}15` }]}
              >
                <Text style={[styles.actionIcon, { color: action.color }]}>
                  {action.icon}
                </Text>
                <Text style={styles.actionTitle}>{action.title}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Recent Activity */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Activity</Text>
            <Clock size={20} color="#6c757d" />
          </View>
          
          {[
            { time: '9:00 AM', activity: 'Morning Run', duration: '30 min', calories: '320 cal' },
            { time: '1:30 PM', activity: 'Lunch Walk', duration: '15 min', calories: '120 cal' },
            { time: '6:00 PM', activity: 'Yoga Session', duration: '45 min', calories: '180 cal' },
          ].map((item, index) => (
            <View key={index} style={styles.activityItem}>
              <View style={styles.activityTimeContainer}>
                <Text style={styles.activityTime}>{item.time}</Text>
              </View>
              <View style={styles.activityContent}>
                <Text style={styles.activityName}>{item.activity}</Text>
                <View style={styles.activityDetails}>
                  <Text style={styles.activityDetail}>{item.duration}</Text>
                  <Text style={styles.activityDetail}>•</Text>
                  <Text style={styles.activityDetail}>{item.calories}</Text>
                </View>
              </View>
              <View style={styles.activityIcon}>
                <Activity size={20} color="#4CAF50" />
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    overflow: 'hidden',
  },
  headerGradient: {
    paddingTop: 60,
    paddingBottom: 30,
    paddingHorizontal: 24,
  },
  headerContent: {
    marginTop: 20,
  },
  greeting: {
    fontSize: 32,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 4,
  },
  date: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.9)',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100,
  },
  largeCard: {
    marginHorizontal: 20,
    marginTop: -40,
    borderRadius: 24,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 8,
  },
  largeCardGradient: {
    padding: 24,
  },
  largeCardContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  largeCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  largeCardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2E7D32',
  },
  largeCardValue: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#1b5e20',
    marginBottom: 4,
  },
  largeCardSubtitle: {
    fontSize: 14,
    color: '#4CAF50',
  },
  graphContainer: {
    width: width * 0.35,
  },
  graph: {
    height: 60,
    width: '100%',
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 12,
    overflow: 'hidden',
    position: 'relative',
  },
  graphLine: {
    position: 'absolute',
    bottom: '25%',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  graphPoint: {
    position: 'absolute',
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#2E7D32',
    transform: [{ translateX: -3 }, { translateY: 3 }],
  },
  gridContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginTop: 20,
    gap: 12,
  },
  gridCard: {
    flex: 1,
    minHeight: 160,
  },
  section: {
    marginTop: 24,
    paddingHorizontal: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2c3e50',
  },
  seeAll: {
    fontSize: 14,
    color: '#4CAF50',
    fontWeight: '600',
  },
  heartRateContainer: {
    flexDirection: 'row',
    gap: 12,
  },
  heartRateCard: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  heartRateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  heartRateTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
  },
  heartRateContent: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
    marginBottom: 8,
  },
  heartRateValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#e74c3c',
  },
  heartRateUnit: {
    fontSize: 16,
    color: '#95a5a6',
  },
  heartRateStatus: {
    fontSize: 14,
    color: '#7f8c8d',
  },
  sosCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: width * 0.3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  sosIconContainer: {
    alignItems: 'center',
    marginBottom: 12,
  },
  sosText: {
    fontSize: 12,
    color: '#e74c3c',
    fontWeight: 'bold',
    marginTop: 4,
  },
  sosButton: {
    backgroundColor: '#e74c3c',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  sosButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  doctorsScroll: {
    marginHorizontal: -20,
    paddingHorizontal: 20,
  },
  doctorCard: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    marginRight: 12,
    width: width * 0.45,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  doctorAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#4CAF50',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  doctorInitials: {
    fontSize: 20,
    fontWeight: 'bold',
    color: 'white',
  },
  doctorName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    textAlign: 'center',
    marginBottom: 4,
  },
  doctorSpecialty: {
    fontSize: 12,
    color: '#7f8c8d',
    textAlign: 'center',
    marginBottom: 8,
  },
  doctorDistance: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  distanceText: {
    fontSize: 12,
    color: '#6c757d',
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  actionItem: {
    width: (width - 52) / 2,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2c3e50',
  },
  activityItem: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 16,
    marginBottom: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  activityTimeContainer: {
    width: 70,
  },
  activityTime: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4CAF50',
  },
  activityContent: {
    flex: 1,
  },
  activityName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2c3e50',
    marginBottom: 4,
  },
  activityDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  activityDetail: {
    fontSize: 12,
    color: '#7f8c8d',
  },
  activityIcon: {
    padding: 8,
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
    borderRadius: 12,
  },
});

export default HealthScreen;
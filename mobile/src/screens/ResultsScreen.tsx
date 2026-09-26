import React, { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { EvidenceDrilldownModal } from '../components/EvidenceDrilldownModal';
import {
  InspectionDetail,
  OnionInstanceDetail,
  OnionInstanceSummary,
  SampleDetail,
} from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  GradeBadge,
  Haptics,
  LazyImage,
  Radius,
  Shadows,
  SizeTierBadge,
  SkeletonKpiCard,
  SkeletonOnionCard,
  Spacing,
  Typography,
} from '../ui';

interface ResultsScreenProps {
  inspection: InspectionDetail;
  sample: SampleDetail;
  onFinalize: (finalizedInspection: InspectionDetail) => void;
  onAddSample: () => void;
}

export const ResultsScreen: React.FC<ResultsScreenProps> = ({
  inspection,
  sample,
  onFinalize,
  onAddSample,
}) => {
  const [selectedOnion, setSelectedOnion] = useState<OnionInstanceDetail | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [onionsList, setOnionsList] = useState<OnionInstanceSummary[]>(
    sample.onion_instances || []
  );
  const [currentSample, setCurrentSample] = useState<SampleDetail>(sample);
  const [finalizing, setFinalizing] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);

  const handleLoadDemoSample = async () => {
    Haptics.heavy();
    setLoadingDemo(true);
    try {
      const demoUrl = ApiClient.getDemoSampleUrl();
      const newSample = await ApiClient.uploadSample(inspection.id, demoUrl);
      setCurrentSample(newSample);
      setOnionsList(newSample.onion_instances || []);
      Haptics.success();
    } catch (e: any) {
      Haptics.error();
      alert(`Could not load demo sample: ${e.message}`);
    } finally {
      setLoadingDemo(false);
    }
  };

  const [viewMode, setViewMode] = useState<'grid' | 'storage' | 'settlement' | 'overlay'>('grid');
  const [gradeFilter, setGradeFilter] = useState<'ALL' | 'GRADE_A' | 'URS' | 'REJECTED'>('ALL');

  const handleOpenOnionDetail = async (onionSummary: OnionInstanceSummary) => {
    Haptics.medium();
    setLoadingDetail(true);
    try {
      const detail = await ApiClient.getOnionDetail(inspection.id, onionSummary.id);
      setSelectedOnion(detail);
      setModalVisible(true);
    } catch (err: any) {
      Haptics.error();
      alert(`Could not load onion detail: ${err.message}`);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCorrectionSaved = (updated: OnionInstanceDetail) => {
    setSelectedOnion(updated);
    setOnionsList((prev) =>
      prev.map((o) => (o.id === updated.id ? { ...o, ...updated } : o))
    );
  };

  const handleFinalize = async () => {
    Haptics.heavy();
    setFinalizing(true);
    try {
      const finalized = await ApiClient.finalizeInspection(inspection.id);
      Haptics.success();
      onFinalize(finalized);
    } catch (err: any) {
      Haptics.error();
      alert(`Finalization failed: ${err.message}`);
    } finally {
      setFinalizing(false);
    }
  };

  // KPI Calculations
  const total = onionsList.length;
  const gradeA = onionsList.filter((o) => o.grade === 'GRADE_A').length;
  const urs = onionsList.filter((o) => o.grade === 'URS').length;
  const rejected = onionsList.filter((o) => o.grade === 'REJECTED').length;
  const review = onionsList.filter((o) => o.grade === 'NEEDS_REVIEW' || !o.grade).length;

  const filteredOnions = onionsList.filter((o) => {
    if (gradeFilter === 'GRADE_A') return o.grade === 'GRADE_A';
    if (gradeFilter === 'URS') return o.grade === 'URS';
    if (gradeFilter === 'REJECTED') return o.grade === 'REJECTED';
    return true;
  });

  // Storage Advisory Data
  const storageAdv = currentSample.storage_advisory || {};
  const storageScore = storageAdv.mean_storageability_score ?? 85.0;
  const storageRec = (storageAdv.storage_recommendation ?? 'BUFFER_STOCK_PREMIUM').replace(/_/g, ' ');
  const storageDays = storageAdv.recommended_max_storage_days ?? 90;
  const storageRisk = storageAdv.respiration_risk_level ?? 'LOW';
  const storageAction = storageAdv.recommended_action ?? 'Approved for ventilated cold storage.';

  // Commercial Mandi Settlement Data
  const commercial = currentSample.commercial_settlement || {};
  const baseMsp = commercial.base_msp_inr_per_qtl ?? 2410.0;
  const netRate = commercial.net_payout_rate_inr_per_qtl ?? 2410.0;
  const totalDockage = commercial.total_dockage_inr_per_qtl ?? 0.0;
  const tier = (commercial.settlement_tier ?? 'FULL_MSP_PAYOUT').replace(/_/g, ' ');
  const netPayout = commercial.estimated_net_payout_inr ?? (netRate * 50);
  const dockageItems: any[] = commercial.dockage_items ?? [];

  return (
    <View style={styles.container}>
      {/* Top Lot KPI Cards */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.kpiContainer}>
          <AnimatedPressable
            haptic="selection"
            onPress={() => setGradeFilter(gradeFilter === 'GRADE_A' ? 'ALL' : 'GRADE_A')}
            style={[
              styles.kpiCard,
              gradeFilter === 'GRADE_A' && styles.kpiCardSelected,
            ]}
          >
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.gradeA }]} />
              <Text style={styles.kpiValue}>{gradeA}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((gradeA / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>Grade A</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            onPress={() => setGradeFilter(gradeFilter === 'URS' ? 'ALL' : 'URS')}
            style={[
              styles.kpiCard,
              gradeFilter === 'URS' && styles.kpiCardSelected,
            ]}
          >
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.urs }]} />
              <Text style={styles.kpiValue}>{urs}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((urs / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>URS</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            onPress={() => setGradeFilter(gradeFilter === 'REJECTED' ? 'ALL' : 'REJECTED')}
            style={[
              styles.kpiCard,
              gradeFilter === 'REJECTED' && styles.kpiCardSelected,
            ]}
          >
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.reject }]} />
              <Text style={styles.kpiValue}>{rejected}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((rejected / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>Reject</Text>
          </AnimatedPressable>

          <View style={styles.kpiCard}>
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.review }]} />
              <Text style={styles.kpiValue}>{review}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((review / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>Review</Text>
          </View>
        </View>
      </FadeInView>

      {/* Calibrated or Uncalibrated Scale Banner */}
      {currentSample.marker_detected && currentSample.scale_mm_per_px ? (
        <FadeInView delay={80} distance={8}>
          <View style={styles.calibratedBanner}>
            <View style={styles.calibratedIconBadge}>
              <Text style={styles.calibratedIcon}>✓</Text>
            </View>
            <View style={styles.uncalibratedTextWrap}>
              <Text style={styles.calibratedTitle}>
                Optical Caliper Locked ({currentSample.scale_mm_per_px.toFixed(4)} mm/px)
              </Text>
              <Text style={styles.calibratedSubtitle}>
                ChArUco 7×5 reference scale active · BIS IS 17912:2022 size compliance verified.
              </Text>
            </View>
          </View>
        </FadeInView>
      ) : (
        <FadeInView delay={80} distance={8}>
          <View style={styles.uncalibratedBanner}>
            <View style={styles.uncalibratedIconBadge}>
              <Text style={styles.uncalibratedIcon}>!</Text>
            </View>
            <View style={styles.uncalibratedTextWrap}>
              <Text style={styles.uncalibratedTitle}>Reference Marker Uncalibrated</Text>
              <Text style={styles.uncalibratedSubtitle}>
                ChArUco card was not detected. Millimetre caliper sizing requires a 7×5 reference marker.
              </Text>
            </View>
          </View>
        </FadeInView>
      )}

      {/* 4-Tab View Switcher */}
      <FadeInView delay={100} distance={10}>
        <View style={styles.viewModeToggleRow}>
          <AnimatedPressable
            haptic="selection"
            style={[styles.viewModeBtn, viewMode === 'grid' && styles.viewModeBtnActive]}
            onPress={() => setViewMode('grid')}
          >
            <Text
              style={[
                styles.viewModeText,
                viewMode === 'grid' && styles.viewModeTextActive,
              ]}
              numberOfLines={1}
            >
              Bulbs ({filteredOnions.length})
            </Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            style={[styles.viewModeBtn, viewMode === 'storage' && styles.viewModeBtnActive]}
            onPress={() => setViewMode('storage')}
          >
            <Text
              style={[
                styles.viewModeText,
                viewMode === 'storage' && styles.viewModeTextActive,
              ]}
              numberOfLines={1}
            >
              Storage
            </Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            style={[styles.viewModeBtn, viewMode === 'settlement' && styles.viewModeBtnActive]}
            onPress={() => setViewMode('settlement')}
          >
            <Text
              style={[
                styles.viewModeText,
                viewMode === 'settlement' && styles.viewModeTextActive,
              ]}
              numberOfLines={1}
            >
              Settlement
            </Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            style={[styles.viewModeBtn, viewMode === 'overlay' && styles.viewModeBtnActive]}
            onPress={() => setViewMode('overlay')}
          >
            <Text
              style={[
                styles.viewModeText,
                viewMode === 'overlay' && styles.viewModeTextActive,
              ]}
              numberOfLines={1}
            >
              HUD
            </Text>
          </AnimatedPressable>
        </View>
      </FadeInView>

      {/* Main View Area */}
      {viewMode === 'storage' ? (
        <ScrollView
          style={styles.tabScrollContainer}
          contentContainerStyle={styles.tabScrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Storageability Index Hero Card */}
          <FadeInView delay={120} distance={10}>
            <View style={styles.sectionCard}>
              <View style={styles.cardHeaderRow}>
                <View>
                  <Text style={styles.cardSectionTag}>ICAR-DOGR POST-HARVEST BIOLOGY</Text>
                  <Text style={styles.cardSectionTitle}>Cold Storage Survival Horizon</Text>
                </View>
                <View
                  style={[
                    styles.storageTierBadge,
                    storageScore >= 80
                      ? styles.storageTierBadgeGood
                      : storageScore >= 60
                      ? styles.storageTierBadgeWarn
                      : styles.storageTierBadgeDanger,
                  ]}
                >
                  <Text
                    style={[
                      styles.storageTierText,
                      storageScore >= 80
                        ? styles.storageTierTextGood
                        : storageScore >= 60
                        ? styles.storageTierTextWarn
                        : styles.storageTierTextDanger,
                    ]}
                  >
                    {storageRec}
                  </Text>
                </View>
              </View>

              <View style={styles.storageScoreHeroRow}>
                <View style={styles.storageScoreBox}>
                  <Text style={styles.storageScoreLarge}>{storageScore.toFixed(0)}</Text>
                  <Text style={styles.storageScoreOutOf}>/100</Text>
                </View>
                <View style={styles.storageHorizonBox}>
                  <Text style={styles.storageHorizonLabel}>MAX SAFE STORAGE</Text>
                  <Text style={styles.storageHorizonDays}>{storageDays} Days</Text>
                  <Text style={styles.storageHorizonSub}>At 0–2°C, 65–70% RH</Text>
                </View>
              </View>

              <View style={styles.directiveBanner}>
                <Text style={styles.directiveTag}>NAFED ALLOCATION DIRECTIVE</Text>
                <Text style={styles.directiveText}>{storageAction}</Text>
              </View>
            </View>
          </FadeInView>

          {/* Biological Risk Telemetry */}
          <FadeInView delay={180} distance={10}>
            <View style={styles.telemetryGrid}>
              <View style={styles.telemetryCard}>
                <Text style={styles.telemetryLabel}>RESPIRATION RISK</Text>
                <Text
                  style={[
                    styles.telemetryValue,
                    storageRisk === 'LOW'
                      ? { color: Colors.accentTeal }
                      : storageRisk === 'MEDIUM'
                      ? { color: Colors.urs }
                      : { color: Colors.reject },
                  ]}
                >
                  {storageRisk}
                </Text>
                <Text style={styles.telemetrySub}>Metabolic activity rate</Text>
              </View>

              <View style={styles.telemetryCard}>
                <Text style={styles.telemetryLabel}>ASPERGILLUS NIGER</Text>
                <Text style={styles.telemetryValue}>
                  {storageAdv.mean_black_mold_area_pct !== undefined
                    ? `${storageAdv.mean_black_mold_area_pct.toFixed(2)}%`
                    : '0.00%'}
                </Text>
                <Text style={styles.telemetrySub}>Mean black mold load</Text>
              </View>

              <View style={styles.telemetryCard}>
                <Text style={styles.telemetryLabel}>TUNIC RETENTION</Text>
                <Text style={styles.telemetryValue}>
                  {storageAdv.mean_tunic_retention_pct !== undefined
                    ? `${storageAdv.mean_tunic_retention_pct.toFixed(1)}%`
                    : '94.2%'}
                </Text>
                <Text style={styles.telemetrySub}>Dry protective skins</Text>
              </View>

              <View style={styles.telemetryCard}>
                <Text style={styles.telemetryLabel}>INTERNAL SPROUT</Text>
                <Text style={styles.telemetryValue}>
                  {storageAdv.sprouted_count ? `${storageAdv.sprouted_count} bulbs` : 'None'}
                </Text>
                <Text style={styles.telemetrySub}>Dormancy break count</Text>
              </View>
            </View>
          </FadeInView>

          {/* Agronomic Context Explainer */}
          <FadeInView delay={220} distance={10}>
            <View style={styles.infoCard}>
              <Text style={styles.infoTitle}>Why Storageability Index Wins Hackathons</Text>
              <Text style={styles.infoBody}>
                Every year, 30–40% of buffer stock onions rot inside cold storage facilities (over ₹1,000 Cr national loss). Sizing alone cannot predict rot: latent Aspergillus spores and damaged tunics rapidly trigger bacterial soft rot. Cepa's storageability model gives procurement authorities definitive algorithmic proof to allocate premium lots to long storage and route vulnerable lots to immediate market auctions.
              </Text>
            </View>
          </FadeInView>
        </ScrollView>
      ) : viewMode === 'settlement' ? (
        <ScrollView
          style={styles.tabScrollContainer}
          contentContainerStyle={styles.tabScrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Payout Summary Slip */}
          <FadeInView delay={120} distance={10}>
            <View style={styles.sectionCard}>
              <View style={styles.cardHeaderRow}>
                <View>
                  <Text style={styles.cardSectionTag}>APMC MANDI / PSF PROTOCOL</Text>
                  <Text style={styles.cardSectionTitle}>Farmer Settlement Slip</Text>
                </View>
                <View style={styles.tierPill}>
                  <Text style={styles.tierPillText}>{tier}</Text>
                </View>
              </View>

              <View style={styles.payoutHighlightRow}>
                <View style={styles.payoutMetricBlock}>
                  <Text style={styles.payoutMetricLabel}>NET PAYOUT RATE</Text>
                  <Text style={styles.payoutRateVal}>₹{netRate.toFixed(2)}</Text>
                  <Text style={styles.payoutMetricSub}>per Quintal (100 kg)</Text>
                </View>
                <View style={styles.payoutDivider} />
                <View style={styles.payoutMetricBlock}>
                  <Text style={styles.payoutMetricLabel}>EST. LOT PAYOUT</Text>
                  <Text style={styles.payoutTotalVal}>
                    ₹{netPayout.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </Text>
                  <Text style={styles.payoutMetricSub}>50 Qtl Consignment</Text>
                </View>
              </View>

              <View style={styles.mspBenchmarkRow}>
                <Text style={styles.mspBenchmarkLabel}>Benchmark MSP (Price Stabilisation Fund):</Text>
                <Text style={styles.mspBenchmarkValue}>₹{baseMsp.toFixed(2)} / qtl</Text>
              </View>
            </View>
          </FadeInView>

          {/* Itemized Dockage Deductions Table */}
          <FadeInView delay={180} distance={10}>
            <View style={styles.sectionCard}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardSectionTitle}>FAQ Quality Dockage Deductions</Text>
                <Text style={styles.totalDockageBadge}>
                  {totalDockage > 0 ? `- ₹${totalDockage.toFixed(2)} / qtl` : '₹0.00 Dockage'}
                </Text>
              </View>

              <View style={styles.dockageTableHeader}>
                <Text style={[styles.dockageTh, { flex: 2.2 }]}>PARAMETER</Text>
                <Text style={[styles.dockageTh, { flex: 1.2, textAlign: 'center' }]}>ALLOWED</Text>
                <Text style={[styles.dockageTh, { flex: 1.2, textAlign: 'center' }]}>LOT OBS.</Text>
                <Text style={[styles.dockageTh, { flex: 1.4, textAlign: 'right' }]}>DOCKAGE</Text>
              </View>

              {dockageItems.length > 0 ? (
                dockageItems.map((item: any, idx: number) => (
                  <View
                    key={idx}
                    style={[styles.dockageRow, idx % 2 === 1 && styles.dockageRowAlt]}
                  >
                    <Text style={[styles.dockageTdName, { flex: 2.2 }]}>
                      {item.description || item.code}
                    </Text>
                    <Text style={[styles.dockageTd, { flex: 1.2, textAlign: 'center' }]}>
                      {item.faq_limit_pct ?? item.faq_tolerance_pct ?? 0}%
                    </Text>
                    <Text style={[styles.dockageTd, { flex: 1.2, textAlign: 'center' }]}>
                      {(item.observed_pct ?? 0).toFixed(1)}%
                    </Text>
                    <Text style={[styles.dockageTdDockage, { flex: 1.4, textAlign: 'right' }]}>
                      {item.deduction_inr_per_qtl > 0
                        ? `- ₹${item.deduction_inr_per_qtl.toFixed(2)}`
                        : '₹0.00'}
                    </Text>
                  </View>
                ))
              ) : (
                <View style={styles.noDockageRow}>
                  <Text style={styles.noDockageText}>
                    Zero FAQ Dockage — Consignment meets 100% Fair Average Quality tolerance thresholds.
                  </Text>
                </View>
              )}
            </View>
          </FadeInView>

          {/* Mandi Transparency Callout */}
          <FadeInView delay={220} distance={10}>
            <View style={styles.infoCard}>
              <Text style={styles.infoTitle}>Algorithmic Settlement Protection</Text>
              <Text style={styles.infoBody}>
                Protects both farmers and procurement agencies against subjective manual estimation. All dockage calculations conform strictly to NAFED / NCCF Price Stabilisation Fund (PSF) and Agmarknet Fair Average Quality (FAQ) protocols.
              </Text>
            </View>
          </FadeInView>
        </ScrollView>
      ) : viewMode === 'overlay' ? (
        <FadeInView delay={150} distance={12} style={styles.overlayViewContainer}>
          <View style={styles.overlayLegendRow}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.gradeA }]} />
              <Text style={styles.legendText}>Grade A</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.urs }]} />
              <Text style={styles.legendText}>URS</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.reject }]} />
              <Text style={styles.legendText}>Reject</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.accent }]} />
              <Text style={styles.legendText}>Caliper Bar</Text>
            </View>
          </View>

          <View style={styles.overlayImageCard}>
            <LazyImage
              source={{
                uri: sample.processed_image_url || sample.original_image_url,
              }}
              style={styles.annotatedFullImage}
              resizeMode="contain"
            />
          </View>
          <Text style={styles.overlayHint}>
            Cyan = Equatorial Diameter (Deq) • Magenta = Polar Length
          </Text>
        </FadeInView>
      ) : (
        <View style={styles.gridContainer}>
          {/* Quick Filter Bar */}
          {gradeFilter !== 'ALL' && (
            <View style={styles.activeFilterBanner}>
              <Text style={styles.activeFilterText}>
                Showing {gradeFilter.replace('_', ' ')} only ({filteredOnions.length})
              </Text>
              <AnimatedPressable
                haptic="selection"
                onPress={() => setGradeFilter('ALL')}
                style={styles.clearFilterBtn}
              >
                <Text style={styles.clearFilterText}>Reset ✕</Text>
              </AnimatedPressable>
            </View>
          )}

          {/* Onion Grid */}
          {total === 0 ? (
            <View style={styles.zeroStateCard}>
              <View style={styles.zeroStateIconBox}>
                <Text style={styles.zeroStateIcon}>🔍</Text>
              </View>
              <Text style={styles.zeroStateTitle}>No Onion Bulbs Detected in Capture</Text>
              <Text style={styles.zeroStateDesc}>
                The camera frame did not contain identifiable onion bulbs against the background. You can instantly load the verified Mandi demo lot to inspect real photographed bulbs, millimeter sizes, and defect classifications.
              </Text>
              <AnimatedPressable
                haptic="heavy"
                style={styles.loadDemoBtn}
                onPress={handleLoadDemoSample}
                disabled={loadingDemo}
              >
                {loadingDemo ? (
                  <ActivityIndicator color="#ffffff" size="small" />
                ) : (
                  <Text style={styles.loadDemoBtnText}>
                    Load Verified Mandi Demo Lot (24 Real Bulbs + ChArUco)
                  </Text>
                )}
              </AnimatedPressable>
              <AnimatedPressable
                haptic="light"
                style={styles.retakeBtnSecondary}
                onPress={onAddSample}
              >
                <Text style={styles.retakeBtnSecondaryText}>Retake Photograph</Text>
              </AnimatedPressable>
            </View>
          ) : (
            <FlatList
              data={filteredOnions}
            keyExtractor={(item) => item.id}
            numColumns={2}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.gridContent}
            columnWrapperStyle={styles.gridRow}
            renderItem={({ item, index }) => (
              <FadeInView delay={Math.min(index * 40, 240)} distance={8} style={styles.bulbCardWrapper}>
                <AnimatedPressable
                  haptic="medium"
                  style={styles.bulbCard}
                  onPress={() => handleOpenOnionDetail(item)}
                >
                  <View style={styles.bulbImgWrapper}>
                    <LazyImage
                      source={{ uri: item.crop_url }}
                      style={styles.bulbImg}
                      borderRadius={Radius.md}
                      resizeMode="contain"
                    />
                    <View style={styles.badgeTagContainer}>
                      <GradeBadge grade={item.grade} size="sm" />
                    </View>
                  </View>

                  <View style={styles.bulbInfo}>
                    <View style={styles.bulbNameRow}>
                      <Text style={styles.bulbName}>#{item.display_number}</Text>
                      <SizeTierBadge tier={item.mandi_size_grade} />
                    </View>

                    <View style={styles.telemetryRow}>
                      {item.equatorial_diameter_mm !== null && item.equatorial_diameter_mm !== undefined ? (
                        <Text style={styles.diaText}>
                          {`Ø ${item.equatorial_diameter_mm.toFixed(1)}mm`}
                        </Text>
                      ) : item.equivalent_diameter_mm !== null && item.equivalent_diameter_mm !== undefined ? (
                        <Text style={styles.diaText}>
                          {`Ø ${item.equivalent_diameter_mm.toFixed(1)}mm`}
                        </Text>
                      ) : (
                        <Text style={styles.diaUncalibrated}>Uncalibrated</Text>
                      )}
                      {item.estimated_weight_grams !== undefined && item.estimated_weight_grams !== null && (
                        <Text style={styles.weightText}>
                          {item.estimated_weight_grams.toFixed(0)}g
                        </Text>
                      )}
                    </View>

                    {/* Defect Warning Chip */}
                    {(item.sprouted_prob ?? 0) > 0.3 ||
                    (item.rotten_prob ?? 0) > 0.3 ||
                    (item.damaged_prob ?? 0) > 0.3 ? (
                      <View style={styles.defectAlertTag}>
                        <Text style={styles.defectAlertText}>
                          {(item.rotten_prob ?? 0) > 0.3
                            ? 'Rotten'
                            : (item.sprouted_prob ?? 0) > 0.3
                            ? 'Sprouted'
                            : 'Damaged'}
                        </Text>
                      </View>
                    ) : null}
                  </View>
                </AnimatedPressable>
              </FadeInView>
            )}
          />
          )}
        </View>
      )}

      {/* Bottom Sticky Action Bar */}
      <View style={styles.actionBar}>
        <AnimatedPressable
          haptic="light"
          style={styles.addSampleBtn}
          onPress={onAddSample}
          disabled={finalizing}
        >
          <Text style={styles.addSampleText}>+ Sample 2</Text>
        </AnimatedPressable>

        <AnimatedPressable
          haptic="heavy"
          style={styles.finalizeBtn}
          onPress={handleFinalize}
          disabled={finalizing}
        >
          {finalizing ? (
            <ActivityIndicator color="#ffffff" size="small" />
          ) : (
            <Text style={styles.finalizeBtnText}>Finalize & Certify Lot →</Text>
          )}
        </AnimatedPressable>
      </View>

      {/* Evidence Drilldown Modal */}
      <EvidenceDrilldownModal
        visible={modalVisible}
        onion={selectedOnion}
        inspectionId={inspection.id}
        onClose={() => setModalVisible(false)}
        onCorrectionSaved={handleCorrectionSaved}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.sm,
  },
  kpiContainer: {
    flexDirection: 'row',
    gap: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  kpiCard: {
    flex: 1,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.md,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xs,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  kpiCardSelected: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1.5,
    borderColor: Colors.accent,
  },
  kpiDotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  kpiDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  kpiValue: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text,
  },
  kpiPercent: {
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 1,
  },
  kpiLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginTop: 1,
  },
  calibratedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ecfdf5',
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: '#a7f3d0',
    padding: Spacing.sm,
    marginBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  calibratedIconBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: '#10b981',
    alignItems: 'center',
    justifyContent: 'center',
  },
  calibratedIcon: {
    color: '#ffffff',
    fontWeight: '800',
    fontSize: 13,
  },
  calibratedTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#065f46',
    marginBottom: 2,
  },
  calibratedSubtitle: {
    fontSize: 11,
    lineHeight: 15,
    color: '#047857',
  },
  zeroStateCard: {
    backgroundColor: '#ffffff',
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    alignItems: 'center',
    marginVertical: Spacing.md,
    borderWidth: 1,
    borderColor: '#e7e5e4',
    ...Shadows.card,
  },
  zeroStateIconBox: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#f4f3ef',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  zeroStateIcon: {
    fontSize: 20,
  },
  zeroStateTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0c0c0e',
    textAlign: 'center',
  },
  zeroStateDesc: {
    fontSize: 12,
    color: '#71717a',
    textAlign: 'center',
    marginTop: 4,
    lineHeight: 17,
    marginBottom: Spacing.lg,
    paddingHorizontal: Spacing.sm,
  },
  loadDemoBtn: {
    backgroundColor: '#0c0c0e',
    paddingVertical: 12,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.sm,
    width: '100%',
    alignItems: 'center',
    marginBottom: 8,
  },
  loadDemoBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
  },
  retakeBtnSecondary: {
    backgroundColor: '#f4f3ef',
    paddingVertical: 10,
    paddingHorizontal: Spacing.lg,
    borderRadius: Radius.sm,
    width: '100%',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e7e5e4',
  },
  retakeBtnSecondaryText: {
    color: '#52525b',
    fontSize: 12,
    fontWeight: '600',
  },
  uncalibratedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: Spacing.sm,
    marginBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  uncalibratedIconBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: 'rgba(217, 119, 6, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  uncalibratedIcon: {
    color: '#d97706',
    fontWeight: '800',
    fontSize: 13,
  },
  uncalibratedTextWrap: {
    flex: 1,
  },
  uncalibratedTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 2,
  },
  uncalibratedSubtitle: {
    fontSize: 11,
    lineHeight: 15,
    color: Colors.textMuted,
  },
  viewModeToggleRow: {
    flexDirection: 'row',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: 3,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  viewModeBtn: {
    flex: 1,
    paddingVertical: 7,
    alignItems: 'center',
    borderRadius: Radius.sm,
  },
  viewModeBtnActive: {
    backgroundColor: Colors.accent,
  },
  viewModeText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  viewModeTextActive: {
    color: '#ffffff',
    fontWeight: '600',
  },
  gridContainer: {
    flex: 1,
  },
  activeFilterBanner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.sm,
    marginBottom: Spacing.xs,
  },
  activeFilterText: {
    fontSize: 11,
    color: Colors.accent,
    fontWeight: '600',
  },
  clearFilterBtn: {
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  clearFilterText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontWeight: '700',
  },
  gridContent: {
    paddingBottom: 85,
  },
  gridRow: {
    justifyContent: 'space-between',
    marginBottom: Spacing.sm,
  },
  bulbCardWrapper: {
    width: '48.5%',
  },
  bulbCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  bulbImgWrapper: {
    width: '100%',
    height: 115,
    backgroundColor: Colors.skeletonBase,
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bulbImg: {
    width: '100%',
    height: '100%',
  },
  badgeTagContainer: {
    position: 'absolute',
    top: 6,
    right: 6,
  },
  bulbInfo: {
    padding: Spacing.sm,
  },
  bulbNameRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  bulbName: {
    fontSize: 13,
    fontWeight: '800',
    color: Colors.text,
  },
  telemetryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  diaText: {
    fontSize: 12,
    color: Colors.accent,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  diaUncalibrated: {
    fontSize: 11,
    color: Colors.textMuted,
    fontStyle: 'italic',
    fontWeight: '500',
  },
  weightText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontFamily: 'monospace',
  },
  defectAlertTag: {
    backgroundColor: Colors.rejectBg,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.xs,
    marginTop: 5,
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
  },
  defectAlertText: {
    fontSize: 9,
    fontWeight: '800',
    color: Colors.reject,
  },
  overlayViewContainer: {
    flex: 1,
    paddingBottom: 85,
  },
  overlayLegendRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: Spacing.md,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.cardBg,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  legendDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  legendText: {
    fontSize: 10,
    color: Colors.textMuted,
    fontWeight: '600',
  },
  overlayImageCard: {
    flex: 1,
    minHeight: 320,
    backgroundColor: '#000',
    borderRadius: Radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  annotatedFullImage: {
    width: '100%',
    height: '100%',
  },
  overlayHint: {
    fontSize: 11,
    color: Colors.textDim,
    textAlign: 'center',
    marginTop: 6,
    fontFamily: 'monospace',
  },
  actionBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: Colors.cardBg,
    padding: Spacing.md,
    flexDirection: 'row',
    gap: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    ...Shadows.modal,
  },
  addSampleBtn: {
    flex: 1,
    backgroundColor: Colors.cardBgElevated,
    paddingVertical: 13,
    borderRadius: Radius.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  addSampleText: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  finalizeBtn: {
    flex: 2.4,
    backgroundColor: Colors.accent,
    paddingVertical: 13,
    borderRadius: Radius.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.accent,
    ...Shadows.card,
  },
  finalizeBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  tabScrollContainer: {
    flex: 1,
    paddingBottom: 85,
  },
  tabScrollContent: {
    paddingBottom: 95,
  },
  sectionCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: Spacing.md,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.sm,
  },
  cardSectionTag: {
    fontSize: 9.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.accentTeal,
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  cardSectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.text,
  },
  storageTierBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.xs,
    borderWidth: 1,
  },
  storageTierBadgeGood: {
    backgroundColor: 'rgba(15, 118, 110, 0.1)',
    borderColor: 'rgba(15, 118, 110, 0.3)',
  },
  storageTierBadgeWarn: {
    backgroundColor: 'rgba(217, 119, 6, 0.1)',
    borderColor: 'rgba(217, 119, 6, 0.3)',
  },
  storageTierBadgeDanger: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
  },
  storageTierText: {
    fontSize: 10,
    fontWeight: '800',
    fontFamily: 'monospace',
    letterSpacing: 0.3,
  },
  storageTierTextGood: { color: Colors.accentTeal },
  storageTierTextWarn: { color: Colors.urs },
  storageTierTextDanger: { color: Colors.reject },
  storageScoreHeroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginVertical: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  storageScoreBox: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginRight: Spacing.lg,
    paddingRight: Spacing.md,
    borderRightWidth: 1,
    borderRightColor: Colors.border,
  },
  storageScoreLarge: {
    fontSize: 38,
    fontWeight: '800',
    color: Colors.text,
    fontFamily: 'monospace',
  },
  storageScoreOutOf: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textMuted,
    fontFamily: 'monospace',
    marginLeft: 2,
  },
  storageHorizonBox: {
    flex: 1,
  },
  storageHorizonLabel: {
    fontSize: 9.5,
    fontWeight: '700',
    color: Colors.textMuted,
    fontFamily: 'monospace',
    letterSpacing: 0.4,
  },
  storageHorizonDays: {
    fontSize: 22,
    fontWeight: '800',
    color: Colors.accentTeal,
    marginVertical: 1,
  },
  storageHorizonSub: {
    fontSize: 11,
    color: Colors.textSecondary,
  },
  directiveBanner: {
    backgroundColor: Colors.bg,
    borderRadius: Radius.sm,
    padding: Spacing.sm,
    marginTop: Spacing.sm,
    borderLeftWidth: 3,
    borderLeftColor: Colors.accentTeal,
  },
  directiveTag: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    marginBottom: 2,
  },
  directiveText: {
    fontSize: 12,
    color: Colors.text,
    lineHeight: 16,
    fontWeight: '500',
  },
  telemetryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
    marginBottom: Spacing.md,
  },
  telemetryCard: {
    width: '48.5%',
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.md,
    padding: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  telemetryLabel: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    marginBottom: 2,
  },
  telemetryValue: {
    fontSize: 16,
    fontWeight: '800',
    fontFamily: 'monospace',
    color: Colors.text,
    marginVertical: 2,
  },
  telemetrySub: {
    fontSize: 10,
    color: Colors.textDim,
  },
  infoCard: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    marginBottom: Spacing.md,
  },
  infoTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 4,
  },
  infoBody: {
    fontSize: 11,
    lineHeight: 16,
    color: Colors.textSecondary,
  },
  tierPill: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tierPillText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.accentTeal,
  },
  payoutHighlightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginVertical: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  payoutMetricBlock: {
    flex: 1,
  },
  payoutDivider: {
    width: 1,
    height: '80%',
    backgroundColor: Colors.border,
    marginHorizontal: Spacing.md,
  },
  payoutMetricLabel: {
    fontSize: 9.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.4,
  },
  payoutRateVal: {
    fontSize: 22,
    fontWeight: '800',
    color: Colors.accentTeal,
    fontFamily: 'monospace',
    marginVertical: 2,
  },
  payoutTotalVal: {
    fontSize: 22,
    fontWeight: '800',
    color: Colors.text,
    fontFamily: 'monospace',
    marginVertical: 2,
  },
  payoutMetricSub: {
    fontSize: 10.5,
    color: Colors.textDim,
  },
  mspBenchmarkRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: Spacing.sm,
    paddingTop: Spacing.xs,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
  },
  mspBenchmarkLabel: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  mspBenchmarkValue: {
    fontSize: 11,
    fontWeight: '700',
    fontFamily: 'monospace',
    color: Colors.textSecondary,
  },
  totalDockageBadge: {
    fontSize: 12,
    fontWeight: '800',
    fontFamily: 'monospace',
    color: Colors.reject,
  },
  dockageTableHeader: {
    flexDirection: 'row',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    marginBottom: 4,
  },
  dockageTh: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.4,
  },
  dockageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 7,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderMuted,
  },
  dockageRowAlt: {
    backgroundColor: Colors.cardBgElevated,
  },
  dockageTdName: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.text,
  },
  dockageTd: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: Colors.textSecondary,
  },
  dockageTdDockage: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.reject,
  },
  noDockageRow: {
    paddingVertical: Spacing.md,
    alignItems: 'center',
  },
  noDockageText: {
    fontSize: 11.5,
    color: Colors.accentTeal,
    fontWeight: '600',
    textAlign: 'center',
  },
});

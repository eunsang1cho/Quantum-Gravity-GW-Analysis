#!/usr/bin/env python3
"""
# Title:  Narrow-Band Quantum Gravitational Resonance in Black Hole Ringdown at M ~ 60 M☉
# Author: Eunsang Cho
# Date: 2026-02-01
# Description: Analyzing LIGO data to detect mass-dependent ringdown anomalies.

Figure 1: Mass vs Quantum Effect
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# matplotlib 기본 설정 (gwpy 충돌 방지)
matplotlib.use('Agg')  # 백엔드 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11
plt.rcParams['figure.dpi'] = 300

print("="*60)
print("논문용 그림 생성 중...")
print("="*60)

# ============================================================================
# 데이터 (실제 분석 결과)
# ============================================================================

events_data = {
    'GW150914': {'mass': 62, 'f_obs': 259.22, 'f_err': 1.52, 'f_gr': 250.0, 'f_q': 257.5, 'winner': 'Q'},
    'GW190517': {'mass': 61, 'f_obs': 320.90, 'f_err': 12.67, 'f_gr': 254.1, 'f_q': 261.7, 'winner': 'Q'},
    'GW170818': {'mass': 59, 'f_obs': 288.00, 'f_err': 1.26, 'f_gr': 262.7, 'f_q': 270.6, 'winner': 'Q'},
    'GW190719': {'mass': 54, 'f_obs': 324.11, 'f_err': 1.82, 'f_gr': 287.0, 'f_q': 295.7, 'winner': 'Q'},
    'GW190412': {'mass': 53, 'f_obs': 293.34, 'f_err': 2.40, 'f_gr': 292.5, 'f_q': 301.2, 'winner': 'GR'},
    'GW170608': {'mass': 54, 'f_obs': 275.51, 'f_err': 1.72, 'f_gr': 287.0, 'f_q': 295.7, 'winner': 'GR'},
    'GW190701': {'mass': 66, 'f_obs': 192.78, 'f_err': 2.67, 'f_gr': 234.8, 'f_q': 241.9, 'winner': 'GR'},
    'GW190620': {'mass': 67, 'f_obs': 233.69, 'f_err': 1.57, 'f_gr': 231.3, 'f_q': 238.3, 'winner': 'GR'},
}

# 시그마 계산
for name, data in events_data.items():
    diff_gr = data['f_obs'] - data['f_gr']
    diff_q = data['f_obs'] - data['f_q']
    data['sigma_gr'] = abs(diff_gr) / data['f_err']
    data['sigma_q'] = abs(diff_q) / data['f_err']

# ============================================================================
# Figure 1: Main Discovery Figure
# ============================================================================

print("\nFigure 1 생성 중...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# ===== 왼쪽: Mass vs Sigma (GR deviation) =====

# 데이터 추출
masses = [d['mass'] for d in events_data.values()]
sigmas_gr = [d['sigma_gr'] for d in events_data.values()]
colors = ['green' if d['winner'] == 'Q' else 'orange' for d in events_data.values()]
event_names = list(events_data.keys())

# 공명 범위 표시 (58-64 M☉)
ax1.axvspan(58, 64, alpha=0.15, color='green', label='Resonance band (59-62 M$_\\odot$)', zorder=1)

# 발견 기준선
ax1.axhline(5, color='red', linestyle='--', linewidth=2, alpha=0.7, label='5$\\sigma$ (discovery)', zorder=2)
ax1.axhline(3, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='3$\\sigma$ (evidence)', zorder=2)

# 데이터 점 그리기
for i, (mass, sigma, color, name) in enumerate(zip(masses, sigmas_gr, colors, event_names)):
    # 특별 표시
    if name == 'GW150914':
        marker = '*'
        size = 400
        ax1.scatter([mass], [sigma], c=[color], marker=marker, s=size, 
                   edgecolors='black', linewidth=2, zorder=4, label='GW150914 (reference)')
        # 라벨
        ax1.annotate('GW150914★', (mass, sigma), 
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='darkgreen')
    else:
        marker = 'o'
        size = 200
        ax1.scatter([mass], [sigma], c=[color], marker=marker, s=size, 
                   edgecolors='black', linewidth=1.5, alpha=0.8, zorder=3)
        
        # 공명 구간 내 이벤트만 라벨
        if 59 <= mass <= 62 and name != 'GW150914':
            ax1.annotate(name, (mass, sigma), 
                        xytext=(5, -10), textcoords='offset points',
                        fontsize=8, alpha=0.7)

ax1.set_xlabel('Final Black Hole Mass (M$_\\odot$)', fontsize=13, fontweight='bold')
ax1.set_ylabel('Deviation from GR ($\\sigma$)', fontsize=13, fontweight='bold')
ax1.set_title('(a) Mass-Selective Quantum Effect', fontsize=14, fontweight='bold')

# ⚠️ 중요: y축 범위를 명시적으로 설정 (log 스케일 오류 방지)
ax1.set_ylim(0.3, 30)
ax1.set_xlim(50, 70)
ax1.set_yscale('log')

ax1.legend(fontsize=9, loc='upper right')
ax1.grid(True, alpha=0.3, which='both', linestyle=':', linewidth=0.5)

# ===== 오른쪽: Frequency Comparison =====

# 질량 순 정렬
sorted_events = sorted(events_data.items(), key=lambda x: x[1]['mass'])
event_names_sorted = [name for name, _ in sorted_events]
x_pos = np.arange(len(event_names_sorted))

# 데이터
f_gr = [d['f_gr'] for _, d in sorted_events]
f_q = [d['f_q'] for _, d in sorted_events]
f_obs = [d['f_obs'] for _, d in sorted_events]
f_err = [d['f_err'] for _, d in sorted_events]
masses_sorted = [d['mass'] for _, d in sorted_events]

width = 0.25

# 막대 그래프
bar1 = ax2.bar(x_pos - width, f_gr, width, label='GR prediction', 
              color='orange', alpha=0.7, edgecolor='black', linewidth=1)
bar2 = ax2.bar(x_pos, f_q, width, label='Quantum (+3%)', 
              color='purple', alpha=0.7, edgecolor='black', linewidth=1)
bar3 = ax2.bar(x_pos + width, f_obs, width, label='Observed', 
              color='red', alpha=0.8, edgecolor='black', linewidth=1.5,
              yerr=f_err, capsize=4, error_kw={'linewidth': 1.5, 'ecolor': 'darkred'})

# 공명 구간 강조 (배경)
for i, (name, data) in enumerate(sorted_events):
    if 59 <= data['mass'] <= 62:
        ax2.axvspan(i - 0.5, i + 0.5, alpha=0.1, color='green', zorder=0)

# X축 라벨
labels = [f"{name}\n({mass:.0f} M$_\\odot$)" for name, mass in zip(event_names_sorted, masses_sorted)]
ax2.set_xticks(x_pos)
ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)

ax2.set_ylabel('Ringdown Frequency (Hz)', fontsize=13, fontweight='bold')
ax2.set_title('(b) Frequency Predictions vs Observations', fontsize=14, fontweight='bold')
ax2.legend(fontsize=10, loc='upper left')
ax2.grid(True, alpha=0.3, axis='y', linestyle=':', linewidth=0.5)

# 주석
ax2.text(0.02, 0.98, 'Green shading: Resonance band', 
        transform=ax2.transAxes, fontsize=9, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='green', alpha=0.15))

plt.tight_layout()

# 저장
try:
    plt.savefig('figure1_main.png', dpi=300, bbox_inches='tight')
    print("✓ PNG 저장 완료: figure1_main.png")
except Exception as e:
    print(f"PNG 저장 실패: {e}")

try:
    plt.savefig('figure1_main.pdf', dpi=300, bbox_inches='tight')
    print("✓ PDF 저장 완료: figure1_main.pdf")
except Exception as e:
    print(f"PDF 저장 실패: {e}")

plt.close()

# ============================================================================
# Figure 2: Resonance Band Detail (공명 구간 상세)
# ============================================================================

print("\nFigure 2 생성 중...")

# 공명 구간 3개 이벤트
resonance_events = {
    'GW170818': events_data['GW170818'],
    'GW190517': events_data['GW190517'],
    'GW150914': events_data['GW150914'],
}

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# (a) 편차 크기 비교
events_r = list(resonance_events.keys())
x = np.arange(len(events_r))

diff_gr = [abs(resonance_events[e]['f_obs'] - resonance_events[e]['f_gr']) for e in events_r]
diff_q = [abs(resonance_events[e]['f_obs'] - resonance_events[e]['f_q']) for e in events_r]

width = 0.35
ax1.bar(x - width/2, diff_gr, width, label='GR deviation', color='orange', alpha=0.7, edgecolor='black')
ax1.bar(x + width/2, diff_q, width, label='Quantum deviation', color='purple', alpha=0.7, edgecolor='black')

ax1.set_xticks(x)
ax1.set_xticklabels([f"{e}\n({resonance_events[e]['mass']} M$_\\odot$)" for e in events_r], fontsize=9)
ax1.set_ylabel('Absolute Deviation (Hz)', fontsize=12, fontweight='bold')
ax1.set_title('(a) Deviation Magnitude', fontsize=13, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3, axis='y')

# (b) 시그마 비교
sigma_gr = [resonance_events[e]['sigma_gr'] for e in events_r]
sigma_q = [resonance_events[e]['sigma_q'] for e in events_r]

ax2.bar(x - width/2, sigma_gr, width, label='$\\sigma$(GR)', color='orange', alpha=0.7, edgecolor='black')
ax2.bar(x + width/2, sigma_q, width, label='$\\sigma$(Quantum)', color='purple', alpha=0.7, edgecolor='black')

ax2.axhline(5, color='red', linestyle='--', linewidth=2, alpha=0.7, label='5$\\sigma$ threshold')
ax2.axhline(3, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='3$\\sigma$ threshold')

ax2.set_xticks(x)
ax2.set_xticklabels(events_r, fontsize=9)
ax2.set_ylabel('Statistical Significance ($\\sigma$)', fontsize=12, fontweight='bold')
ax2.set_title('(b) Significance Comparison', fontsize=13, fontweight='bold')

# ⚠️ y축 범위 명시 (log 오류 방지)
ax2.set_ylim(0.5, 30)
ax2.set_yscale('log')

ax2.legend(fontsize=9, loc='upper right')
ax2.grid(True, alpha=0.3, which='both')

# (c) 주파수 정확도
for i, event in enumerate(events_r):
    data = resonance_events[event]
    
    # 선으로 연결
    ax3.plot([i, i], [data['f_gr'], data['f_obs']], 
            'o-', color='orange', linewidth=3, markersize=8, alpha=0.7, 
            label='GR' if i == 0 else '')
    ax3.plot([i, i], [data['f_q'], data['f_obs']], 
            's-', color='purple', linewidth=3, markersize=8, alpha=0.7, 
            label='Quantum' if i == 0 else '')
    
    # 관측값
    ax3.errorbar([i], [data['f_obs']], yerr=[data['f_err']], 
                fmt='*', color='red', markersize=15, linewidth=2, capsize=5,
                label='Observed' if i == 0 else '')

ax3.set_xticks(range(len(events_r)))
ax3.set_xticklabels(events_r, fontsize=9)
ax3.set_ylabel('Frequency (Hz)', fontsize=12, fontweight='bold')
ax3.set_title('(c) Prediction Accuracy', fontsize=13, fontweight='bold')
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)

# (d) 통계 요약
ax4.axis('off')

summary_text = f"""
══════════════════════════════════════
   RESONANCE BAND (59-62 M☉)
══════════════════════════════════════

Events:              3
Quantum wins:        3/3 (100%)
GR wins:             0/3 (0%)

Avg GR deviation:    10.5σ
Avg Quantum dev:     6.5σ

Improvement:         1.6×

══════════════════════════════════════
           INDIVIDUAL RESULTS
══════════════════════════════════════

GW170818 (59 M☉):
  Obs:  288.0 ± 1.3 Hz
  GR:   262.7 Hz → 20.1σ
  Q:    270.6 Hz → 13.8σ
  Winner: Quantum (1.5× better)

GW190517 (61 M☉):
  Obs:  320.9 ± 12.7 Hz
  GR:   254.1 Hz → 5.3σ
  Q:    261.7 Hz → 4.7σ
  Winner: Quantum (1.1× better)

GW150914★ (62 M☉):
  Obs:  259.2 ± 1.5 Hz
  GR:   250.0 Hz → 6.1σ
  Q:    257.5 Hz → 1.1σ
  Winner: Quantum (5.5× better)

══════════════════════════════════════
"""

ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
        fontsize=9, verticalalignment='top', family='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()

try:
    plt.savefig('figure2_resonance_detail.png', dpi=300, bbox_inches='tight')
    print("✓ PNG 저장 완료: figure2_resonance_detail.png")
except Exception as e:
    print(f"PNG 저장 실패: {e}")

try:
    plt.savefig('figure2_resonance_detail.pdf', dpi=300, bbox_inches='tight')
    print("✓ PDF 저장 완료: figure2_resonance_detail.pdf")
except Exception as e:
    print(f"PDF 저장 실패: {e}")

plt.close()

# ============================================================================
# 완료
# ============================================================================

print("\n" + "="*60)
print("✅ 모든 그림 생성 완료!")
print("="*60)
print("\n생성된 파일:")
print("  • figure1_main.png/pdf          (메인 발견)")
print("  • figure2_resonance_detail.png/pdf  (공명 구간 상세)")
print("\n논문에 포함:")
print("  → Figure 1: 필수 (핵심 결과)")
print("  → Figure 2: 권장 (상세 분석)")
print("="*60)

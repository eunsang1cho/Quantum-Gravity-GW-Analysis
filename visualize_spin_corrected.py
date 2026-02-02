#!/usr/bin/env python3
"""
Visualize Spin-Corrected Results

Usage:
    python visualize_spin_corrected.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

plt.rcParams['font.size'] = 11
plt.rcParams['figure.dpi'] = 300

# ============================================================================
# Load Data
# ============================================================================

def load_results():
    """Load spin-corrected results"""
    
    filename = 'data/spin_corrected_results.csv'
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        print(f"   Run: python spin_corrected_analysis.py first")
        return None
    
    df = pd.read_csv(filename)
    print(f"✓ Loaded {len(df)} events")
    
    return df

# ============================================================================
# Comparison Plot
# ============================================================================

def plot_before_after_correction(df, save=True):
    """
    Compare results before and after spin correction
    """
    
    with_spin = df[df['spin_available'] == True]
    
    if len(with_spin) == 0:
        print("No spin data available")
        return
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    masses = with_spin['mass'].values
    delta_raw = with_spin['delta_raw'].values
    quantum_residual = with_spin['quantum_residual'].values
    
    # Colors
    colors = ['green' if 59 <= m <= 62 else 'gray' for m in masses]
    
    # (a) BEFORE correction
    ax1.axvspan(59, 62, alpha=0.2, color='green', label='Resonance')
    ax1.scatter(masses, delta_raw, c=colors, s=100, alpha=0.7, 
               edgecolors='black', linewidth=1)
    ax1.axhline(0, color='red', linestyle='--', linewidth=2, label='GR')
    ax1.axhline(3, color='blue', linestyle=':', linewidth=2, alpha=0.7, label='+3%')
    ax1.set_xlabel('Mass (M☉)', fontweight='bold')
    ax1.set_ylabel('Raw Deviation (%)', fontweight='bold')
    ax1.set_title('(a) BEFORE Spin Correction', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-30, 50)
    
    # (b) AFTER correction
    ax2.axvspan(59, 62, alpha=0.2, color='green', label='Resonance')
    ax2.scatter(masses, quantum_residual, c=colors, s=100, alpha=0.7,
               edgecolors='black', linewidth=1)
    ax2.axhline(0, color='red', linestyle='--', linewidth=2, label='No quantum')
    ax2.axhline(3, color='blue', linestyle=':', linewidth=2, alpha=0.7, label='+3%')
    ax2.set_xlabel('Mass (M☉)', fontweight='bold')
    ax2.set_ylabel('Quantum Residual (%)', fontweight='bold')
    ax2.set_title('(b) AFTER Spin Correction', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(-30, 50)
    
    # (c) Distribution BEFORE
    resonance_before = with_spin[(with_spin['mass'] >= 59) & (with_spin['mass'] <= 62)]['delta_raw']
    outside_before = with_spin[(with_spin['mass'] < 59) | (with_spin['mass'] > 62)]['delta_raw']
    
    ax3.hist(outside_before, bins=15, alpha=0.5, color='gray', 
            label=f'Outside (n={len(outside_before)})', edgecolor='black')
    ax3.hist(resonance_before, bins=8, alpha=0.7, color='green',
            label=f'Resonance (n={len(resonance_before)})', edgecolor='black')
    ax3.axvline(0, color='red', linestyle='--', linewidth=2)
    ax3.axvline(3, color='blue', linestyle=':', linewidth=2)
    ax3.set_xlabel('Raw Deviation (%)', fontweight='bold')
    ax3.set_ylabel('Count', fontweight='bold')
    ax3.set_title('(c) Distribution BEFORE', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # (d) Distribution AFTER
    resonance_after = with_spin[(with_spin['mass'] >= 59) & (with_spin['mass'] <= 62)]['quantum_residual']
    outside_after = with_spin[(with_spin['mass'] < 59) | (with_spin['mass'] > 62)]['quantum_residual']
    
    ax4.hist(outside_after, bins=15, alpha=0.5, color='gray',
            label=f'Outside (n={len(outside_after)})', edgecolor='black')
    ax4.hist(resonance_after, bins=8, alpha=0.7, color='green',
            label=f'Resonance (n={len(resonance_after)})', edgecolor='black')
    ax4.axvline(0, color='red', linestyle='--', linewidth=2)
    ax4.axvline(3, color='blue', linestyle=':', linewidth=2)
    ax4.set_xlabel('Quantum Residual (%)', fontweight='bold')
    ax4.set_ylabel('Count', fontweight='bold')
    ax4.set_title('(d) Distribution AFTER', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if save:
        os.makedirs('figures', exist_ok=True)
        plt.savefig('figures/spin_correction_comparison.png', dpi=300, bbox_inches='tight')
        print("✓ Saved: figures/spin_correction_comparison.png")
    
    plt.show()

def plot_spin_effects(df, save=True):
    """
    Visualize spin parameters and their effects
    """
    
    with_spin = df[df['spin_available'] == True]
    
    if len(with_spin) == 0:
        return
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    masses = with_spin['mass'].values
    spins = with_spin['a_effective'].values
    kerr_factors = with_spin['kerr_factor'].values
    delta_raw = with_spin['delta_raw'].values
    quantum = with_spin['quantum_residual'].values
    
    colors = ['green' if 59 <= m <= 62 else 'gray' for m in masses]
    
    # (a) Spin distribution
    ax1.scatter(masses, spins, c=colors, s=100, alpha=0.7, edgecolors='black')
    ax1.axvspan(59, 62, alpha=0.2, color='green')
    ax1.axhline(0, color='black', linestyle='-', alpha=0.3)
    ax1.set_xlabel('Mass (M☉)', fontweight='bold')
    ax1.set_ylabel('Effective Spin (a_eff)', fontweight='bold')
    ax1.set_title('(a) Spin vs Mass', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-1, 1)
    
    # (b) Kerr correction factor
    ax2.scatter(masses, kerr_factors, c=colors, s=100, alpha=0.7, edgecolors='black')
    ax2.axvspan(59, 62, alpha=0.2, color='green')
    ax2.axhline(1.0, color='red', linestyle='--', label='No correction')
    ax2.set_xlabel('Mass (M☉)', fontweight='bold')
    ax2.set_ylabel('Kerr Factor (f_Kerr/f_Schw)', fontweight='bold')
    ax2.set_title('(b) Kerr Correction Factor', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # (c) Spin vs raw deviation
    ax3.scatter(spins, delta_raw, c=colors, s=100, alpha=0.7, edgecolors='black')
    ax3.axhline(0, color='red', linestyle='--')
    ax3.axvline(0, color='black', linestyle='-', alpha=0.3)
    ax3.set_xlabel('Effective Spin (a_eff)', fontweight='bold')
    ax3.set_ylabel('Raw Deviation (%)', fontweight='bold')
    ax3.set_title('(c) Spin vs Raw Deviation', fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # (d) Spin vs quantum residual
    ax4.scatter(spins, quantum, c=colors, s=100, alpha=0.7, edgecolors='black')
    ax4.axhline(0, color='red', linestyle='--', label='No quantum')
    ax4.axhline(3, color='blue', linestyle=':', alpha=0.7, label='+3%')
    ax4.axvline(0, color='black', linestyle='-', alpha=0.3)
    ax4.set_xlabel('Effective Spin (a_eff)', fontweight='bold')
    ax4.set_ylabel('Quantum Residual (%)', fontweight='bold')
    ax4.set_title('(d) Spin vs Quantum Residual', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save:
        plt.savefig('figures/spin_effects.png', dpi=300, bbox_inches='tight')
        print("✓ Saved: figures/spin_effects.png")
    
    plt.show()

# ============================================================================
# Statistical Comparison
# ============================================================================

def compare_statistics(df):
    """Compare statistics before and after correction"""
    
    with_spin = df[df['spin_available'] == True]
    resonance = with_spin[(with_spin['mass'] >= 59) & (with_spin['mass'] <= 62)]
    outside = with_spin[(with_spin['mass'] < 59) | (with_spin['mass'] > 62)]
    
    print("\n" + "="*70)
    print("📊 BEFORE vs AFTER COMPARISON")
    print("="*70)
    
    if len(resonance) == 0:
        print("\nNo events in resonance band")
        return
    
    print(f"\n🎯 RESONANCE BAND (59-62 M☉): {len(resonance)} events")
    
    print(f"\nBEFORE spin correction:")
    print(f"  Raw deviation: {resonance['delta_raw'].mean():.2f}% ± {resonance['delta_raw'].std():.2f}%")
    print(f"  Spread: {resonance['delta_raw'].std():.2f}%")
    
    print(f"\nAFTER spin correction:")
    print(f"  Quantum residual: {resonance['quantum_residual'].mean():.2f}% ± {resonance['quantum_residual'].std():.2f}%")
    print(f"  Spread: {resonance['quantum_residual'].std():.2f}%")
    
    # Improvement
    improvement = (1 - resonance['quantum_residual'].std() / resonance['delta_raw'].std()) * 100
    print(f"\n  → Spread reduction: {improvement:.0f}%")
    
    # Test for +3%
    from scipy import stats as sp_stats
    
    t_stat, p_value = sp_stats.ttest_1samp(resonance['quantum_residual'], 3.0)
    print(f"\n  t-test (H0: mean = +3%):")
    print(f"    p-value: {p_value:.4f}")
    
    if p_value > 0.05:
        print(f"    ✓ Consistent with +3%")
    else:
        print(f"    ✗ Not consistent with +3%")

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    df = load_results()
    
    if df is not None:
        print("\n📊 Creating visualizations...")
        plot_before_after_correction(df)
        plot_spin_effects(df)
        compare_statistics(df)
        
        print("\n✅ Done!")

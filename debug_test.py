#!/usr/bin/env python3
"""
Debug script to test what's going wrong with the analysis
"""

import numpy as np

# Load one of the processed files
print("Loading GW150914 data...")
data = np.load('GW150914_H1_processed.npz', allow_pickle=True)

print("\nData contents:")
print(f"  Strain length: {len(data['strain'])}")
print(f"  Sample rate: {data['sample_rate']}")
print(f"  Merger index: {data['merger_idx']}")
print(f"  Final mass: {data['final_mass']} M_sun")
print(f"  Final spin: {data['final_spin']}")

print("\n" + "="*60)
print("Key parameters:")

strain = data['strain']
sample_rate = float(data['sample_rate'])
merger_idx = int(data['merger_idx'])

print(f"  Strain length: {len(strain)}")
print(f"  Merger index: {merger_idx}")
print(f"  Samples after merger: {len(strain) - merger_idx}")
print(f"  Time after merger: {(len(strain) - merger_idx) / sample_rate * 1000:.1f}ms")

# Test the time segment extraction
print("\n" + "="*60)
print("Testing time segment extraction (what the code does):")

# Try to extract 0-2ms after merger
t_start = 0.0
t_end = 0.002  # 2ms

print(f"\nRequested window: {t_start}s to {t_end}s after merger")
print(f"Required samples: {int(t_end * sample_rate)}")

# This is what the current code does
print(f"\nMerger index value: {merger_idx}")
print(f"Is merger_idx < len(strain)? {merger_idx < len(strain)}")

if merger_idx < len(strain):  # merger_idx is an index
    idx_start = int(merger_idx + t_start * sample_rate)
    idx_end = int(merger_idx + t_end * sample_rate)
    print("→ Treating as index")
else:  # merger_idx is GPS time
    idx_start = int((merger_idx + t_start) * sample_rate)
    idx_end = int((merger_idx + t_end) * sample_rate)  
    print("→ Treating as GPS time")

print(f"\nCalculated indices:")
print(f"  idx_start (raw): {idx_start}")
print(f"  idx_end (raw): {idx_end}")

# Ensure valid
idx_start_clipped = max(0, idx_start)
idx_end_clipped = min(len(strain), idx_end)

print(f"  idx_start (clipped): {idx_start_clipped}")
print(f"  idx_end (clipped): {idx_end_clipped}")

segment = strain[idx_start_clipped:idx_end_clipped]
print(f"\nResulting segment length: {len(segment)}")

if len(segment) == 0:
    print("\n❌ PROBLEM: Empty segment!")
elif len(segment) < 10:
    print(f"\n⚠️  WARNING: Very short segment ({len(segment)} samples)")
else:
    print(f"\n✓ Segment OK: {len(segment)} samples = {len(segment)/sample_rate*1000:.2f}ms")
    
print("\n" + "="*60)
print("Analysis:")
if idx_end > len(strain):
    print(f"❌ Problem: idx_end ({idx_end}) exceeds array length ({len(strain)})")
    print(f"   We need: {idx_end - len(strain)} more samples")
    print(f"   That's: {(idx_end - len(strain))/sample_rate*1000:.1f}ms more data")
elif len(segment) == 0:
    print(f"❌ Segment is empty even though indices are valid")
    print(f"   This shouldn't happen!")
else:
    print(f"✓ Everything looks OK")
    print(f"\nTesting bandpass filter on this segment...")
    from scipy import signal as sp_signal
    
    freq_band = (200, 300)  # Expected freq ±30%
    try:
        sos = sp_signal.butter(8, freq_band, btype='bandpass', fs=sample_rate, output='sos')
        filtered = sp_signal.sosfilt(sos, segment)
        print(f"✓ Filter works: output length = {len(filtered)}")
        
        # Hilbert transform
        analytic = sp_signal.hilbert(filtered)
        amplitude = np.abs(analytic)
        phase = np.unwrap(np.angle(analytic))
        inst_freq = np.diff(phase) * sample_rate / (2 * np.pi)
        
        print(f"✓ Hilbert transform works: inst_freq length = {len(inst_freq)}")
        print(f"  Mean frequency: {np.mean(inst_freq):.1f} Hz")
        print(f"  Std frequency: {np.std(inst_freq):.1f} Hz")
        
    except Exception as e:
        print(f"❌ Error in processing: {e}")


# Methodology

Complete description of analysis methods, corrections, and statistical tests.

---

## 1. Data Acquisition

### 1.1 Source
- **Provider**: LIGO Open Science Center (GWOSC)
- **Data**: Strain time series from H1 (Hanford) detector
- **Events**: 44 binary black hole mergers from GWTC-3 catalog
- **Time window**: ±16 seconds around merger GPS time

### 1.2 Event Selection Criteria
```python
- Confident detection (FAR < 1/year)
- Final mass: 18-142 M☉
- Data quality: No instrumental glitches
- O1, O2, O3a, O3b observing runs
```

---

## 2. Signal Processing

### 2.1 Ringdown Extraction

**Time window**: t ∈ [t_merger + 3ms, t_merger + 40ms]
- Avoids inspiral/merger phases
- Captures fundamental quasi-normal mode (QNM)

### 2.2 Whitening
```python
from gwpy.timeseries import TimeSeries

data = TimeSeries.fetch_open_data('H1', gps-16, gps+16)
whitened = data.whiten(fftlength=4, overlap=2)
```

**Purpose**: Flatten noise spectrum for optimal SNR

### 2.3 Bandpass Filtering

```python
f_center = 250 Hz × (62 M☉ / M_final)  # GR prediction
f_min = 0.7 × f_center
f_max = 1.5 × f_center

filtered = whitened.bandpass(f_min, f_max)
```

**Adaptive**: Filter range scales with black hole mass

---

## 3. Frequency Measurement

### 3.1 Model

Exponentially-damped sinusoid:
```
h(t) = A × exp(-(t-t₀)/τ) × cos(2πf(t-t₀) + φ)
```

Parameters:
- A: Amplitude
- τ: Damping time
- f: **Ringdown frequency** (measurement target)
- φ: Phase

### 3.2 Fitting Procedure

```python
from scipy.optimize import curve_fit

# Initial guess
p0 = [amplitude=1.0, tau=0.01s, f=f_center, phi=0]

# Bounds
bounds = ([0, 0.001, f_min, -π], [∞, 0.1, f_max, π])

# Levenberg-Marquardt fit
popt, pcov = curve_fit(model, times, strain, p0=p0, bounds=bounds)

f_obs = popt[2]
f_error = sqrt(diag(pcov)[2])
```

### 3.3 Uncertainty Estimation

**Covariance matrix diagonal** provides 1σ uncertainties
- Typical f_error: 1-10 Hz (0.5-2% of frequency)
- Depends on SNR and fitting window

---

## 4. General Relativity Predictions

### 4.1 Schwarzschild (Non-rotating)

For l=2, m=2, n=0 quasi-normal mode:

```
f_GR = (c³/2πGM) × Ω₂₂₀

where Ω₂₂₀ = 0.37367 (dimensionless)
```

**Scaling**: f ∝ 1/M

Example: M = 62 M☉ → f_GR = 250 Hz

### 4.2 Kerr (Rotating) Correction

Spin affects frequency via frame-dragging:

```python
# Effective spin (line-of-sight projection)
a_eff = a_final × cos(θ_inclination)

# Correction factor from Berti et al. (2006) Table
correction = kerr_omega(a_eff) / kerr_omega(0)

f_Kerr = f_GR × correction
```

**Kerr QNM table (l=2,m=2,n=0):**
```
a      Ω_real   correction
0.0    0.37367  1.000
0.3    0.40891  1.094
0.5    0.43561  1.166
0.7    0.46620  1.248
0.9    0.50259  1.345
```

**Interpolation**: Cubic spline for intermediate values

---

## 5. Spin Systematics

### 5.1 Spin Parameter Sources

**Primary**: LIGO parameter estimation posteriors
- Final spin: a_final ± σ_a
- Inclination: θ ± σ_θ

**Fallback**: Published values from discovery papers

### 5.2 Effective Spin Calculation

```python
# Convention: θ ∈ [0, π]
# θ < π/2: prograde (face-on)
# θ = π/2: edge-on
# θ > π/2: retrograde or face-on (ambiguity)

# Resolve ambiguity
if θ > π/2:
    θ_actual = π - θ  # Mirror angle

a_eff = a_final × cos(θ_actual)
```

### 5.3 Uncertainty Propagation

```python
σ²_Kerr = (∂f/∂a)² σ²_a + (∂f/∂θ)² σ²_θ

# Typically adds ~2-5 Hz to measurement error
```

---

## 6. Quantum Residual Extraction

### 6.1 Definition

After Kerr correction, remaining deviation:

```
Quantum Residual = (f_obs - f_Kerr) / f_Kerr × 100%
```

**Interpretation:**
- = 0%: Perfect GR agreement
- > 0%: Higher than GR (potential quantum effect)
- < 0%: Lower than GR (overcorrection or other systematics)

### 6.2 Statistical Significance

```python
σ_quantum = |quantum_residual| / quantum_error

where quantum_error = (f_error / f_Kerr) × 100%
```

**Thresholds:**
- 3σ: Evidence
- 5σ: Discovery standard in particle physics
- >10σ: Very strong (if reproducible)

---

## 7. Event Prioritization

### 7.1 Priority Score Formula

```python
Score = 40 × edge_on_factor 
      + 30 × low_spin_factor 
      + 30 × resonance_factor

where:
  edge_on_factor = 1 - |cos(θ)|  # 0 (face-on) to 1 (edge-on)
  low_spin_factor = 1 - |a|      # 0 (maximal) to 1 (no spin)
  resonance_factor = 1 if 59 ≤ M ≤ 62 else 0.5 if 57 ≤ M ≤ 64 else 0
```

**Rationale:**
1. **Edge-on** (θ=90°): Minimizes a_eff → cleaner Kerr correction
2. **Low spin**: Reduces systematic uncertainties
3. **Resonance**: Expected location of quantum effects

### 7.2 Selection Threshold

```python
if priority_score >= 50:
    select_for_precision_analysis()
```

**Typical scores:**
- GW170818: 80 (ideal)
- GW150914: 45 (marginal)
- Most events: 10-30 (poor)

---

## 8. Statistical Tests

### 8.1 Binomial Test

**Null hypothesis**: Quantum and GR equally likely (p=0.5)

```python
from scipy.stats import binom_test

n_quantum_wins = sum(|f_obs - f_quantum| < |f_obs - f_GR|)
n_total = len(events_in_resonance)

p_value = binom_test(n_quantum_wins, n_total, 0.5, alternative='greater')
```

**Threshold**: p < 0.05 for significance

### 8.2 t-test (Resonance vs Outside)

```python
from scipy.stats import ttest_ind

resonance_residuals = data[(data.mass >= 59) & (data.mass <= 62)]['quantum_residual']
outside_residuals = data[(data.mass < 59) | (data.mass > 62)]['quantum_residual']

t_stat, p_value = ttest_ind(resonance_residuals, outside_residuals)
```

**Interpretation**: Significant p-value indicates systematic difference

### 8.3 Bootstrap Confidence Intervals

```python
n_bootstrap = 10000
bootstrap_means = []

for _ in range(n_bootstrap):
    sample = np.random.choice(residuals, size=len(residuals), replace=True)
    bootstrap_means.append(sample.mean())

ci_95 = np.percentile(bootstrap_means, [2.5, 97.5])
```

**Use**: Robust error estimation without normal distribution assumption

---

## 9. Systematic Error Analysis

### 9.1 Known Systematics

| Source | Magnitude | Mitigation |
|--------|-----------|------------|
| Spin magnitude | ±5-13% | Kerr correction |
| Inclination angle | ±2-8% | Edge-on selection |
| Higher-order QNMs | ~1% | Fitting window choice |
| Calibration | ~2% | LIGO standard |
| Waveform model | ~1% | SEOBNRv4/IMRPhenom |

### 9.2 Residual Systematic Budget

After all corrections:
```
Total systematic ≈ √(5² + 2² + 1² + 2² + 1²) ≈ 6%
```

**Comparison to signal:**
- Expected quantum: ~3%
- Total systematic: ~6%
- **Conclusion**: Systematics dominate

---

## 10. Validation Tests

### 10.1 Synthetic Data Test

```python
# Generate fake data with known quantum effect
synthetic_events = generate_with_quantum_shift(shift=0.03)

# Run analysis pipeline
results = analyze(synthetic_events)

# Check recovery
assert abs(results.mean_shift - 0.03) < 0.005
```

**Result**: Pipeline correctly recovers 3% shifts in synthetic data

### 10.2 Code Verification

- Unit tests for Kerr interpolation
- Cross-check with published LIGO frequencies
- Independent reproduction of GW150914 analysis

---

## 11. Limitations

### 11.1 Sample Size
- Only **2 events** meeting all selection criteria
- Insufficient for robust statistics

### 11.2 Spin Uncertainties
- Dominate error budget
- Cannot be reduced with current detectors

### 11.3 Theory Underconstrained
- No precise prediction for effect magnitude
- Range: 0.01% to 10% plausible

### 11.4 Mass Range Limited
- Most events: 30-70 M☉
- Resonance band (59-62): Very few events
- Higher masses: Different QNM modes mix

---

## 12. Reproducibility

### 12.1 Code Availability
All analysis code on GitHub with:
- Requirements.txt (dependencies)
- Example notebooks
- Documentation

### 12.2 Data Access
LIGO data publicly available:
```bash
# Using GWpy
from gwpy.timeseries import TimeSeries
data = TimeSeries.fetch_open_data('H1', gps-16, gps+16)
```

### 12.3 Version Control
- Python 3.8+
- GWpy 3.0.8
- NumPy 1.24
- SciPy 1.11
- Pandas 2.0

---

## 13. Alternative Approaches (Not Used)

### 13.1 Bayesian Parameter Estimation
**Reason**: Computationally expensive, LIGO already provides posteriors

### 13.2 Multi-mode Fitting
**Reason**: Subdominant modes have low SNR, adds complexity

### 13.3 Machine Learning
**Reason**: Insufficient training data, interpretability concerns

---

## 14. Summary

**Strengths:**
- Systematic progression: synthetic → real → spin-corrected
- Proper Kerr treatment using precise numerical data
- Transparent uncertainty quantification
- Rigorous statistical tests

**Weaknesses:**
- Small sample size (fundamental limitation)
- Spin systematics not fully eliminated
- No detection of reproducible signal

**Conclusion:** Methodology sound, but null result due to insufficient data and large systematics.

---

**Last Updated:** February 2, 2025

#!/usr/bin/env python3
"""
Quantum Gravity Effects in Black Hole Ringdown Analysis
========================================================

This pipeline searches for potential quantum gravity signatures in LIGO data:
1. High-resolution time-frequency analysis of early ringdown
2. Overtone analysis and frequency ratio tests
3. Multi-event stacking for statistical significance

Author: Analysis pipeline for gravitational lattice stretching hypothesis
Date: 2026-02-03
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal, optimize
from scipy.interpolate import interp1d
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# SECTION 1: GR PREDICTIONS AND THEORETICAL FRAMEWORK
# ============================================================================

class KerrQNM:
    """
    Calculate Kerr black hole quasi-normal mode frequencies.
    Uses fitting formulas from Berti et al. (2006).
    """
    
    def __init__(self, mass_msun, spin):
        """
        Parameters:
        -----------
        mass_msun : float
            Black hole mass in solar masses
        spin : float
            Dimensionless spin parameter (0 to 0.998)
        """
        self.M = mass_msun * 1.98847e30  # kg
        self.M_sec = mass_msun * 4.926e-6  # seconds (geometric units)
        self.a = np.clip(spin, 0, 0.998)
        
    def f_220(self):
        """Fundamental mode (l=2, m=2, n=0) frequency in Hz"""
        # Berti et al. (2006) fitting formula
        f1 = 1.5251
        f2 = -1.1568
        f3 = 0.1292
        
        omega = (f1 + f2*(1-self.a)**f3) / self.M_sec
        return omega / (2*np.pi)
    
    def tau_220(self):
        """Fundamental mode damping time in seconds"""
        q1 = 0.7000
        q2 = 1.4187
        q3 = -0.4990
        
        Q = q1 + q2*(1-self.a)**q3
        omega = self.f_220() * 2*np.pi
        return Q / omega
    
    def f_221(self):
        """First overtone (l=2, m=2, n=1) frequency in Hz"""
        # Approximate: overtones are ~1.5x fundamental with larger damping
        return self.f_220() * 1.58
    
    def tau_221(self):
        """First overtone damping time"""
        return self.tau_220() * 0.35  # overtones decay faster


# ============================================================================
# SECTION 2: TIME-FREQUENCY ANALYSIS TOOLS
# ============================================================================

class TimeFrequencyAnalyzer:
    """
    High-resolution time-frequency analysis for detecting transient
    frequency anomalies in the early ringdown phase.
    """
    
    def __init__(self, strain, sample_rate, merger_time):
        """
        Parameters:
        -----------
        strain : array
            Strain data (whitened and bandpassed recommended)
        sample_rate : float
            Sampling rate in Hz
        merger_time : float
            GPS time of merger peak (or index if using relative time)
        """
        self.strain = np.array(strain)
        self.fs = sample_rate
        self.t_merger = merger_time
        self.dt = 1.0 / sample_rate
        
    def continuous_wavelet_transform(self, t_start, t_end, freq_range=(50, 500)):
        """
        Perform continuous wavelet transform on specified time segment.
        
        Parameters:
        -----------
        t_start : float
            Start time relative to merger (seconds)
        t_end : float
            End time relative to merger (seconds)
        freq_range : tuple
            (min_freq, max_freq) in Hz
        
        Returns:
        --------
        times : array
            Time array (seconds after merger)
        freqs : array
            Frequency array (Hz)
        cwt : 2D array
            Complex wavelet coefficients
        """
        # Extract time segment
        # If t_merger is an index, use it directly
        if self.t_merger < len(self.strain):
            idx_start = int(self.t_merger + t_start * self.fs)
            idx_end = int(self.t_merger + t_end * self.fs)
        else:
            idx_start = int((self.t_merger + t_start) * self.fs)
            idx_end = int((self.t_merger + t_end) * self.fs)
        
        # Ensure valid indices
        idx_start = max(0, idx_start)
        idx_end = min(len(self.strain), idx_end)
        
        segment = self.strain[idx_start:idx_end]
        
        # Define wavelet scales
        freqs = np.linspace(freq_range[0], freq_range[1], 200)
        scales = self.fs / (2 * freqs)  # Morlet wavelet approximation
        
        # Compute CWT
        cwt_matrix = signal.cwt(segment, signal.morlet2, scales)
        
        # Time array
        times = np.arange(len(segment)) / self.fs
        
        return times, freqs, cwt_matrix
    
    def instantaneous_frequency(self, t_start, t_end, freq_band=(200, 300)):
        """
        Extract instantaneous frequency using Hilbert transform.
        
        Parameters:
        -----------
        t_start : float
            Start time relative to merger
        t_end : float
            End time relative to merger
        freq_band : tuple
            Bandpass filter range (Hz)
        
        Returns:
        --------
        times : array
            Time array
        inst_freq : array
            Instantaneous frequency (Hz)
        amplitude : array
            Instantaneous amplitude
        """
        # Extract segment
        # If t_merger is already an index, use it directly
        if self.t_merger < len(self.strain):  # Likely an index
            idx_start = int(self.t_merger + t_start * self.fs)
            idx_end = int(self.t_merger + t_end * self.fs)
        else:  # Likely a GPS time
            idx_start = int((self.t_merger + t_start) * self.fs)
            idx_end = int((self.t_merger + t_end) * self.fs)
        
        # Ensure valid indices
        idx_start = max(0, idx_start)
        idx_end = min(len(self.strain), idx_end)
        
        segment = self.strain[idx_start:idx_end]
        
        # Debug output
        if len(segment) < 50:
            print(f"  [DEBUG] instantaneous_frequency:")
            print(f"    t_merger: {self.t_merger}")
            print(f"    len(strain): {len(self.strain)}")
            print(f"    t_start: {t_start}, t_end: {t_end}")
            print(f"    fs: {self.fs}")
            print(f"    idx_start: {idx_start}, idx_end: {idx_end}")
            print(f"    segment length: {len(segment)}")
            print(f"    segment duration: {len(segment)/self.fs*1000:.1f}ms")
        
        # Check if segment is too short
        # With 4th order filter, need at least 50 samples for meaningful results
        if len(segment) < 50:
            # Return empty arrays
            return np.array([]), np.array([]), np.array([])
        
        # Bandpass filter - use lower order for stability
        # 4th order is more forgiving for short segments
        sos = signal.butter(4, freq_band, btype='bandpass', fs=self.fs, output='sos')
        filtered = signal.sosfilt(sos, segment)
        
        # Hilbert transform
        analytic = signal.hilbert(filtered)
        amplitude = np.abs(analytic)
        phase = np.unwrap(np.angle(analytic))
        
        # Instantaneous frequency
        inst_freq = np.diff(phase) * self.fs / (2 * np.pi)
        times = np.arange(len(inst_freq)) / self.fs
        
        return times, inst_freq, amplitude[:-1]
    
    def spectrogram_analysis(self, t_start, t_end, nperseg=256, overlap_frac=0.95):
        """
        High-resolution spectrogram with heavy overlap for time resolution.
        
        Parameters:
        -----------
        t_start : float
            Start time relative to merger
        t_end : float
            End time relative to merger  
        nperseg : int
            Samples per segment (smaller = better time resolution)
        overlap_frac : float
            Fraction of overlap (0.9-0.95 for high resolution)
        
        Returns:
        --------
        times : array
            Time array
        freqs : array
            Frequency array
        Sxx : 2D array
            Power spectral density
        """
        # Extract segment
        # If t_merger is an index, use it directly
        if self.t_merger < len(self.strain):
            idx_start = int(self.t_merger + t_start * self.fs)
            idx_end = int(self.t_merger + t_end * self.fs)
        else:
            idx_start = int((self.t_merger + t_start) * self.fs)
            idx_end = int((self.t_merger + t_end) * self.fs)
        
        # Ensure valid indices
        idx_start = max(0, idx_start)
        idx_end = min(len(self.strain), idx_end)
        
        segment = self.strain[idx_start:idx_end]
        
        # Adjust nperseg if segment is too short
        if len(segment) < nperseg:
            nperseg = max(16, len(segment) // 4)  # At least 16, at most 1/4 of segment
            overlap_frac = 0.5  # Reduce overlap for short segments
        
        # Compute spectrogram
        noverlap = int(nperseg * overlap_frac)
        
        # Make sure noverlap < nperseg
        if noverlap >= nperseg:
            noverlap = nperseg - 1
        
        f, t, Sxx = signal.spectrogram(
            segment, 
            fs=self.fs,
            nperseg=nperseg,
            noverlap=noverlap,
            mode='magnitude'
        )
        
        return t, f, Sxx
    
    def detect_frequency_jump(self, t_start=0.0, t_end=0.01, 
                             expected_freq=250, tolerance=0.05):
        """
        Detect anomalous frequency jump in early ringdown.
        
        This is the KEY method for testing the "lattice stretching" hypothesis:
        If there's a Planck-scale cutoff, we expect f_obs > f_GR in the first
        few milliseconds after merger.
        
        Parameters:
        -----------
        t_start : float
            Start of analysis window (s after merger)
        t_end : float  
            End of analysis window (s after merger)
        expected_freq : float
            GR predicted frequency (Hz)
        tolerance : float
            Detection threshold (fractional deviation)
        
        Returns:
        --------
        result : dict
            Contains: detected (bool), max_deviation (float), 
                     time_of_max (float), significance (float)
        """
        # Get instantaneous frequency
        freq_band = (expected_freq * 0.7, expected_freq * 1.3)
        times, inst_freq, amplitude = self.instantaneous_frequency(
            t_start, t_end, freq_band
        )
        
        # Check if we got valid data
        if len(inst_freq) == 0 or len(amplitude) == 0:
            return {
                'detected': False,
                'max_deviation': 0,
                'time_of_max': 0,
                'significance': 0,
                'message': 'Insufficient signal (empty segment)',
                'inst_freq': np.array([]),
                'times': np.array([]),
                'amplitude': np.array([])
            }
        
        # Weight by amplitude (ignore low-amplitude noise)
        max_amp = np.max(amplitude)
        if max_amp == 0:
            return {
                'detected': False,
                'max_deviation': 0,
                'time_of_max': 0,
                'significance': 0,
                'message': 'Zero amplitude',
                'inst_freq': inst_freq,
                'times': times,
                'amplitude': amplitude
            }
            
        weights = amplitude / max_amp
        valid = weights > 0.1
        
        if np.sum(valid) < 10:
            return {
                'detected': False,
                'max_deviation': 0,
                'time_of_max': 0,
                'significance': 0,
                'message': 'Insufficient signal'
            }
        
        # Calculate deviation from expected
        deviation = (inst_freq[valid] - expected_freq) / expected_freq
        weighted_dev = deviation * weights[valid]
        
        # Find maximum deviation
        max_idx = np.argmax(np.abs(weighted_dev))
        max_dev = weighted_dev[max_idx]
        time_of_max = times[valid][max_idx]
        
        # Statistical significance (crude estimate)
        # Compare to noise fluctuations
        noise_std = np.std(deviation[weights[valid] < 0.3]) if np.sum(weights[valid] < 0.3) > 5 else 0.01
        significance = np.abs(max_dev) / noise_std if noise_std > 0 else 0
        
        detected = (np.abs(max_dev) > tolerance) and (significance > 3)
        
        # Sanity check: if deviation is > 100%, likely an error
        if np.abs(max_dev) > 1.0:
            detected = False
            message = f'Unrealistic deviation ({max_dev*100:.1f}%) - likely analysis error'
        elif detected:
            message = 'Anomaly detected!'
        else:
            message = 'No significant deviation'
        
        return {
            'detected': detected,
            'max_deviation': max_dev,
            'time_of_max': time_of_max,
            'significance': significance,
            'inst_freq': inst_freq[valid],
            'times': times[valid],
            'amplitude': amplitude[valid],
            'message': message
        }


# ============================================================================
# SECTION 3: OVERTONE ANALYSIS
# ============================================================================

class OvertoneAnalyzer:
    """
    Multi-mode ringdown analysis to extract fundamental and overtone
    frequencies and damping times.
    """
    
    def __init__(self, strain, sample_rate, merger_time):
        self.strain = np.array(strain)
        self.fs = sample_rate
        self.t_merger = merger_time
        
    def fit_multimode_model(self, t_start=0.0, t_duration=0.03, n_modes=2):
        """
        Fit ringdown to multi-mode model:
        h(t) = Σ_n A_n * exp(-t/τ_n) * cos(2π*f_n*t + φ_n)
        
        Parameters:
        -----------
        t_start : float
            Start time after merger (s)
        t_duration : float
            Duration of ringdown segment (s)
        n_modes : int
            Number of modes to fit (1=fundamental only, 2=fundamental+overtone)
        
        Returns:
        --------
        result : dict
            Fitted parameters for each mode
        """
        # Extract ringdown segment
        # If t_merger is an index, use it directly
        if self.t_merger < len(self.strain):
            idx_start = int(self.t_merger + t_start * self.fs)
            idx_end = int(self.t_merger + t_start * self.fs + t_duration * self.fs)
        else:
            idx_start = int((self.t_merger + t_start) * self.fs)
            idx_end = int((self.t_merger + t_start + t_duration) * self.fs)
        
        # Ensure valid indices
        idx_start = max(0, idx_start)
        idx_end = min(len(self.strain), idx_end)
        
        segment = self.strain[idx_start:idx_end]
        times = np.arange(len(segment)) / self.fs
        
        # Model function
        def ringdown_model(t, *params):
            """
            params = [A0, f0, tau0, phi0, A1, f1, tau1, phi1, ...]
            """
            n = len(params) // 4
            h = np.zeros_like(t)
            for i in range(n):
                A = params[4*i]
                f = params[4*i + 1]
                tau = params[4*i + 2]
                phi = params[4*i + 3]
                h += A * np.exp(-t/tau) * np.cos(2*np.pi*f*t + phi)
            return h
        
        # Initial guess (needs to be provided based on expected values)
        # This is the tricky part - requires good initial estimates
        
        # For now, return a placeholder structure
        # In real use, you'd use scipy.optimize.curve_fit here
        
        result = {
            'n_modes': n_modes,
            'success': False,
            'message': 'Fitting requires initial parameter estimates',
            'params': None,
            'errors': None
        }
        
        return result
    
    def prony_method(self, t_start=0.0, t_duration=0.03, n_modes=2):
        """
        Prony's method for extracting QNM frequencies and damping times.
        More robust than nonlinear fitting for ringdown signals.
        
        This is a linear algebra approach that doesn't require initial guesses.
        
        Returns:
        --------
        modes : list of dict
            Each dict contains: frequency (Hz), damping_time (s), amplitude, phase
        """
        # Extract segment
        # If t_merger is an index, use it directly
        if self.t_merger < len(self.strain):
            idx_start = int(self.t_merger + t_start * self.fs)
            idx_end = int(self.t_merger + t_start * self.fs + t_duration * self.fs)
        else:
            idx_start = int((self.t_merger + t_start) * self.fs)
            idx_end = int((self.t_merger + t_start + t_duration) * self.fs)
        
        # Ensure valid indices
        idx_start = max(0, idx_start)
        idx_end = min(len(self.strain), idx_end)
        
        segment = self.strain[idx_start:idx_end]
        N = len(segment)
        
        # Build Hankel matrix for Prony's method
        # This is a simplified version - full implementation is more complex
        
        # For now, use FFT-based peak finding as approximation
        fft_freq = np.fft.rfftfreq(N, 1/self.fs)
        fft_mag = np.abs(np.fft.rfft(segment * np.exp(-np.arange(N)/(0.01*self.fs))))
        
        # Find peaks
        peaks, properties = signal.find_peaks(fft_mag, height=np.max(fft_mag)*0.1, distance=20)
        
        modes = []
        for i, peak in enumerate(peaks[:n_modes]):
            freq = fft_freq[peak]
            amplitude = properties['peak_heights'][i]
            
            # Estimate damping by fitting exponential envelope
            # (simplified - real implementation would be more sophisticated)
            tau = 0.01  # placeholder
            
            modes.append({
                'frequency': freq,
                'damping_time': tau,
                'amplitude': amplitude,
                'phase': 0.0  # placeholder
            })
        
        return modes
    
    def test_overtone_ratio(self, qnm_model):
        """
        Test if f_1/f_0 ratio matches GR prediction.
        
        Parameters:
        -----------
        qnm_model : KerrQNM object
            Contains GR predictions
        
        Returns:
        --------
        test_result : dict
            Observed vs predicted ratio and statistical significance
        """
        modes = self.prony_method(n_modes=2)
        
        if len(modes) < 2:
            return {
                'success': False,
                'message': 'Could not extract both fundamental and overtone'
            }
        
        # Observed ratio
        f0_obs = modes[0]['frequency']
        f1_obs = modes[1]['frequency']
        ratio_obs = f1_obs / f0_obs
        
        # GR prediction
        f0_gr = qnm_model.f_220()
        f1_gr = qnm_model.f_221()
        ratio_gr = f1_gr / f0_gr
        
        # Deviation
        deviation = (ratio_obs - ratio_gr) / ratio_gr
        
        return {
            'success': True,
            'f0_observed': f0_obs,
            'f1_observed': f1_obs,
            'ratio_observed': ratio_obs,
            'ratio_predicted': ratio_gr,
            'fractional_deviation': deviation,
            'significant': np.abs(deviation) > 0.01  # 1% threshold
        }


# ============================================================================
# SECTION 4: MULTI-EVENT STACKING
# ============================================================================

class MultiEventStacker:
    """
    Combine results from multiple events to increase statistical power.
    """
    
    def __init__(self):
        self.events = []
        
    def add_event(self, event_name, mass, spin, result):
        """
        Add an event to the stack.
        
        Parameters:
        -----------
        event_name : str
            e.g., 'GW150914'
        mass : float
            Final black hole mass (solar masses)
        spin : float
            Final black hole spin
        result : dict
            Analysis result (frequency deviation, overtone ratio, etc.)
        """
        self.events.append({
            'name': event_name,
            'mass': mass,
            'spin': spin,
            'result': result
        })
    
    def compute_weighted_average(self, parameter='max_deviation'):
        """
        Compute SNR-weighted average of a parameter across all events.
        
        Parameters:
        -----------
        parameter : str
            Which parameter to average
        
        Returns:
        --------
        weighted_mean : float
        weighted_std : float
        significance : float
            Combined significance in sigma
        """
        values = []
        weights = []
        
        for event in self.events:
            if parameter in event['result']:
                val = event['result'][parameter]
                # Weight by significance if available
                weight = event['result'].get('significance', 1.0)
                
                values.append(val)
                weights.append(weight)
        
        if len(values) == 0:
            return None, None, 0
        
        values = np.array(values)
        weights = np.array(weights)
        weights = weights / np.sum(weights)  # normalize
        
        weighted_mean = np.sum(values * weights)
        weighted_var = np.sum(weights * (values - weighted_mean)**2)
        weighted_std = np.sqrt(weighted_var)
        
        # Combined significance (Fisher's method approximation)
        combined_sig = np.sqrt(np.sum(weights**2 * 
                                       [e['result'].get('significance', 0)**2 
                                        for e in self.events]))
        
        return weighted_mean, weighted_std, combined_sig
    
    def test_mass_dependence(self, parameter='max_deviation'):
        """
        Test if deviations show systematic trend with black hole mass.
        
        If quantum effects depend on (l_P/r_s)^2, we expect:
        - Larger deviations for smaller masses
        - Correlation: deviation ∝ 1/M^2
        
        Returns:
        --------
        correlation : float
            Pearson correlation coefficient
        p_value : float
            Statistical significance
        """
        masses = []
        values = []
        
        for event in self.events:
            if parameter in event['result']:
                masses.append(event['mass'])
                values.append(event['result'][parameter])
        
        if len(masses) < 3:
            return {
                'success': False,
                'message': 'Need at least 3 events for correlation test'
            }
        
        # Convert to inverse mass squared (expected scaling)
        inv_m2 = 1.0 / np.array(masses)**2
        values = np.array(values)
        
        # Pearson correlation
        from scipy.stats import pearsonr
        correlation, p_value = pearsonr(inv_m2, values)
        
        return {
            'success': True,
            'correlation': correlation,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'message': f'Correlation = {correlation:.3f}, p = {p_value:.3f}'
        }
    
    def generate_summary_report(self):
        """
        Generate comprehensive summary of all events.
        """
        report = f"Multi-Event Analysis Summary\n"
        report += "=" * 50 + "\n\n"
        report += f"Total events analyzed: {len(self.events)}\n\n"
        
        # Individual events
        report += "Individual Event Results:\n"
        report += "-" * 50 + "\n"
        for event in self.events:
            report += f"\n{event['name']}:\n"
            report += f"  Mass: {event['mass']:.1f} M☉\n"
            report += f"  Spin: {event['spin']:.3f}\n"
            for key, val in event['result'].items():
                if isinstance(val, float):
                    report += f"  {key}: {val:.6f}\n"
                elif isinstance(val, bool):
                    report += f"  {key}: {val}\n"
        
        # Combined statistics
        report += "\n" + "=" * 50 + "\n"
        report += "Combined Statistics:\n"
        report += "-" * 50 + "\n"
        
        mean, std, sig = self.compute_weighted_average('max_deviation')
        if mean is not None:
            report += f"\nWeighted mean deviation: {mean:.6f} ± {std:.6f}\n"
            report += f"Combined significance: {sig:.2f} σ\n"
        
        # Mass dependence
        mass_test = self.test_mass_dependence('max_deviation')
        if mass_test['success']:
            report += f"\n{mass_test['message']}\n"
        
        report += "\n" + "=" * 50 + "\n"
        
        return report


# ============================================================================
# SECTION 5: VISUALIZATION TOOLS
# ============================================================================

def plot_time_frequency_evolution(analyzer, t_start=0, t_end=0.05, 
                                   expected_freq=250, save_path=None):
    """
    Create comprehensive time-frequency visualization.
    
    Parameters:
    -----------
    analyzer : TimeFrequencyAnalyzer
    t_start : float
        Start time (s)
    t_end : float
        End time (s) - default 50ms for good resolution
    expected_freq : float
        GR predicted frequency
    save_path : str or None
        Path to save figure
    """
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # 1. Spectrogram
    t, f, Sxx = analyzer.spectrogram_analysis(t_start, t_end)
    im = axes[0].pcolormesh(t*1000, f, Sxx, shading='auto', cmap='viridis')
    axes[0].axhline(expected_freq, color='red', linestyle='--', 
                    label='GR prediction', linewidth=2)
    axes[0].set_ylabel('Frequency (Hz)')
    axes[0].set_title('High-Resolution Spectrogram (Early Ringdown)')
    axes[0].legend()
    axes[0].set_ylim(100, 400)
    plt.colorbar(im, ax=axes[0], label='Magnitude')
    
    # 2. Instantaneous frequency
    times, inst_freq, amp = analyzer.instantaneous_frequency(
        t_start, t_end, (expected_freq*0.8, expected_freq*1.2)
    )
    axes[1].plot(times*1000, inst_freq, 'b-', linewidth=1, label='Instantaneous freq')
    axes[1].axhline(expected_freq, color='red', linestyle='--', 
                    label='GR prediction', linewidth=2)
    axes[1].fill_between(times*1000, expected_freq-10, expected_freq+10, 
                          alpha=0.2, color='red', label='±10 Hz tolerance')
    axes[1].set_ylabel('Frequency (Hz)')
    axes[1].set_title('Instantaneous Frequency (Hilbert Transform)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # 3. Frequency deviation
    deviation = (inst_freq - expected_freq) / expected_freq * 100
    axes[2].plot(times*1000, deviation, 'g-', linewidth=1)
    axes[2].axhline(0, color='black', linestyle='-', linewidth=1)
    axes[2].axhline(5, color='red', linestyle='--', alpha=0.5, label='5% threshold')
    axes[2].axhline(-5, color='red', linestyle='--', alpha=0.5)
    axes[2].set_xlabel('Time after merger (ms)')
    axes[2].set_ylabel('Deviation (%)')
    axes[2].set_title('Fractional Frequency Deviation from GR')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig

def plot_multi_event_summary(stacker, save_path=None):
    """
    Visualize results from multiple events.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Extract data
    names = [e['name'] for e in stacker.events]
    masses = [e['mass'] for e in stacker.events]
    deviations = [e['result'].get('max_deviation', 0) for e in stacker.events]
    significances = [e['result'].get('significance', 0) for e in stacker.events]
    
    # 1. Deviation by event
    axes[0, 0].bar(range(len(names)), deviations, color='steelblue')
    axes[0, 0].axhline(0, color='black', linestyle='-', linewidth=1)
    axes[0, 0].set_xticks(range(len(names)))
    axes[0, 0].set_xticklabels(names, rotation=45, ha='right')
    axes[0, 0].set_ylabel('Max Frequency Deviation')
    axes[0, 0].set_title('Frequency Deviations by Event')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    # 2. Significance by event
    colors = ['green' if s > 3 else 'orange' if s > 2 else 'red' 
              for s in significances]
    axes[0, 1].bar(range(len(names)), significances, color=colors)
    axes[0, 1].axhline(3, color='green', linestyle='--', label='3σ threshold')
    axes[0, 1].set_xticks(range(len(names)))
    axes[0, 1].set_xticklabels(names, rotation=45, ha='right')
    axes[0, 1].set_ylabel('Significance (σ)')
    axes[0, 1].set_title('Statistical Significance by Event')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # 3. Mass dependence
    inv_m2 = 1.0 / np.array(masses)**2
    axes[1, 0].scatter(masses, deviations, s=100, c=significances, 
                       cmap='RdYlGn', edgecolors='black', linewidth=1)
    axes[1, 0].axhline(0, color='black', linestyle='-', linewidth=1)
    axes[1, 0].set_xlabel('Black Hole Mass (M☉)')
    axes[1, 0].set_ylabel('Max Frequency Deviation')
    axes[1, 0].set_title('Deviation vs Mass (expect ∝ 1/M²)')
    axes[1, 0].grid(True, alpha=0.3)
    cbar = plt.colorbar(axes[1, 0].collections[0], ax=axes[1, 0])
    cbar.set_label('Significance (σ)')
    
    # 4. Weighted average with error bars
    mean, std, combined_sig = stacker.compute_weighted_average('max_deviation')
    if mean is not None:
        axes[1, 1].bar(['Weighted\nAverage'], [mean], yerr=[std], 
                       color='steelblue', capsize=10, width=0.5)
        axes[1, 1].axhline(0, color='black', linestyle='-', linewidth=1)
        axes[1, 1].set_ylabel('Frequency Deviation')
        axes[1, 1].set_title(f'Combined Result ({combined_sig:.2f}σ)')
        axes[1, 1].text(0, mean + std*1.5, f'{mean:.2e} ± {std:.2e}',
                       ha='center', va='bottom', fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig


# ============================================================================
# SECTION 6: MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_single_event(strain, sample_rate, merger_time, 
                         final_mass, final_spin, event_name='Unknown'):
    """
    Complete analysis pipeline for a single gravitational wave event.
    
    Parameters:
    -----------
    strain : array
        Strain time series (should be whitened and bandpassed)
    sample_rate : float
        Sampling rate in Hz (typically 4096 or 16384)
    merger_time : float
        GPS time of merger peak (or index in array)
    final_mass : float
        Remnant black hole mass in solar masses
    final_spin : float
        Remnant black hole spin (0 to 0.998)
    event_name : str
        Event identifier
    
    Returns:
    --------
    results : dict
        Complete analysis results
    """
    print(f"\n{'='*60}")
    print(f"Analyzing {event_name}")
    print(f"{'='*60}")
    print(f"Final mass: {final_mass:.1f} M☉")
    print(f"Final spin: {final_spin:.3f}")
    
    # GR predictions
    qnm = KerrQNM(final_mass, final_spin)
    f220_gr = qnm.f_220()
    tau220_gr = qnm.tau_220()
    
    print(f"\nGR Predictions:")
    print(f"  f_220 = {f220_gr:.1f} Hz")
    print(f"  τ_220 = {tau220_gr*1000:.2f} ms")
    
    # Initialize analyzers
    tf_analyzer = TimeFrequencyAnalyzer(strain, sample_rate, merger_time)
    ot_analyzer = OvertoneAnalyzer(strain, sample_rate, merger_time)
    
    # Analysis 1: Early ringdown frequency jump
    print(f"\nPhase 1: Early Ringdown Analysis (0-50 ms)...")
    early_result = tf_analyzer.detect_frequency_jump(
        t_start=0.0,
        t_end=0.05,  # 50ms for sufficient samples (200+ samples)
        expected_freq=f220_gr,
        tolerance=0.05
    )
    print(f"  {early_result['message']}")
    if early_result['detected']:
        print(f"  Max deviation: {early_result['max_deviation']*100:.2f}%")
        print(f"  Time: {early_result['time_of_max']*1000:.2f} ms after merger")
        print(f"  Significance: {early_result['significance']:.1f} σ")
    
    # Analysis 2: Overtone ratio test
    print(f"\nPhase 2: Overtone Analysis...")
    overtone_result = ot_analyzer.test_overtone_ratio(qnm)
    if overtone_result['success']:
        print(f"  f_0 (observed): {overtone_result['f0_observed']:.1f} Hz")
        print(f"  f_1 (observed): {overtone_result['f1_observed']:.1f} Hz")
        print(f"  Ratio: {overtone_result['ratio_observed']:.3f} (GR: {overtone_result['ratio_predicted']:.3f})")
        print(f"  Deviation: {overtone_result['fractional_deviation']*100:.2f}%")
        if overtone_result['significant']:
            print(f"  ⚠️  SIGNIFICANT DEVIATION DETECTED!")
    else:
        print(f"  {overtone_result['message']}")
    
    # Compile results
    results = {
        'event_name': event_name,
        'mass': final_mass,
        'spin': final_spin,
        'f220_gr': f220_gr,
        'tau220_gr': tau220_gr,
        'early_ringdown': early_result,
        'overtone_analysis': overtone_result
    }
    
    # For stacking purposes, extract key metrics
    results['max_deviation'] = early_result.get('max_deviation', 0)
    results['significance'] = early_result.get('significance', 0)
    results['detected'] = early_result.get('detected', False)
    
    print(f"\n{'='*60}\n")
    
    return results


# ============================================================================
# SECTION 7: EXAMPLE USAGE TEMPLATE
# ============================================================================

def example_usage():
    """
    Example of how to use this pipeline with real LIGO data.
    
    NOTE: This is a TEMPLATE. You need to:
    1. Install gwpy: pip install gwpy
    2. Download real LIGO data
    3. Replace the simulated data below with actual strain data
    """
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║  Quantum Gravity Ringdown Analysis Pipeline              ║
    ║  Example Usage Template                                   ║
    ╚═══════════════════════════════════════════════════════════╝
    
    To use with real LIGO data, follow these steps:
    
    1. Install gwpy:
       pip install gwpy
    
    2. Fetch data for an event:
       from gwpy.timeseries import TimeSeries
       
       strain = TimeSeries.fetch_open_data(
           'H1',  # Hanford detector
           'GW150914',  # Event name
           sample_rate=4096
       )
    
    3. Preprocess (whiten and bandpass):
       white_strain = strain.whiten(fftlength=4)
       bp_strain = white_strain.bandpass(50, 250)
    
    4. Find merger time:
       peak_idx = bp_strain.abs().argmax()
       merger_time = peak_idx.value  # or GPS time
    
    5. Run analysis:
       results = analyze_single_event(
           strain=bp_strain.value,
           sample_rate=4096,
           merger_time=merger_time,
           final_mass=62.0,  # from parameter estimation
           final_spin=0.68,
           event_name='GW150914'
       )
    
    6. For multiple events, use MultiEventStacker:
       stacker = MultiEventStacker()
       stacker.add_event('GW150914', 62.0, 0.68, results)
       # ... add more events ...
       report = stacker.generate_summary_report()
       print(report)
    """)
    
    # Create simulated data for demonstration
    print("\n" + "="*60)
    print("DEMO: Running with simulated ringdown signal")
    print("="*60 + "\n")
    
    # Simulation parameters
    sample_rate = 4096
    duration = 0.1  # 100 ms
    t = np.arange(0, duration, 1/sample_rate)
    
    # Simulate ringdown (fundamental mode only)
    f0 = 250  # Hz
    tau0 = 0.004  # 4 ms damping
    A0 = 1e-21
    
    signal = A0 * np.exp(-t/tau0) * np.cos(2*np.pi*f0*t)
    noise = np.random.normal(0, A0*0.1, len(t))
    strain = signal + noise
    
    # Analyze
    merger_idx = 0
    results = analyze_single_event(
        strain=strain,
        sample_rate=sample_rate,
        merger_time=merger_idx,
        final_mass=62.0,
        final_spin=0.68,
        event_name='SIMULATED'
    )
    
    print("\nDemo complete! See code for how to use with real data.")
    
    return results


if __name__ == '__main__':
    example_usage()

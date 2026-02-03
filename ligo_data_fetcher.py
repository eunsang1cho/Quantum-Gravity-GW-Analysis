#!/usr/bin/env python3
"""
LIGO Data Fetcher and Preprocessor
===================================

This script handles downloading and preprocessing LIGO open data
for quantum gravity ringdown analysis.

Usage:
    python ligo_data_fetcher.py --event GW150914 --detector H1
"""

import argparse
import numpy as np

# These will be imported when running with gwpy installed
try:
    from gwpy.timeseries import TimeSeries
    from gwpy.signal import filter_design
    GWPY_AVAILABLE = True
except ImportError:
    GWPY_AVAILABLE = False
    print("WARNING: gwpy not installed. Install with: pip install gwpy")


# ============================================================================
# EVENT CATALOG WITH PARAMETERS
# ============================================================================

LIGO_EVENTS = {
    'GW150914': {
        'gps_time': 1126259462.4,
        'mass_1': 36.0,  # solar masses
        'mass_2': 29.0,
        'final_mass': 62.0,
        'final_spin': 0.68,
        'distance': 410,  # Mpc
        'snr_H1': 24,
        'snr_L1': 13,
    },
    'GW151226': {
        'gps_time': 1135136350.6,
        'mass_1': 14.2,
        'mass_2': 7.5,
        'final_mass': 20.8,
        'final_spin': 0.74,
        'distance': 440,
        'snr_H1': 13,
        'snr_L1': 13,
    },
    'GW170814': {
        'gps_time': 1186741861.5,
        'mass_1': 30.5,
        'mass_2': 25.3,
        'final_mass': 53.2,
        'final_spin': 0.72,
        'distance': 540,
        'snr_H1': 18,
        'snr_L1': 15,
        'snr_V1': 10,
    },
    'GW170817': {
        'gps_time': 1187008882.4,
        'mass_1': 1.46,  # neutron star merger
        'mass_2': 1.27,
        'final_mass': 2.73,
        'final_spin': 0.89,
        'distance': 40,
        'snr_H1': 26,
        'snr_L1': 18,
        'type': 'BNS',  # binary neutron star
    },
    'GW190521': {
        'gps_time': 1242442967.4,
        'mass_1': 85.0,
        'mass_2': 66.0,
        'final_mass': 142.0,  # intermediate mass BH
        'final_spin': 0.72,
        'distance': 5300,
        'snr_H1': 15,
        'snr_L1': 15,
    },
    'GW190814': {
        'gps_time': 1249852257.0,
        'mass_1': 23.0,
        'mass_2': 2.6,  # mass gap object
        'final_mass': 25.6,
        'final_spin': 0.71,
        'distance': 241,
        'snr_H1': 25,
        'snr_L1': 25,
    },
}


# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def fetch_event_data(event_name, detector='H1', sample_rate=4096, 
                     duration=32, crop_to_merger=False):
    """
    Fetch strain data for a specific event from LIGO open data.
    
    Parameters:
    -----------
    event_name : str
        Event name (e.g., 'GW150914')
    detector : str
        Detector name ('H1', 'L1', or 'V1')
    sample_rate : int
        Desired sample rate (Hz)
    duration : float
        Duration of data to fetch (seconds)
    crop_to_merger : bool
        If True, return data centered on merger (after preprocessing)
    
    Returns:
    --------
    strain : TimeSeries
        Strain data
    event_params : dict
        Event parameters
    merger_crop_info : dict or None
        Information for cropping to merger (if crop_to_merger=True)
    """
    if not GWPY_AVAILABLE:
        raise ImportError("gwpy is required. Install with: pip install gwpy")
    
    if event_name not in LIGO_EVENTS:
        raise ValueError(f"Unknown event: {event_name}. Available: {list(LIGO_EVENTS.keys())}")
    
    event_params = LIGO_EVENTS[event_name]
    gps_time = event_params['gps_time']
    
    # Check if detector observed this event
    snr_key = f'snr_{detector}'
    if snr_key not in event_params:
        print(f"Warning: {detector} may not have observed {event_name}")
    
    print(f"Fetching {event_name} from {detector}...")
    print(f"GPS time: {gps_time}")
    
    # Fetch data - use full duration for better whitening
    start_time = gps_time - duration/2
    end_time = gps_time + duration/2
    
    try:
        strain = TimeSeries.fetch_open_data(
            detector,
            start_time,
            end_time,
            sample_rate=sample_rate,
            cache=True  # cache locally for faster repeat access
        )
        print(f"✓ Data fetched successfully")
        print(f"  Sample rate: {strain.sample_rate.value} Hz")
        print(f"  Duration: {strain.duration.value:.1f} s")
        
        # Store merger info for later cropping (after preprocessing)
        merger_crop_info = None
        if crop_to_merger:
            merger_crop_info = {
                'crop_start': gps_time - 0.15,  # 150 ms before
                'crop_end': gps_time + 0.15,    # 150 ms after (ensures ringdown data)
                'merger_gps': gps_time
            }
            print(f"  Note: Will crop to merger after preprocessing (±150ms)")
        
        return strain, event_params, merger_crop_info
        
    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        raise


def preprocess_strain(strain, fmin=20, fmax=400, fftlength=None):
    """
    Preprocess strain data: whitening and bandpass filtering.
    
    Parameters:
    -----------
    strain : TimeSeries
        Raw strain data
    fmin : float
        Lower frequency for bandpass (Hz)
    fmax : float
        Upper frequency for bandpass (Hz)
    fftlength : float or None
        FFT length for whitening (seconds)
        If None, automatically set to min(4, duration/4)
    
    Returns:
    --------
    processed_strain : TimeSeries
        Whitened and bandpassed strain
    """
    print("\nPreprocessing strain data...")
    
    # Auto-adjust fftlength for short data
    duration = strain.duration.value
    if fftlength is None or fftlength > duration / 4:
        fftlength = min(4, duration / 4)
        print(f"  Auto-adjusted fftlength to {fftlength:.2f}s for {duration:.2f}s data")
    
    # Step 1: Whiten
    print(f"  1. Whitening (fftlength={fftlength:.2f}s)...")
    try:
        white = strain.whiten(fftlength=fftlength, fduration=2)
    except ValueError as e:
        # If whitening fails, use even shorter fftlength
        fftlength = max(0.25, duration / 8)
        print(f"     Retrying with fftlength={fftlength:.2f}s...")
        white = strain.whiten(fftlength=fftlength, fduration=1)
    
    # Step 2: Bandpass filter
    print(f"  2. Bandpass filtering ({fmin}-{fmax} Hz)...")
    bp = white.bandpass(fmin, fmax)
    
    # Step 3: Crop edges (remove filter artifacts)
    # Adjust crop duration based on data length
    crop_dur = min(0.02, duration * 0.1)  # 2% of duration or 20ms
    print(f"  3. Cropping filter edges ({crop_dur*1000:.0f}ms from each end)...")
    
    if duration > 2 * crop_dur:
        bp = bp.crop(bp.t0.value + crop_dur, bp.times[-1].value - crop_dur)
    else:
        print(f"     Skipping crop (data too short)")
    
    print("✓ Preprocessing complete")
    
    return bp


def find_merger_peak(strain, search_window=None, min_post_merger_duration=0.05):
    """
    Find the merger peak in the strain data.
    
    Parameters:
    -----------
    strain : TimeSeries
        Preprocessed strain data
    search_window : tuple or None
        (start, end) GPS times to search, or None for entire series
    min_post_merger_duration : float
        Minimum duration (seconds) of data required after merger peak
    
    Returns:
    --------
    merger_time : float
        GPS time of peak
    merger_idx : int
        Index of peak in array
    """
    print("\nFinding merger peak...")
    
    if search_window is not None:
        search_strain = strain.crop(search_window[0], search_window[1])
    else:
        search_strain = strain
    
    # Find maximum absolute value
    abs_strain = np.abs(search_strain.value)
    merger_idx_local = np.argmax(abs_strain)
    
    # Convert to GPS time
    merger_time = search_strain.times[merger_idx_local].value
    
    # Find index in original strain
    merger_idx = np.argmin(np.abs(strain.times.value - merger_time))
    
    # Check if we have enough post-merger data
    samples_after = len(strain) - merger_idx
    duration_after = samples_after / strain.sample_rate.value
    
    print(f"✓ Merger peak found:")
    print(f"  GPS time: {merger_time:.6f}")
    print(f"  Index: {merger_idx}/{len(strain)}")
    print(f"  Peak strain: {abs_strain[merger_idx_local]:.2e}")
    print(f"  Data after merger: {duration_after*1000:.1f}ms")
    
    if duration_after < min_post_merger_duration:
        print(f"⚠️  WARNING: Only {duration_after*1000:.1f}ms after merger")
        print(f"   Recommended: at least {min_post_merger_duration*1000:.0f}ms for ringdown analysis")
    
    return merger_time, merger_idx


def compute_psd(strain, fftlength=4):
    """
    Compute power spectral density for noise characterization.
    
    Parameters:
    -----------
    strain : TimeSeries
        Strain data
    fftlength : float
        FFT length (seconds)
    
    Returns:
    --------
    psd : FrequencySeries
        Power spectral density
    """
    psd = strain.psd(fftlength=fftlength, method='median')
    return psd


# ============================================================================
# QUALITY CHECKS
# ============================================================================

def check_data_quality(strain, event_params):
    """
    Perform basic quality checks on the data.
    
    Returns:
    --------
    passed : bool
        Whether data passes quality checks
    report : str
        Quality report
    """
    report = "\nData Quality Checks:\n" + "-"*40 + "\n"
    passed = True
    
    # Check 1: No NaN values
    if np.any(np.isnan(strain.value)):
        report += "✗ FAIL: NaN values detected\n"
        passed = False
    else:
        report += "✓ PASS: No NaN values\n"
    
    # Check 2: No Inf values
    if np.any(np.isinf(strain.value)):
        report += "✗ FAIL: Inf values detected\n"
        passed = False
    else:
        report += "✓ PASS: No Inf values\n"
    
    # Check 3: Reasonable strain amplitude
    max_strain = np.max(np.abs(strain.value))
    if max_strain > 1e-18:  # after whitening, should be order ~1
        report += f"⚠ WARNING: Very large strain amplitude: {max_strain:.2e}\n"
        report += "  (May indicate preprocessing issue)\n"
    else:
        report += f"✓ PASS: Reasonable amplitude ({max_strain:.2e})\n"
    
    # Check 4: Duration
    duration = strain.duration.value
    if duration < 0.1:
        report += f"✗ FAIL: Duration too short: {duration:.3f}s\n"
        passed = False
    else:
        report += f"✓ PASS: Sufficient duration ({duration:.2f}s)\n"
    
    report += "-"*40 + "\n"
    
    return passed, report


# ============================================================================
# COMPLETE PIPELINE
# ============================================================================

def prepare_event_for_analysis(event_name, detector='H1', 
                               sample_rate=4096, save_to_file=True):
    """
    Complete pipeline: fetch, preprocess, and prepare event data.
    
    Parameters:
    -----------
    event_name : str
        Event name
    detector : str
        Detector
    sample_rate : int
        Sample rate
    save_to_file : bool
        If True, save processed data to .npy file
    
    Returns:
    --------
    data_package : dict
        Contains all necessary data for analysis
    """
    print(f"\n{'='*60}")
    print(f"Preparing {event_name} for analysis")
    print(f"{'='*60}\n")
    
    # Step 1: Fetch data (full 32s for good whitening)
    strain_raw, event_params, merger_crop_info = fetch_event_data(
        event_name, 
        detector, 
        sample_rate,
        duration=32,
        crop_to_merger=True  # Get crop info, but don't crop yet
    )
    
    # Step 2: Preprocess (on full data for better whitening)
    strain_processed = preprocess_strain(
        strain_raw,
        fmin=20,
        fmax=400,
        fftlength=None  # Auto-adjust
    )
    
    # Step 3: Now crop to merger region (after preprocessing)
    if merger_crop_info is not None:
        print(f"\nCropping to merger-centered window...")
        strain_processed = strain_processed.crop(
            merger_crop_info['crop_start'],
            merger_crop_info['crop_end']
        )
        duration_ms = strain_processed.duration.value * 1000
        print(f"✓ Cropped to {duration_ms:.0f}ms centered on merger")
    
    # Step 4: Find merger
    merger_time, merger_idx = find_merger_peak(strain_processed)
    
    # Step 5: Quality check
    passed, report = check_data_quality(strain_processed, event_params)
    print(report)
    
    if not passed:
        print("⚠️  WARNING: Data quality checks failed!")
    
    # Package results
    data_package = {
        'event_name': event_name,
        'detector': detector,
        'strain': strain_processed.value,
        'times': strain_processed.times.value,
        'sample_rate': strain_processed.sample_rate.value,
        'merger_time': merger_time,
        'merger_idx': merger_idx,
        'final_mass': event_params['final_mass'],
        'final_spin': event_params['final_spin'],
        'quality_passed': passed,
        'event_params': event_params
    }
    
    # Save to file
    if save_to_file:
        filename = f"{event_name}_{detector}_processed.npz"
        np.savez(filename, **data_package)
        print(f"\n✓ Data saved to {filename}")
        print(f"  Load with: data = np.load('{filename}')")
    
    print(f"\n{'='*60}")
    print("Data preparation complete!")
    print(f"{'='*60}\n")
    
    return data_package


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description='Fetch and preprocess LIGO data for quantum ringdown analysis'
    )
    parser.add_argument(
        '--event', '-e',
        type=str,
        required=False,  # Changed to False
        choices=list(LIGO_EVENTS.keys()),
        help='Event name'
    )
    parser.add_argument(
        '--detector', '-d',
        type=str,
        default='H1',
        choices=['H1', 'L1', 'V1'],
        help='Detector name'
    )
    parser.add_argument(
        '--sample-rate', '-s',
        type=int,
        default=4096,
        help='Sample rate (Hz)'
    )
    parser.add_argument(
        '--list-events',
        action='store_true',
        help='List available events and exit'
    )
    
    args = parser.parse_args()
    
    # List events if requested
    if args.list_events:
        print("\nAvailable LIGO Events:")
        print("="*60)
        for name, params in LIGO_EVENTS.items():
            print(f"\n{name}:")
            print(f"  Final mass: {params['final_mass']:.1f} M☉")
            print(f"  Final spin: {params['final_spin']:.3f}")
            print(f"  Distance: {params['distance']} Mpc")
            if 'type' in params:
                print(f"  Type: {params['type']}")
        print()
        return
    
    # Check if event was provided
    if not args.event:
        parser.error("--event/-e is required (unless using --list-events)")
    
    # Check gwpy availability
    if not GWPY_AVAILABLE:
        print("\nERROR: gwpy not installed!")
        print("Install with: pip install gwpy")
        return
    
    # Prepare data
    data_package = prepare_event_for_analysis(
        args.event,
        args.detector,
        args.sample_rate
    )
    
    print("\nNext steps:")
    print("1. Load this data in quantum_ringdown_analysis.py")
    print("2. Run the analysis pipeline")
    print(f"3. Example code:")
    print(f"""
    import numpy as np
    from quantum_ringdown_analysis import analyze_single_event
    
    # Load data
    data = np.load('{args.event}_{args.detector}_processed.npz')
    
    # Run analysis
    results = analyze_single_event(
        strain=data['strain'],
        sample_rate=data['sample_rate'],
        merger_time=data['merger_idx'],  # use index, not GPS time
        final_mass=data['final_mass'],
        final_spin=data['final_spin'],
        event_name='{args.event}'
    )
    """)


if __name__ == '__main__':
    main()

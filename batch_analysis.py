#!/usr/bin/env python3
"""
Batch Analysis of Multiple LIGO Events
=======================================

This script runs the complete quantum gravity ringdown analysis
on multiple events and generates a comprehensive report.

Usage:
    python batch_analysis.py --events GW150914 GW151226 GW170814
    python batch_analysis.py --all  # analyze all available events
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
from datetime import datetime

# Import our analysis modules
from quantum_ringdown_analysis import (
    analyze_single_event,
    MultiEventStacker,
    plot_time_frequency_evolution,
    plot_multi_event_summary,
    TimeFrequencyAnalyzer
)

try:
    from ligo_data_fetcher import prepare_event_for_analysis, LIGO_EVENTS
    FETCHER_AVAILABLE = True
except ImportError:
    FETCHER_AVAILABLE = False
    print("WARNING: ligo_data_fetcher not available")


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def analyze_multiple_events(event_list, detector='H1', sample_rate=4096,
                            output_dir='analysis_results'):
    """
    Analyze multiple events in batch.
    
    Parameters:
    -----------
    event_list : list of str
        List of event names
    detector : str
        Detector to use
    sample_rate : int
        Sample rate
    output_dir : str
        Directory to save results
    
    Returns:
    --------
    stacker : MultiEventStacker
        Object containing all results
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"BATCH ANALYSIS: {len(event_list)} events")
    print(f"Output directory: {output_dir}")
    print(f"{'='*70}\n")
    
    # Initialize stacker
    stacker = MultiEventStacker()
    
    # Process each event
    all_results = []
    
    for i, event_name in enumerate(event_list, 1):
        print(f"\n{'#'*70}")
        print(f"Event {i}/{len(event_list)}: {event_name}")
        print(f"{'#'*70}")
        
        try:
            # Check if processed data already exists
            data_file = f"{event_name}_{detector}_processed.npz"
            
            if Path(data_file).exists():
                print(f"Loading existing processed data from {data_file}")
                data = np.load(data_file)
            elif FETCHER_AVAILABLE:
                print(f"Fetching and processing {event_name}...")
                data = prepare_event_for_analysis(
                    event_name, 
                    detector, 
                    sample_rate,
                    save_to_file=True
                )
            else:
                print(f"ERROR: No processed data found and fetcher unavailable")
                continue
            
            # Run analysis
            results = analyze_single_event(
                strain=data['strain'],
                sample_rate=float(data['sample_rate']),
                merger_time=int(data['merger_idx']),
                final_mass=float(data['final_mass']),
                final_spin=float(data['final_spin']),
                event_name=event_name
            )
            
            # Add to stacker
            stacker.add_event(
                event_name,
                float(data['final_mass']),
                float(data['final_spin']),
                results
            )
            
            all_results.append(results)
            
            # Save individual event plot
            print(f"\nGenerating plots for {event_name}...")
            tf_analyzer = TimeFrequencyAnalyzer(
                data['strain'],
                float(data['sample_rate']),
                int(data['merger_idx'])
            )
            
            plot_path = output_path / f"{event_name}_time_frequency.png"
            plot_time_frequency_evolution(
                tf_analyzer,
                t_start=0.0,
                t_end=0.02,
                expected_freq=results['f220_gr'],
                save_path=str(plot_path)
            )
            
            print(f"✓ Analysis complete for {event_name}")
            
        except Exception as e:
            print(f"✗ ERROR analyzing {event_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*70}")
    print(f"Batch analysis complete: {len(stacker.events)}/{len(event_list)} successful")
    print(f"{'='*70}\n")
    
    return stacker, all_results


def generate_comprehensive_report(stacker, output_dir='analysis_results'):
    """
    Generate comprehensive analysis report with plots and statistics.
    
    Parameters:
    -----------
    stacker : MultiEventStacker
        Results from all events
    output_dir : str
        Output directory
    """
    output_path = Path(output_dir)
    
    print("\n" + "="*70)
    print("GENERATING COMPREHENSIVE REPORT")
    print("="*70 + "\n")
    
    # 1. Text report
    print("1. Writing text report...")
    report = stacker.generate_summary_report()
    
    # Add theoretical context
    report += "\n" + "="*70 + "\n"
    report += "THEORETICAL INTERPRETATION\n"
    report += "="*70 + "\n\n"
    
    report += "Expected quantum gravity effects:\n"
    report += "-" * 50 + "\n"
    report += "1. Planck-scale cutoff (Gravitational Lattice Stretching):\n"
    report += "   - Frequency shift: δf/f ~ ξ(l_P/r_s)²\n"
    report += "   - For solar-mass BH: (l_P/r_s)² ~ 10⁻⁸⁰\n"
    report += "   - Detection requires ξ >> 10⁷⁰ (implausible)\n\n"
    
    report += "2. Loop Quantum Gravity corrections:\n"
    report += "   - Area quantization: A_min ~ γl_P²\n"
    report += "   - Primarily affects Planck-mass BHs\n"
    report += "   - For solar-mass: effect ~ 10⁻⁷⁶ (undetectable)\n\n"
    
    report += "3. Quantum horizon effects (echoes):\n"
    report += "   - Post-ringdown reflections\n"
    report += "   - Time delay ~ r_s/c ~ 0.1-1 ms\n"
    report += "   - Amplitude ~ 10⁻³ of main signal\n\n"
    
    # Statistical interpretation
    mean_dev, std_dev, combined_sig = stacker.compute_weighted_average('max_deviation')
    
    report += "="*70 + "\n"
    report += "STATISTICAL INTERPRETATION\n"
    report += "="*70 + "\n\n"
    
    if mean_dev is not None:
        if combined_sig < 2:
            interpretation = "NO EVIDENCE for quantum effects"
            confidence = "Results consistent with GR"
        elif combined_sig < 3:
            interpretation = "WEAK HINT (< 3σ)"
            confidence = "Insufficient evidence, needs more events"
        elif combined_sig < 5:
            interpretation = "SIGNIFICANT DEVIATION (3-5σ)"
            confidence = "Warrants further investigation"
        else:
            interpretation = "STRONG DEVIATION (> 5σ)"
            confidence = "Potential new physics or systematic error"
        
        report += f"Combined significance: {combined_sig:.2f}σ\n"
        report += f"Interpretation: {interpretation}\n"
        report += f"Confidence: {confidence}\n\n"
        
        # Check for unrealistic values
        if np.abs(mean_dev) > 0.5:  # > 50% deviation
            report += "⚠️  WARNING: Deviation > 50% is unrealistic for quantum gravity\n"
            report += "   This strongly suggests systematic error, not real physics.\n\n"
        
        if mean_dev != 0:
            # Estimate implied quantum parameter
            typical_mass = np.mean([e['mass'] for e in stacker.events])
            r_s = typical_mass * 2.95e3  # meters
            l_P = 1.616e-35  # meters
            
            xi_estimate = mean_dev / (l_P / r_s)**2
            
            report += f"If real, implied quantum parameter:\n"
            report += f"  ξ ~ {xi_estimate:.2e}\n"
            report += f"  (compared to theoretical expectation ~ 1)\n\n"
            
            if xi_estimate > 1e50 or np.abs(mean_dev) > 0.5:
                report += "⚠️  WARNING: Unrealistically large ξ or deviation suggests:\n"
                report += "   - Systematic error in analysis (most likely)\n"
                report += "   - Analysis method not suitable for this data\n"
                report += "   - Need to tune preprocessing parameters\n\n"
                report += "RECOMMENDATION: Treat as NULL RESULT.\n\n"
    
    # Save report
    report_path = output_path / "analysis_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"✓ Text report saved to {report_path}")
    
    # 2. Multi-event summary plot
    print("2. Generating summary plots...")
    plot_path = output_path / "multi_event_summary.png"
    plot_multi_event_summary(stacker, save_path=str(plot_path))
    
    # 3. JSON results for further analysis
    print("3. Saving JSON results...")
    json_data = {
        'analysis_date': datetime.now().isoformat(),
        'n_events': len(stacker.events),
        'events': []
    }
    
    for event in stacker.events:
        event_data = {
            'name': event['name'],
            'mass': float(event['mass']),
            'spin': float(event['spin']),
            'results': {}
        }
        
        # Extract serializable results
        for key, val in event['result'].items():
            if isinstance(val, (int, float, bool, str)):
                event_data['results'][key] = val
            elif isinstance(val, np.ndarray):
                event_data['results'][key] = val.tolist()
        
        json_data['events'].append(event_data)
    
    # Add combined statistics
    if mean_dev is not None:
        json_data['combined_statistics'] = {
            'weighted_mean_deviation': float(mean_dev),
            'weighted_std_deviation': float(std_dev),
            'combined_significance_sigma': float(combined_sig)
        }
    
    json_path = output_path / "analysis_results.json"
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"✓ JSON results saved to {json_path}")
    
    # 4. Create README
    print("4. Creating README...")
    readme = f"""
# Quantum Gravity Ringdown Analysis Results
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total events analyzed: {len(stacker.events)}
- Combined significance: {combined_sig:.2f}σ
- Interpretation: {interpretation if mean_dev is not None else 'N/A'}

## Files in this directory:
- `analysis_report.txt`: Detailed text report with statistics
- `multi_event_summary.png`: Summary plots for all events
- `analysis_results.json`: Machine-readable results
- `<event>_time_frequency.png`: Individual event time-frequency plots
- `<event>_<detector>_processed.npz`: Processed strain data

## How to interpret:
1. Check combined significance in `analysis_report.txt`
2. Look at `multi_event_summary.png` for visual overview
3. Examine individual event plots for anomalies
4. Compare with theoretical predictions in report

## Next steps:
- If significance < 3σ: No evidence for quantum effects
- If 3σ < significance < 5σ: Interesting but needs confirmation
- If significance > 5σ: Either new physics or systematic error!

## Theory:
This analysis searched for quantum gravity signatures in black hole
ringdown, specifically testing the "Gravitational Lattice Stretching"
hypothesis that predicts frequency anomalies due to Planck-scale
spatial cutoffs near the event horizon.

For more details, see the main analysis report.
"""
    
    readme_path = output_path / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme)
    print(f"✓ README saved to {readme_path}")
    
    print("\n" + "="*70)
    print("REPORT GENERATION COMPLETE")
    print(f"All results saved to: {output_dir}/")
    print("="*70 + "\n")
    
    # Print summary to console
    print(report)


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Batch analysis of LIGO events for quantum gravity signatures',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze specific events
  python batch_analysis.py --events GW150914 GW151226
  
  # Analyze all available events
  python batch_analysis.py --all
  
  # Specify detector and output directory
  python batch_analysis.py --all --detector L1 --output my_results
  
  # List available events
  python batch_analysis.py --list
        """
    )
    
    parser.add_argument(
        '--events', '-e',
        nargs='+',
        help='List of event names to analyze'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Analyze all available events (BBH only, excludes BNS)'
    )
    parser.add_argument(
        '--detector', '-d',
        default='H1',
        choices=['H1', 'L1', 'V1'],
        help='Detector to use (default: H1)'
    )
    parser.add_argument(
        '--sample-rate', '-s',
        type=int,
        default=4096,
        help='Sample rate in Hz (default: 4096)'
    )
    parser.add_argument(
        '--output', '-o',
        default='analysis_results',
        help='Output directory (default: analysis_results)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available events and exit'
    )
    
    args = parser.parse_args()
    
    # List events
    if args.list:
        if FETCHER_AVAILABLE:
            print("\nAvailable LIGO Events:")
            print("="*60)
            for name, params in LIGO_EVENTS.items():
                event_type = params.get('type', 'BBH')
                print(f"{name:12} | Mass: {params['final_mass']:6.1f} M☉ | "
                      f"Spin: {params['final_spin']:.3f} | Type: {event_type}")
            print()
        else:
            print("ERROR: ligo_data_fetcher not available")
        return
    
    # Determine event list
    if args.all:
        if not FETCHER_AVAILABLE:
            print("ERROR: --all requires ligo_data_fetcher module")
            return
        # Exclude BNS (GW170817) as theory is different
        event_list = [name for name, params in LIGO_EVENTS.items() 
                     if params.get('type', 'BBH') == 'BBH']
        print(f"Analyzing all {len(event_list)} BBH events")
    elif args.events:
        event_list = args.events
    else:
        parser.error("Must specify either --events or --all")
        return
    
    # Run batch analysis
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*15 + "QUANTUM RINGDOWN BATCH ANALYSIS" + " "*22 + "║")
    print("╚" + "═"*68 + "╝")
    
    stacker, results = analyze_multiple_events(
        event_list,
        detector=args.detector,
        sample_rate=args.sample_rate,
        output_dir=args.output
    )
    
    if len(stacker.events) > 0:
        generate_comprehensive_report(stacker, args.output)
        
        print("\n" + "🎉 "*20)
        print("ANALYSIS COMPLETE!")
        print("🎉 "*20)
        print(f"\nResults saved to: {args.output}/")
        print("Check analysis_report.txt for detailed findings.")
    else:
        print("\n❌ No events successfully analyzed!")


if __name__ == '__main__':
    main()

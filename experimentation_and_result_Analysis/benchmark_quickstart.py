"""
Benchmark Quickstart Examples
7 examples showing how to generate and work with framework benchmark comparison tables
"""

import json
from pathlib import Path
from framework_benchmark_comparison import FrameworkBenchmarkComparison, FrameworkMetrics
from benchmark_metrics_extractor import BenchmarkMetricsExtractor
from benchmark_report_generator import BenchmarkReportGenerator


def example_1_generate_all_tables():
    """Example 1: Generate all benchmark tables (TABLE IV-VII)"""
    print("\n" + "="*80)
    print("Example 1: Generate All Benchmark Tables")
    print("="*80)
    
    benchmark = FrameworkBenchmarkComparison()
    
    # Generate each table
    table_iv = benchmark.generate_time_consumption_table()
    table_v = benchmark.generate_crypto_overhead_table()
    table_vi = benchmark.generate_signature_overhead_table()
    table_vii = benchmark.generate_fairness_metrics_table()
    
    # Display summary
    print(f"✓ TABLE IV (Time Consumption): {table_iv['frameworks'].__len__()} frameworks")
    print(f"✓ TABLE V (Crypto Overhead): {table_v['frameworks'].__len__()} schemes")
    print(f"✓ TABLE VI (Digital Signature): {table_vi['frameworks'].__len__()} entries")
    print(f"✓ TABLE VII (Fairness Guarantees): {table_vii['frameworks'].__len__()} mechanisms")
    
    print("\nKEY FINDINGS:")
    print(f"  - HealChain total time: {table_iv['frameworks'][-1]['Total_Time_h']:.2f}h")
    print(f"  - HealChain accuracy: {table_iv['frameworks'][-1]['Accuracy_%']:.2f}%")
    print(f"  - Time vs ESB-FL: {table_iv['analysis']['healchain_vs_esb_fl']['time_improvement']:.2f}% improvement")


def example_2_save_json_tables():
    """Example 2: Save benchmark tables as JSON"""
    print("\n" + "="*80)
    print("Example 2: Save Benchmark Tables to JSON")
    print("="*80)
    
    benchmark = FrameworkBenchmarkComparison()
    output_file = benchmark.save_all_tables()
    
    print(f"✓ Saved: {output_file}")
    
    # Show file size
    file_size = output_file.stat().st_size / 1024
    print(f"✓ File size: {file_size:.1f} KB")
    
    # Load and display summary
    with open(output_file) as f:
        data = json.load(f)
    
    print(f"✓ Contains {len(data)} top-level sections")
    print(f"✓ Frameworks compared: {', '.join(data['metadata']['reference_frameworks'] + ['HealChain'])}")


def example_3_generate_ascii_tables():
    """Example 3: Generate ASCII-formatted tables for markdown"""
    print("\n" + "="*80)
    print("Example 3: Generate ASCII Tables for Markdown")
    print("="*80)
    
    benchmark = FrameworkBenchmarkComparison()
    ascii_output = benchmark.generate_ascii_tables()
    
    # Save to file
    output_file = Path('results') / 'benchmark_tables_ascii.txt'
    output_file.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ascii_output)
    
    print(f"✓ Saved ASCII tables to: {output_file}")
    print(f"✓ First 500 characters:\n")
    print(ascii_output[:500])
    print("...")


def example_4_extract_metrics_from_logs():
    """Example 4: Extract metrics from execution logs"""
    print("\n" + "="*80)
    print("Example 4: Extract Metrics from Execution Logs")
    print("="*80)
    
    extractor = BenchmarkMetricsExtractor()
    
    # Generate realistic demo data (simulating actual execution)
    print("Generating realistic HealChain execution metrics...")
    metrics_list = extractor.generate_realistic_distribution(num_tasks=5)
    
    # Aggregate
    aggregated = extractor.aggregate_metrics(metrics_list)
    
    # Display results
    print(f"\n✓ Extracted metrics from {aggregated['num_executions']} tasks")
    print(f"✓ Tasks: {', '.join(aggregated['task_ids'])}")
    print("\nPhase Timing Summary (hours):")
    for phase, timings in list(aggregated['phase_timings'].items())[:4]:
        print(f"  {phase:>10}: {timings['mean']:>6.2f}h ± {timings['stdev']:>5.2f}h")
    
    print(f"\nAccuracy: {aggregated['accuracy']['mean']:.2f}% "
          f"(range: {aggregated['accuracy']['min']:.2f}% - {aggregated['accuracy']['max']:.2f}%)")
    
    # Save metrics
    output_file = extractor.save_metrics(metrics_list)
    print(f"\n✓ Saved metrics to: {output_file}")


def example_5_generate_markdown_report():
    """Example 5: Generate comprehensive markdown report"""
    print("\n" + "="*80)
    print("Example 5: Generate Comprehensive Markdown Report")
    print("="*80)
    
    generator = BenchmarkReportGenerator()
    
    print("Generating markdown report with all tables and actual metrics...")
    markdown = generator.generate_markdown_report(include_actual_metrics=True, num_demo_tasks=3)
    
    # Save to file
    output_file = Path('results') / 'benchmark_report_sample.md'
    output_file.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"✓ Saved markdown report: {output_file}")
    print(f"✓ Report size: {len(markdown) / 1024:.1f} KB")
    print(f"✓ Contains: 6 main sections + 2 tables + analysis")
    
    # Show first 600 chars
    print(f"\nReport preview (first 600 chars):\n")
    print(markdown[:600])
    print("\n...")


def example_6_full_report_generation():
    """Example 6: Generate complete report (markdown + JSON) in one call"""
    print("\n" + "="*80)
    print("Example 6: Generate Complete Report (Markdown + JSON)")
    print("="*80)
    
    generator = BenchmarkReportGenerator()
    
    print("Generating complete benchmark report...")
    md_file, json_file = generator.create_full_report()
    
    print(f"✓ Markdown report: {md_file}")
    print(f"  └─ Use for: presentations, defense slides, documentation")
    
    print(f"\n✓ JSON report: {json_file}")
    print(f"  └─ Use for: data analysis, visualization, further processing")
    
    # Show summary
    with open(json_file) as f:
        data = json.load(f)
    
    print(f"\n✓ Report includes:")
    for key in data.keys():
        if key != 'metadata':
            print(f"  - {key}")


def example_7_custom_framework_comparison():
    """Example 7: Add custom framework and generate comparison"""
    print("\n" + "="*80)
    print("Example 7: Custom Framework Comparison")
    print("="*80)
    
    benchmark = FrameworkBenchmarkComparison()
    
    # Create a hypothetical "FutureChain" framework
    future_chain = FrameworkMetrics(
        framework_name='FutureChain (Hypothetical)',
        task_publishing=0.30,
        model_training=24.0,
        model_aggregation=10.0,
        consensus=0.05,
        total_time=34.35,
        accuracy=98.5,
        key_generation=0.15,
        encryption=15.0,
        inner_product=30.0,
        decryption=0.0,
        signature_overhead_avg=12.0,
        signature_overhead_std=0.02
    )
    
    print("Adding hypothetical 'FutureChain' framework...")
    benchmark.reference_data['FutureChain'] = future_chain
    
    # Compare HealChain vs FutureChain
    healchain = benchmark.generate_healchain_metrics()
    
    print(f"\nComparison with FutureChain:")
    print(f"  HealChain Total:     {healchain.total_time:.2f}h @ {healchain.accuracy:.2f}%")
    print(f"  FutureChain Total:   {future_chain.total_time:.2f}h @ {future_chain.accuracy:.2f}%")
    print(f"  FutureChain faster:  {healchain.total_time - future_chain.total_time:.2f}h (-{(healchain.total_time - future_chain.total_time)/healchain.total_time*100:.1f}%)")
    print(f"  FutureChain more accurate: {future_chain.accuracy - healchain.accuracy:.2f}%")
    
    print("\nNote: This example shows how to extend the framework comparison")
    print("      with your own custom implementation metrics")


def example_8_integration_with_actual_data():
    """Example 8: Integration pattern - use with actual task results"""
    print("\n" + "="*80)
    print("Example 8: Integration with Actual Task Results")
    print("="*80)
    
    print("Pattern 1: If you have task_037_results.json with actual predictions:")
    print("""
    import json
    import numpy as np
    from benchmark_report_generator import BenchmarkReportGenerator
    
    # Load actual task results
    with open('backend/task_037_results.json') as f:
        actual_data = json.load(f)
    
    # Extract metrics
    y_true = np.array(actual_data['ground_truth'])
    y_pred = np.array(actual_data['predictions'])
    actual_accuracy = np.mean(y_true == y_pred)
    
    # Use in benchmark comparison
    generator = BenchmarkReportGenerator()
    md_report = generator.generate_markdown_report(include_actual_metrics=True)
    """)
    
    print("\nPattern 2: If you have execution logs (plaintext with [INFO] markers):")
    print("""
    from benchmark_metrics_extractor import BenchmarkMetricsExtractor
    from pathlib import Path
    
    extractor = BenchmarkMetricsExtractor()
    
    # Parse your execution log
    metrics = extractor.extract_from_execution_log(
        Path('execution_logs/task_037_log.txt')
    )
    
    # Aggregate with other tasks
    all_metrics = [metrics]  # Add more...
    aggregated = extractor.aggregate_metrics(all_metrics)
    """)
    
    print("\nPattern 3: Generate report with your actual metrics:")
    print("""
    from benchmark_report_generator import BenchmarkReportGenerator
    
    generator = BenchmarkReportGenerator()
    md_file, json_file = generator.create_full_report(
        include_actual_metrics=True  # Uses actual extracted metrics
    )
    """)


def run_all_examples():
    """Run all examples sequentially"""
    print("\n" + "="*80)
    print("HEALCHAIN BENCHMARK QUICKSTART - ALL EXAMPLES")
    print("="*80)
    
    examples = [
        ("Generate All Tables", example_1_generate_all_tables),
        ("Save JSON Tables", example_2_save_json_tables),
        ("Generate ASCII Tables", example_3_generate_ascii_tables),
        ("Extract Metrics", example_4_extract_metrics_from_logs),
        ("Generate Markdown Report", example_5_generate_markdown_report),
        ("Generate Complete Report", example_6_full_report_generation),
        ("Custom Framework", example_7_custom_framework_comparison),
        ("Integration Patterns", example_8_integration_with_actual_data),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        try:
            func()
            print(f"\n✓ Example {i} completed: {name}")
        except Exception as e:
            print(f"\n✗ Example {i} error: {e}")


CONFIG_TEMPLATE = """
# Benchmark Configuration Template

To customize benchmark comparison:

1. **Add reference frameworks** in framework_benchmark_comparison.py:
   ```python
   custom_fw = FrameworkMetrics(
       framework_name='MyFramework',
       task_publishing=0.3,
       model_training=24.0,
       # ... other metrics
   )
   benchmark.reference_data['MyFramework'] = custom_fw
   ```

2. **Configure extraction** in benchmark_metrics_extractor.py:
   ```python
   extractor = BenchmarkMetricsExtractor(logs_dir=Path('my_logs'))
   metrics = extractor.extract_from_execution_log(log_file)
   ```

3. **Customize report** in benchmark_report_generator.py:
   ```python
   generator = BenchmarkReportGenerator(output_dir=Path('my_reports'))
   md_file, json_file = generator.create_full_report(
       output_prefix='my_benchmark',
       include_actual_metrics=True
   )
   ```

4. **Choose comparison frameworks** - modify:
   frameworks_to_compare = ['FL', 'ESFL', 'ESB-FL', 'PBFL', 'BSR-FL', 'HealChain']
"""


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        
        examples = {
            '1': example_1_generate_all_tables,
            '2': example_2_save_json_tables,
            '3': example_3_generate_ascii_tables,
            '4': example_4_extract_metrics_from_logs,
            '5': example_5_generate_markdown_report,
            '6': example_6_full_report_generation,
            '7': example_7_custom_framework_comparison,
            '8': example_8_integration_with_actual_data,
            'all': run_all_examples,
            'config': lambda: print(CONFIG_TEMPLATE)
        }
        
        if example_num in examples:
            examples[example_num]()
        else:
            print(f"Unknown example: {example_num}")
            print(f"Available: {', '.join(examples.keys())}")
    else:
        # Run example 6 by default (complete report)
        print("Running Example 6: Generate Complete Report (default)")
        print("Usage: python benchmark_quickstart.py [1-8|all|config]")
        print("")
        example_6_full_report_generation()

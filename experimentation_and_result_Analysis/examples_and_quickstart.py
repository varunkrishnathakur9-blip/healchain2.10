"""
Quick-Start Examples for HealChain Experimentation Suite
Copy and adapt these examples for your own tasks
"""

import numpy as np
import json
from pathlib import Path
from main_driver import HealChainExperimentationDriver
from confusion_matrix_generator import ConfusionMatrixGenerator, create_sample_task_confusion_matrix
from batch_analysis_suite import BatchConfusionMatrixAnalysis


# ============================================================================
# EXAMPLE 1: Single Task with Sample Data (Quickest Start)
# ============================================================================

def example_single_task_demo():
    """Simplest example - generates demo confusion matrix"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Single Task Demo")
    print("="*70)
    
    # Create sample data (simulates task_037 results)
    gen = create_sample_task_confusion_matrix(
        task_id='task_037',
        num_samples=1000,
        accuracy=0.952
    )
    
    # Generate and display
    report = gen.generate_report()
    print(f"\n✓ Task: {report['metadata']['task_id']}")
    print(f"✓ Accuracy: {report['classification_metrics']['accuracy']:.2%}")
    print(f"✓ Privacy: {report['privacy_validation']['privacy_mechanisms']}")
    
    # Save outputs
    gen.save_report()
    gen.plot_confusion_matrix()


# ============================================================================
# EXAMPLE 2: Your Actual Task Results
# ============================================================================

def example_with_actual_predictions():
    """Use your actual task predictions"""
    print("\n" + "="*70)
    print("EXAMPLE 2: With Your Actual Task Predictions")
    print("="*70)
    
    # TODO: Replace these with your actual predictions
    y_true = [0, 1, 2, 1, 0, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5]  # Ground truth
    y_pred = [0, 1, 2, 1, 0, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5]  # Model predictions
    
    # Create generator
    gen = ConfusionMatrixGenerator(task_id='task_037_actual', num_classes=10)
    gen.add_predictions(np.array(y_true), np.array(y_pred))
    
    # Set privacy metrics from your actual execution
    gen.set_privacy_metrics({
        'gradients_encrypted': True,
        'encryption_algorithm': 'NDD-FE',
        'gradient_compression_ratio': 0.15,  # Actual DGC compression
        'bandwidth_reduction': 85,
        'key_derivation_method': 'deterministic_hash',
        'aggregator_key_secured': True,
        'miners_involved': 4
    })
    
    # Generate outputs
    report = gen.generate_report()
    gen.save_report(Path('results'))
    gen.plot_confusion_matrix(Path('visualizations'))
    
    print(f"\n✓ Accuracy: {report['classification_metrics']['accuracy']:.2%}")
    print(f"✓ Predictions: {len(y_pred)}")


# ============================================================================
# EXAMPLE 3: Load from JSON File (Backend Integration)
# ============================================================================

def example_from_json_file():
    """Load predictions from backend JSON file"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Load from JSON File")
    print("="*70)
    
    # Create sample JSON (simulating backend output)
    sample_data = {
        'task_id': 'task_037',
        'predictions': [0, 1, 2, 1, 0, 3, 4, 5, 6, 7, 8, 9],
        'ground_truth': [0, 1, 2, 1, 0, 3, 4, 5, 6, 7, 8, 9],
        'accuracy': 0.952,
        'consensus_passed': True,
        'miners_involved': 4,
        'privacy_metrics': {
            'gradients_encrypted': True,
            'encryption_algorithm': 'NDD-FE',
            'gradient_compression_ratio': 0.15,
            'bandwidth_reduction': 85
        }
    }
    
    # Save sample JSON
    json_file = Path('sample_task_results.json')
    with open(json_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    # Load and process
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    gen = ConfusionMatrixGenerator(
        task_id=data['task_id'],
        num_classes=10
    )
    gen.add_predictions(
        np.array(data['ground_truth']),
        np.array(data['predictions'])
    )
    gen.set_privacy_metrics(data.get('privacy_metrics', {}))
    
    print(f"\n✓ Loaded: {data['task_id']}")
    print(f"✓ Accuracy: {data['accuracy']:.2%}")
    print(f"✓ Encrypted: {data['privacy_metrics']['gradients_encrypted']}")
    
    # Cleanup
    json_file.unlink()


# ============================================================================
# EXAMPLE 4: Batch Processing Multiple Tasks
# ============================================================================

def example_batch_processing():
    """Process multiple tasks (task_037, 038, 039)"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Batch Processing Multiple Tasks")
    print("="*70)
    
    # Prepare multiple tasks
    task_configs = []
    
    for i, task_id in enumerate(['task_037', 'task_038', 'task_039']):
        np.random.seed(42 + i)
        
        # Generate sample predictions
        y_true = np.random.randint(0, 10, 500)
        y_pred = y_true.copy()
        
        # Introduce some errors
        errors = np.random.choice(500, 25, replace=False)
        for e in errors:
            y_pred[e] = (y_pred[e] + 1) % 10
        
        task_configs.append({
            'task_id': task_id,
            'y_true': y_true,
            'y_pred': y_pred,
            'privacy_metrics': {
                'gradients_encrypted': True,
                'encryption_algorithm': 'NDD-FE',
                'gradient_compression_ratio': 0.15,
                'bandwidth_reduction': 85
            },
            'num_classes': 10
        })
    
    # Run batch analysis
    batch = BatchConfusionMatrixAnalysis(
        task_ids=[c['task_id'] for c in task_configs],
        output_dir=Path('batch_results')
    )
    
    for config in task_configs:
        batch.process_task(
            config['task_id'],
            config['y_true'],
            config['y_pred'],
            config.get('privacy_metrics', {}),
            config.get('num_classes', 10)
        )
    
    # Generate reports
    analysis = batch.generate_comparative_analysis()
    batch.save_comparative_report()
    batch.generate_visual_comparison()
    batch.generate_all_individual_matrices()
    
    print(f"\n✓ Tasks processed: {len(task_configs)}")
    print(f"✓ Mean accuracy: {analysis['summary_statistics']['mean_accuracy']:.2%}")
    print(f"✓ Encryption rate: {analysis['summary_statistics']['encryption_rate']:.0%}")
    print(f"✓ Output directory: batch_results/")


# ============================================================================
# EXAMPLE 5: Using the Main Driver (Full Orchestration)
# ============================================================================

def example_main_driver():
    """Use HealChainExperimentationDriver for complete automation"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Main Driver - Full Orchestration")
    print("="*70)
    
    # Initialize driver
    driver = HealChainExperimentationDriver(Path('experimentation_results'))
    
    # Process single task
    np.random.seed(42)
    y_true = np.random.randint(0, 10, 1000)
    y_pred = y_true.copy()
    errors = np.random.choice(1000, 50, replace=False)
    for e in errors:
        y_pred[e] = (y_pred[e] + 1) % 10
    
    result = driver.run_single_task_analysis(
        task_id='task_037',
        y_true=y_true,
        y_pred=y_pred,
        privacy_metrics={
            'gradients_encrypted': True,
            'encryption_algorithm': 'NDD-FE',
            'gradient_compression_ratio': 0.15,
            'bandwidth_reduction': 85
        }
    )
    
    print(f"\n✓ Single task result: {result['accuracy']:.2%}")
    print(f"✓ Report: {result['report_file']}")
    print(f"✓ Plot: {result['plot_file']}")
    
    # Generate comprehensive report
    report_file = driver.generate_comprehensive_report(
        experiment_name="HealChain Task Execution",
        description="Privacy-preserving federated learning with blockchain verification",
        tasks_data=[result]
    )
    
    print(f"\n✓ Comprehensive report: {report_file}")


# ============================================================================
# EXAMPLE 6: Extract from Backend Logs
# ============================================================================

def example_extract_from_logs():
    """Extract task results from backend logs"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Extract from Backend Logs")
    print("="*70)
    
    from task_results_extractor import TaskResultsExtractor
    
    # Create sample log file
    sample_log = {
        'task_id': 'task_037',
        'predictions': [0, 1, 2, 1, 0, 3, 4, 5, 6, 7, 8, 9],
        'actual_labels': [0, 1, 2, 1, 0, 3, 4, 5, 6, 7, 8, 9],
        'accuracy': 0.952,
        'consensus_passed': True,
        'miners_involved': 4
    }
    
    log_file = Path('sample_verification.log')
    with open(log_file, 'w') as f:
        json.dump(sample_log, f)
    
    # Extract results
    extractor = TaskResultsExtractor(Path('.'))
    task_data = extractor.extract_from_verification_logs('task_037', log_file)
    
    if task_data:
        print(f"\n✓ Extracted task: {task_data.task_id}")
        print(f"✓ Accuracy: {task_data.accuracy:.2%}")
        print(f"✓ Predictions: {len(task_data.predictions)}")
    
    # Cleanup
    log_file.unlink()


# ============================================================================
# EXAMPLE 7: Custom Multi-Class Classification (Medical)
# ============================================================================

def example_medical_classification():
    """Medical classification example (bacteria/normal/virus)"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Medical Classification - Like Base Paper")
    print("="*70)
    
    # Medical classification (3 classes: bacteria, normal, virus)
    class_names = ['bacteria', 'normal', 'virus']
    
    # Sample predictions (simulate actual medical imaging classification)
    y_true = np.array([0]*370 + [1]*328 + [2]*287)  # Ground truth
    y_pred = np.array([0]*370 + [0]*9 + [0]*6 +     # Actual predictions
                      [1]*14 + [1]*306 + [1]*8 +
                      [2]*7 + [2]*10 + [2]*270)
    
    # Generate confusion matrix
    gen = ConfusionMatrixGenerator(
        task_id='medical_task_001',
        num_classes=3,
        class_names=class_names
    )
    
    gen.add_predictions(y_true, y_pred)
    gen.set_privacy_metrics({
        'gradients_encrypted': True,
        'encryption_algorithm': 'NDD-FE',
        'gradient_compression_ratio': 0.15,
        'bandwidth_reduction': 85,
        'key_derivation_method': 'deterministic_hash',
        'privacy_guarantee': 'Gradient recovery probability 2^-256'
    })
    
    # Generate outputs
    report = gen.generate_report()
    gen.save_report(Path('medical_results'))
    gen.plot_confusion_matrix(Path('medical_results'))
    
    print(f"\n✓ Medical classification results:")
    print(f"✓ Classes: {', '.join(class_names)}")
    print(f"✓ Accuracy: {report['classification_metrics']['accuracy']:.2%}")
    print(f"✓ Privacy: NDD-FE encrypted (256-bit security)")
    print(f"✓ Saved to: medical_results/")


# ============================================================================
# Configuration Template (Fill This In)
# ============================================================================

CONFIG_TEMPLATE = {
    'experiment': {
        'name': 'HealChain Task Execution',
        'description': 'Privacy-preserving federated learning with blockchain verification'
    },
    'tasks': [
        {
            'task_id': 'task_037',
            'y_true_file': 'path/to/ground_truth.npy',
            'y_pred_file': 'path/to/predictions.npy',
            'num_classes': 10,
            'privacy_metrics': {
                'gradients_encrypted': True,
                'encryption_algorithm': 'NDD-FE',
                'gradient_compression_ratio': 0.15,
                'bandwidth_reduction': 85
            }
        },
        # Add more tasks here
    ],
    'output_dir': 'experimentation_results'
}


# ============================================================================
# Main: Run All Examples
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("HealChain Experimentation Suite - Quick-Start Examples")
    print("="*70)
    
    examples = [
        ("Demo (Fastest)", example_single_task_demo),
        ("With Actual Predictions", example_with_actual_predictions),
        ("From JSON File", example_from_json_file),
        ("Batch Processing", example_batch_processing),
        ("Main Driver (Full)", example_main_driver),
        ("Extract from Logs", example_extract_from_logs),
        ("Medical Classification", example_medical_classification),
    ]
    
    print("\nAvailable examples:")
    for i, (name, func) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning Example 1 (fastest demo)...")
    example_single_task_demo()
    
    print("\n" + "="*70)
    print("✓ Examples complete! Check output files in:")
    print("  - results/")
    print("  - visualizations/")
    print("  - experimentation_results/")
    print("="*70 + "\n")

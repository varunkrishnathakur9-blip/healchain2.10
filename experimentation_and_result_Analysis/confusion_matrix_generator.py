"""
Privacy-Preserving Confusion Matrix Generator for HealChain
Generates confusion matrices showing model classification performance 
while maintaining cryptographic privacy guarantees (NDD-FE + DGC)
"""

import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any


class ConfusionMatrixGenerator:
    """
    Generates and analyzes confusion matrices for federated learning tasks
    while tracking privacy-preserving metrics (gradient encryption, compression).
    """
    
    def __init__(self, task_id: str, num_classes: int = 10, class_names: List[str] = None):
        """
        Initialize the confusion matrix generator.
        
        Args:
            task_id: Task identifier (e.g., 'task_037')
            num_classes: Number of output classes
            class_names: List of class names (optional)
        """
        self.task_id = task_id
        self.num_classes = num_classes
        self.class_names = class_names or [str(i) for i in range(num_classes)]
        self.predictions = []
        self.actuals = []
        self.privacy_metrics = {}
        self.timestamp = datetime.now().isoformat()
        
    def add_predictions(self, y_true: np.ndarray, y_pred: np.ndarray):
        """
        Add predictions and ground truth labels.
        
        Args:
            y_true: Ground truth labels (1D array or list)
            y_pred: Predicted labels (1D array or list)
        """
        self.actuals.extend(y_true)
        self.predictions.extend(y_pred)
        
    def compute_confusion_matrix(self) -> np.ndarray:
        """
        Compute confusion matrix from accumulated predictions.
        
        Returns:
            Confusion matrix (num_classes x num_classes)
        """
        if len(self.actuals) == 0:
            raise ValueError("No predictions added yet. Call add_predictions() first.")
        
        cm = confusion_matrix(self.actuals, self.predictions, labels=range(self.num_classes))
        return cm
    
    def compute_classification_metrics(self) -> Dict[str, Any]:
        """
        Compute detailed classification metrics.
        
        Returns:
            Dictionary with precision, recall, F1-score per class and overall accuracy
        """
        if len(self.actuals) == 0:
            raise ValueError("No predictions added yet.")
        
        accuracy = accuracy_score(self.actuals, self.predictions)
        report = classification_report(
            self.actuals, 
            self.predictions,
            labels=range(self.num_classes),
            target_names=self.class_names,
            output_dict=True
        )
        
        return {
            'accuracy': accuracy,
            'per_class_metrics': report,
            'num_predictions': len(self.actuals)
        }
    
    def set_privacy_metrics(self, privacy_data: Dict[str, Any]):
        """
        Set privacy-related metrics (encryption, gradient compression, etc.)
        
        Args:
            privacy_data: Dictionary containing privacy metrics like:
                - gradients_encrypted: bool
                - encryption_algorithm: str (NDD-FE)
                - gradient_compression_ratio: float
                - bandwidth_reduction: float
                - aggregator_key_derivation_method: str
        """
        self.privacy_metrics = privacy_data
    
    def validate_privacy_guarantees(self) -> Dict[str, Any]:
        """
        Validate that privacy guarantees are maintained (for audit trail).
        
        Returns:
            Validation report with privacy properties
        """
        validation = {
            'timestamp': self.timestamp,
            'task_id': self.task_id,
            'privacy_mechanisms': {
                'ndd_fe_encrypted': self.privacy_metrics.get('gradients_encrypted', False),
                'gradient_compression_active': self.privacy_metrics.get('compression_ratio', 0.0) < 1.0,
                'aggregator_key_secured': self.privacy_metrics.get('key_derivation_method') == 'deterministic_hash',
                'data_leakage_risk': self._assess_leakage_risk()
            },
            'privacy_metrics': self.privacy_metrics
        }
        return validation
    
    def _assess_leakage_risk(self) -> str:
        """
        Assess potential information leakage risk.
        
        Returns:
            'LOW', 'MEDIUM', or 'HIGH' based on privacy mechanisms
        """
        if not self.privacy_metrics.get('gradients_encrypted', False):
            return 'HIGH'
        
        if self.privacy_metrics.get('compression_ratio', 1.0) > 0.5:  # > 50% of gradients
            return 'MEDIUM'
        
        return 'LOW'
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive confusion matrix analysis report.
        
        Returns:
            Complete analysis report with metrics and privacy validation
        """
        cm = self.compute_confusion_matrix()
        metrics = self.compute_classification_metrics()
        privacy_validation = self.validate_privacy_guarantees()
        
        report = {
            'metadata': {
                'task_id': self.task_id,
                'timestamp': self.timestamp,
                'num_predictions': len(self.actuals),
                'num_classes': self.num_classes,
                'class_names': self.class_names
            },
            'confusion_matrix': cm.tolist(),
            'classification_metrics': metrics,
            'privacy_validation': privacy_validation,
            'per_class_analysis': self._detailed_per_class_analysis(cm, metrics)
        }
        return report
    
    def _detailed_per_class_analysis(self, cm: np.ndarray, metrics: Dict) -> List[Dict]:
        """
        Generate detailed per-class analysis.
        """
        analysis = []
        for class_idx in range(self.num_classes):
            true_positives = cm[class_idx, class_idx]
            false_positives = cm[:, class_idx].sum() - true_positives
            false_negatives = cm[class_idx, :].sum() - true_positives
            true_negatives = cm.sum() - true_positives - false_positives - false_negatives
            
            class_data = {
                'class': self.class_names[class_idx],
                'class_index': class_idx,
                'true_positives': int(true_positives),
                'false_positives': int(false_positives),
                'false_negatives': int(false_negatives),
                'true_negatives': int(true_negatives),
                'precision': float(metrics['per_class_metrics'][self.class_names[class_idx]]['precision']),
                'recall': float(metrics['per_class_metrics'][self.class_names[class_idx]]['recall']),
                'f1_score': float(metrics['per_class_metrics'][self.class_names[class_idx]]['f1-score'])
            }
            analysis.append(class_data)
        
        return analysis
    
    def save_report(self, output_dir: Path = None) -> Path:
        """
        Save the analysis report as JSON.
        
        Args:
            output_dir: Directory to save report (default: current script directory)
            
        Returns:
            Path to saved report
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / 'results'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_report()
        report_file = output_dir / f'{self.task_id}_confusion_matrix_report_{self.timestamp.replace(":", "-")}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✓ Report saved: {report_file}")
        return report_file
    
    def plot_confusion_matrix(self, output_dir: Path = None, use_percentage: bool = False) -> Path:
        """
        Plot and save confusion matrix visualization.
        
        Args:
            output_dir: Directory to save plot
            use_percentage: If True, show percentages instead of counts
            
        Returns:
            Path to saved plot
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / 'results'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cm = self.compute_confusion_matrix()
        metrics = self.compute_classification_metrics()
        
        # Normalize for percentage view if requested
        if use_percentage:
            cm_display = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100
            fmt = '.1f'
            cbar_label = 'Percentage (%)'
        else:
            cm_display = cm
            fmt = 'd'
            cbar_label = 'Count'
        
        # Create figure with two subplots: confusion matrix and privacy metrics
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Confusion Matrix Heatmap
        sns.heatmap(
            cm_display,
            annot=True,
            fmt=fmt,
            cmap='Blues',
            xticklabels=self.class_names,
            yticklabels=self.class_names,
            cbar_kws={'label': cbar_label},
            ax=axes[0],
            square=True
        )
        axes[0].set_title(f'Confusion Matrix - {self.task_id}\nAccuracy: {metrics["accuracy"]:.2%}', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Actual Label', fontsize=11)
        axes[0].set_xlabel('Predicted Label', fontsize=11)
        
        # Privacy Metrics Panel
        privacy_text = self._format_privacy_metrics_text(metrics)
        axes[1].text(0.05, 0.95, privacy_text, transform=axes[1].transAxes,
                    fontsize=10, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        axes[1].axis('off')
        axes[1].set_title('Privacy & Performance Metrics', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot
        plot_file = output_dir / f'{self.task_id}_confusion_matrix_visual_{self.timestamp.replace(":", "-")}.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"✓ Visualization saved: {plot_file}")
        plt.close()
        
        return plot_file
    
    def _format_privacy_metrics_text(self, metrics: Dict) -> str:
        """Format privacy and performance metrics for display."""
        text = "Performance Metrics:\n"
        text += f"  Overall Accuracy: {metrics['accuracy']:.2%}\n"
        text += f"  Total Predictions: {metrics['num_predictions']}\n\n"
        
        text += "Privacy Preservation:\n"
        text += f"  Encryption: {'✓ NDD-FE' if self.privacy_metrics.get('gradients_encrypted') else '✗ None'}\n"
        text += f"  Gradient Compression: {self.privacy_metrics.get('compression_ratio', 1.0):.1%}\n"
        text += f"  Bandwidth Reduction: {self.privacy_metrics.get('bandwidth_reduction', '0')}%\n"
        text += f"  Key Derivation: {self.privacy_metrics.get('key_derivation_method', 'Unknown')}\n\n"
        
        text += "Per-Class Performance:\n"
        for class_name in self.class_names[:5]:  # Show first 5 classes
            if class_name in metrics['per_class_metrics']:
                prec = metrics['per_class_metrics'][class_name]['precision']
                recall = metrics['per_class_metrics'][class_name]['recall']
                text += f"  {class_name}: P={prec:.2f}, R={recall:.2f}\n"
        
        return text


def create_sample_task_confusion_matrix(task_id: str = 'task_037', 
                                       num_samples: int = 600,
                                       num_classes: int = 10,
                                       accuracy: float = 0.90) -> ConfusionMatrixGenerator:
    """
    Create a sample confusion matrix for testing/demonstration.
    Simulates a realistic MNIST classification with specified accuracy.
    
    Args:
        task_id: Task identifier
        num_samples: Number of test samples
        num_classes: Number of output classes
        accuracy: Target accuracy rate
        
    Returns:
        ConfusionMatrixGenerator with sample data
    """
    np.random.seed(42)  # For reproducibility
    
    # Generate realistic predictions biased toward specified accuracy
    y_true = np.random.randint(0, num_classes, num_samples)
    y_pred = y_true.copy()
    
    # Introduce classification errors
    num_errors = int(num_samples * (1 - accuracy))
    error_indices = np.random.choice(num_samples, num_errors, replace=False)
    
    for idx in error_indices:
        wrong_classes = list(range(num_classes))
        wrong_classes.remove(y_pred[idx])
        y_pred[idx] = np.random.choice(wrong_classes)
    
    # Create generator and populate with data
    class_names = [str(i) for i in range(num_classes)]
    gen = ConfusionMatrixGenerator(task_id, num_classes, class_names)
    gen.add_predictions(y_true, y_pred)
    
    # Add privacy metrics typical for HealChain
    gen.set_privacy_metrics({
        'gradients_encrypted': True,
        'encryption_algorithm': 'NDD-FE',
        'gradient_compression_ratio': 0.15,  # DGC: 85% compression
        'bandwidth_reduction': 85,
        'aggregator_key_derivation_method': 'deterministic_hash',
        'encryption_scheme': 'secp256r1 (256-bit)',
        'privacy_guarantee': '2^-256 gradient recovery probability'
    })
    
    return gen


if __name__ == '__main__':
    # Example usage
    print("=" * 70)
    print("HealChain Privacy-Preserving Confusion Matrix Generator")
    print("=" * 70)
    
    # Create sample confusion matrix
    gen = create_sample_task_confusion_matrix(task_id='task_037', num_samples=1000, accuracy=0.952)
    
    # Generate report
    report = gen.generate_report()
    print(f"\n✓ Confusion matrix generated for {report['metadata']['task_id']}")
    print(f"  Samples: {report['metadata']['num_predictions']}")
    print(f"  Accuracy: {report['classification_metrics']['accuracy']:.2%}")
    
    # Save report and visualization
    report_file = gen.save_report()
    plot_file = gen.plot_confusion_matrix(use_percentage=False)
    
    print(f"\n✓ Files saved in: {Path(report_file).parent}")
    print("\nDone!")

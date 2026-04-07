"""
Task Results Extractor for HealChain
Extracts verification results, predictions, and privacy metrics from task execution logs
and prepares data for confusion matrix generation.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import asdict, dataclass
from datetime import datetime
import re


@dataclass
class TaskExecutionData:
    """Container for extracted task execution data."""
    task_id: str
    module_phase: str  # M1-M7
    timestamp: str
    predictions: List[int]
    ground_truth: List[int]
    accuracy: float
    model_predictions_artifact: str  # IPFS link or local path
    privacy_metrics: Dict[str, Any]
    miners_involved: int
    escrow_amount: float
    consensus_votes: int
    consensus_passed: bool
    

class TaskResultsExtractor:
    """
    Extracts model predictions and privacy metrics from task execution.
    Interfaces with backend database, aggregator logs, and blockchain records.
    """
    
    def __init__(self, task_output_dir: Path):
        """
        Initialize extractor with task outputs directory.
        
        Args:
            task_output_dir: Path containing task artifacts (logs, models, results)
        """
        self.task_output_dir = Path(task_output_dir)
        self.extracted_data: Dict[str, TaskExecutionData] = {}
        
    def extract_from_verification_logs(self, task_id: str, log_file: Path) -> Optional[TaskExecutionData]:
        """
        Extract predictions and accuracy from verification module logs (M5/M6).
        
        Args:
            task_id: Task identifier
            log_file: Path to verification log file
            
        Returns:
            TaskExecutionData or None if extraction fails
        """
        try:
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Parse JSON verification results if available
            if content.strip().startswith('{'):
                data = json.loads(content)
                return self._parse_verification_json(task_id, data)
            else:
                # Parse text-based logs
                return self._parse_verification_text(task_id, content)
        except Exception as e:
            print(f"  ✗ Failed to extract from {log_file}: {e}")
            return None
    
    def extract_from_model_artifact(self, task_id: str, model_file: Path) -> Optional[Tuple[List[int], float]]:
        """
        Extract predictions from saved model predictions file.
        
        Args:
            task_id: Task identifier
            model_file: Path to model predictions JSON
            
        Returns:
            Tuple of (predictions, accuracy) or None
        """
        try:
            with open(model_file, 'r') as f:
                data = json.load(f)
            
            predictions = data.get('predictions', [])
            accuracy = data.get('accuracy', 0.0)
            
            return predictions, accuracy
        except Exception as e:
            print(f"  ✗ Failed to extract model artifact {model_file}: {e}")
            return None
    
    def extract_from_database_results(self, task_queries: Dict[str, str], 
                                     db_backend: Optional[Any] = None) -> Dict[str, TaskExecutionData]:
        """
        Extract task results by querying backend database via JSON query results.
        
        Args:
            task_queries: Dictionary of task_id -> query result JSON
            db_backend: Optional database connection object
            
        Returns:
            Dictionary of task_id -> TaskExecutionData
        """
        results = {}
        
        for task_id, query_result in task_queries.items():
            try:
                if isinstance(query_result, str):
                    data = json.loads(query_result)
                else:
                    data = query_result
                
                task_data = self._parse_db_query_result(task_id, data)
                if task_data:
                    results[task_id] = task_data
            except Exception as e:
                print(f"  ✗ Failed to parse DB result for {task_id}: {e}")
        
        return results
    
    def extract_privacy_metrics_from_logs(self, task_id: str, aggregator_log: Path) -> Dict[str, Any]:
        """
        Extract privacy metrics (NDD-FE, DGC compression) from aggregator logs.
        
        Args:
            task_id: Task identifier
            aggregator_log: Path to aggregator execution log
            
        Returns:
            Dictionary of privacy metrics
        """
        metrics = {
            'gradients_encrypted': False,
            'compression_ratio': 1.0,
            'bandwidth_reduction': 0,
            'key_derivation_method': 'unknown',
            'bsgs_recovery_time': 0,
            'miners_involved': 0
        }
        
        try:
            with open(aggregator_log, 'r') as f:
                content = f.read()
            
            # Parse encryption status
            if 'NDD-FE' in content or 'encrypted' in content.lower():
                metrics['gradients_encrypted'] = True
            
            # Extract compression ratio
            compression_match = re.search(r'compression[_\s]*ratio[:\s]*(\d+\.?\d*)', content, re.IGNORECASE)
            if compression_match:
                metrics['compression_ratio'] = float(compression_match.group(1))
            
            # Extract bandwidth reduction
            bandwidth_match = re.search(r'bandwidth[_\s]*reduction[:\s]*(\d+)%?', content, re.IGNORECASE)
            if bandwidth_match:
                metrics['bandwidth_reduction'] = int(bandwidth_match.group(1))
            
            # Extract BSGS recovery time
            bsgs_match = re.search(r'BSGS[_\s]*recovery[_\s]*time[:\s]*(\d+\.?\d*)', content, re.IGNORECASE)
            if bsgs_match:
                metrics['bsgs_recovery_time'] = float(bsgs_match.group(1))
            
            # Extract miners count
            miners_match = re.search(r'miners[_\s]*involved[:\s]*(\d+)', content, re.IGNORECASE)
            if miners_match:
                metrics['miners_involved'] = int(miners_match.group(1))
            
            metrics['key_derivation_method'] = 'deterministic_hash'
            
        except Exception as e:
            print(f"  ✗ Failed to extract privacy metrics: {e}")
        
        return metrics
    
    def _parse_verification_json(self, task_id: str, data: Dict) -> Optional[TaskExecutionData]:
        """Parse JSON-formatted verification data."""
        try:
            predictions = data.get('predictions', [])
            ground_truth = data.get('ground_truth', []) or data.get('actual_labels', [])
            accuracy = data.get('accuracy', 0.0)
            consensus_passed = data.get('consensus_passed', True)
            
            if not predictions or not ground_truth:
                return None
            
            return TaskExecutionData(
                task_id=task_id,
                module_phase='M5-M6',
                timestamp=datetime.now().isoformat(),
                predictions=predictions,
                ground_truth=ground_truth,
                accuracy=accuracy,
                model_predictions_artifact=data.get('model_link', 'N/A'),
                privacy_metrics=data.get('privacy_metrics', {}),
                miners_involved=data.get('miners_involved', 0),
                escrow_amount=data.get('escrow_amount', 0),
                consensus_votes=data.get('consensus_votes', 0),
                consensus_passed=consensus_passed
            )
        except Exception as e:
            print(f"  ✗ Failed to parse verification JSON: {e}")
            return None
    
    def _parse_verification_text(self, task_id: str, content: str) -> Optional[TaskExecutionData]:
        """Parse text-formatted verification logs."""
        try:
            lines = content.split('\n')
            
            # Extract accuracy from text
            accuracy_match = re.search(r'accuracy[:\s]*(\d+\.?\d*)%?', content, re.IGNORECASE)
            accuracy = float(accuracy_match.group(1)) / 100 if accuracy_match else 0.0
            
            # Extract consensus result
            consensus_passed = 'passed' in content.lower() and 'failed' not in content.lower()
            
            # Extract miners count
            miners_match = re.search(r'miners[:\s]*(\d+)', content, re.IGNORECASE)
            miners = int(miners_match.group(1)) if miners_match else 0
            
            # Return minimal data structure
            return TaskExecutionData(
                task_id=task_id,
                module_phase='M5-M6',
                timestamp=datetime.now().isoformat(),
                predictions=[],
                ground_truth=[],
                accuracy=accuracy,
                model_predictions_artifact='N/A',
                privacy_metrics={},
                miners_involved=miners,
                escrow_amount=0,
                consensus_votes=0,
                consensus_passed=consensus_passed
            )
        except Exception as e:
            print(f"  ✗ Failed to parse text verification: {e}")
            return None
    
    def _parse_db_query_result(self, task_id: str, data: Dict) -> Optional[TaskExecutionData]:
        """Parse database query result."""
        try:
            # Query typically returns: { task, block, verification, reward }
            task_record = data.get('task', {})
            verification_record = data.get('verification', {})
            block_record = data.get('block', {})
            
            predictions = verification_record.get('predictions', [])
            ground_truth = verification_record.get('actual_labels', [])
            accuracy = float(block_record.get('accuracy', 0.0))
            
            return TaskExecutionData(
                task_id=task_id,
                module_phase='M7',
                timestamp=block_record.get('timestamp', datetime.now().isoformat()),
                predictions=predictions,
                ground_truth=ground_truth,
                accuracy=accuracy,
                model_predictions_artifact=block_record.get('model_link', 'N/A'),
                privacy_metrics=self._extract_privacy_from_db(data),
                miners_involved=len(verification_record.get('miner_votes', [])),
                escrow_amount=float(task_record.get('reward_amount', 0)),
                consensus_votes=sum(1 for v in verification_record.get('miner_votes', []) if v),
                consensus_passed=verification_record.get('consensus_passed', True)
            )
        except Exception as e:
            print(f"  ✗ Failed to parse DB result: {e}")
            return None
    
    def _extract_privacy_from_db(self, data: Dict) -> Dict[str, Any]:
        """Extract privacy metrics from database record."""
        return {
            'gradients_encrypted': data.get('encryption_used', True),
            'encryption_algorithm': data.get('encryption_type', 'NDD-FE'),
            'gradient_compression_ratio': float(data.get('compression_ratio', 0.15)),
            'bandwidth_reduction': data.get('bandwidth_reduction', 85),
            'key_derivation_method': data.get('key_derivation', 'deterministic_hash'),
            'aggregator_key_secured': data.get('key_secured', True),
            'bsgs_time': data.get('bsgs_recovery_time', 0)
        }
    
    def generate_extraction_summary(self) -> Dict[str, Any]:
        """Generate summary of all extracted task data."""
        summary = {
            'total_tasks': len(self.extracted_data),
            'timestamp': datetime.now().isoformat(),
            'tasks': {}
        }
        
        for task_id, task_data in self.extracted_data.items():
            summary['tasks'][task_id] = {
                'phase': task_data.module_phase,
                'accuracy': task_data.accuracy,
                'consensus_passed': task_data.consensus_passed,
                'miners': task_data.miners_involved,
                'predictions_count': len(task_data.predictions),
                'privacy_encrypted': task_data.privacy_metrics.get('gradients_encrypted', False)
            }
        
        return summary


def load_task_results_from_directory(task_dir: Path) -> Dict[str, TaskExecutionData]:
    """
    Load all task results from a directory containing task outputs.
    
    Args:
        task_dir: Directory containing task result files
        
    Returns:
        Dictionary of task_id -> TaskExecutionData
    """
    extractor = TaskResultsExtractor(task_dir)
    results = {}
    
    # Look for verification results
    for result_file in task_dir.glob('*/verification_results.json'):
        task_id = result_file.parent.name
        
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            task_data = extractor._parse_verification_json(task_id, data)
            if task_data:
                results[task_id] = task_data
        except Exception as e:
            print(f"✗ Failed to load {task_id}: {e}")
    
    return results


if __name__ == '__main__':
    print("=" * 70)
    print("Task Results Extractor for HealChain")
    print("=" * 70)
    
    print("\nExample usage:")
    print("  extractor = TaskResultsExtractor(Path('backend/task_outputs'))")
    print("  results = extractor.extract_from_verification_logs('task_037', Path('logs'))")
    print("  privacy_metrics = extractor.extract_privacy_metrics_from_logs('task_037', log_file)")
    print("\nDone!")

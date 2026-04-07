"""
Benchmark Tables to PNG Visualization
Renders TABLE IV-VII as professional PNG images for presentations
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from framework_benchmark_comparison import FrameworkBenchmarkComparison


class BenchmarkTableVisualizer:
    """Convert benchmark tables to publication-ready PNG images"""
    
    def __init__(self, output_dir: Path = None, dpi: int = 300):
        """
        Initialize table visualizer
        
        Args:
            output_dir: Directory to save PNG files
            dpi: Resolution for PNG output (300 for print, 150 for screen)
        """
        self.output_dir = output_dir or Path('visualizations')
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.dpi = dpi
        
        self.benchmark = FrameworkBenchmarkComparison()
    
    def render_table_iv_time_consumption(self) -> Path:
        """Render TABLE IV: Time Consumption as PNG"""
        
        # Get data
        table_data = self.benchmark.generate_time_consumption_table()
        
        # Create DataFrame
        data_rows = []
        for fw in table_data['frameworks']:
            data_rows.append({
                'Framework': fw['Framework'],
                'Task Pub (h)': fw['Task_Publishing_h'],
                'Model Train (h)': fw['Model_Training_h'],
                'Model Agg (h)': fw['Model_Aggregation_h'],
                'Consensus (h)': fw['Consensus_h'],
                'Total (h)': fw['Total_Time_h'],
                'Accuracy (%)': fw['Accuracy_%']
            })
        
        df = pd.DataFrame(data_rows)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6), dpi=self.dpi)
        ax.axis('tight')
        ax.axis('off')
        
        # Create table
        table = ax.table(cellText=df.values, colLabels=df.columns,
                        cellLoc='center', loc='center',
                        colWidths=[0.15, 0.13, 0.13, 0.13, 0.13, 0.12, 0.12])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.5)
        
        # Style header
        for i in range(len(df.columns)):
            cell = table[(0, i)]
            cell.set_facecolor('#4472C4')
            cell.set_text_props(weight='bold', color='white', fontsize=11)
        
        # Style rows - highlight HealChain
        for i in range(1, len(df) + 1):
            for j in range(len(df.columns)):
                cell = table[(i, j)]
                
                # HealChain row (last row)
                if i == len(df):
                    cell.set_facecolor('#E7E6F7')
                    cell.set_text_props(weight='bold')
                # Alternate row colors
                elif i % 2 == 0:
                    cell.set_facecolor('#F2F2F2')
                else:
                    cell.set_facecolor('white')
        
        # Title and notes
        fig.suptitle('TABLE IV: Time Consumption of Different Frameworks',
                    fontsize=14, fontweight='bold', y=0.98)
        
        fig.text(0.5, 0.02, 'Note: All measurements in hours. Accuracy represents final model performance.',
                ha='center', fontsize=9, style='italic', color='#555555')
        
        # Save
        output_file = self.output_dir / 'TABLE_IV_Time_Consumption.png'
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_file
    
    def render_table_v_crypto_overhead(self) -> Path:
        """Render TABLE V: Cryptographic Overhead as PNG"""
        
        # Get data
        table_data = self.benchmark.generate_crypto_overhead_table()
        
        # Create data
        crypto_schemes = [
            ('NIFE & NIFE(SIMD)\n[BSR-FL]', 0.25, 18.12, 37.61, 0),
            ('NDD-FE\n[ESB-FL]', 0.19, 17.51, 36.19, 0),
            ('HE\n[PBFL]', 0.028, 44.43, 59.81, 29.93),
            ('NDD-FE\n[HealChain]', 0.19, 17.51, 36.19, 0),
        ]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6), dpi=self.dpi)
        ax.axis('tight')
        ax.axis('off')
        
        # Create table data
        table_rows = []
        for scheme, kg, enc, ip, dec in crypto_schemes:
            dec_str = f"{dec:.0f}" if dec > 0 else "0.0\n(non-interactive)"
            table_rows.append([scheme, f"{kg:.3f}", f"{enc:.2f}", f"{ip:.2f}", dec_str])
        
        table = ax.table(cellText=table_rows,
                        colLabels=['Cryptographic Scheme', 'Key Gen (s)', 'Encryption (s)', 
                                   'Inner Product (s)', 'Decryption (s)'],
                        cellLoc='center', loc='center',
                        colWidths=[0.25, 0.15, 0.15, 0.15, 0.2])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 3)
        
        # Style header
        for i in range(5):
            cell = table[(0, i)]
            cell.set_facecolor('#70AD47')
            cell.set_text_props(weight='bold', color='white', fontsize=11)
        
        # Style rows - highlight HealChain
        for i in range(1, len(crypto_schemes) + 1):
            for j in range(5):
                cell = table[(i, j)]
                
                # HealChain row (last row)
                if i == len(crypto_schemes):
                    cell.set_facecolor('#E2F0D9')
                    cell.set_text_props(weight='bold')
                # Alternate colors
                elif i % 2 == 0:
                    cell.set_facecolor('#F2F2F2')
                else:
                    cell.set_facecolor('white')
        
        # Title and notes
        fig.suptitle('TABLE V: Time Overheads of Cryptographic Schemes',
                    fontsize=14, fontweight='bold', y=0.98)
        
        fig.text(0.5, 0.02, 
                'Note: All measurements per operation in seconds. HealChain uses same NDD-FE as ESB-FL; Gradient-Norm scoring adds ≈0.02s.',
                ha='center', fontsize=9, style='italic', color='#555555')
        
        # Save
        output_file = self.output_dir / 'TABLE_V_Crypto_Overhead.png'
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_file
    
    def render_table_vi_signature_overhead(self) -> Path:
        """Render TABLE VI: Digital Signature Overhead as PNG"""
        
        # Create data
        sig_data = [
            ('BSR-FL', 'LeNet5', 0.26, 0.04),
            ('PBFL', 'LeNet5', 0.53, 0.05),
            ('BSR-FL', 'ResNet18', 12.74, 0.03),
            ('PBFL', 'ResNet18', 14.58, 0.04),
            ('HealChain', 'LeNet5', 0.25, 0.04),
            ('HealChain', 'ResNet18', 12.72, 0.03),
        ]
        
        # Create DataFrame
        df_data = []
        for fw, model, avg, std in sig_data:
            df_data.append({
                'Framework': fw,
                'Model': model,
                'Avg (s)': avg,
                'Std (s)': std
            })
        
        df = pd.DataFrame(df_data)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 5), dpi=self.dpi)
        ax.axis('tight')
        ax.axis('off')
        
        # Create table
        table = ax.table(cellText=df.values, colLabels=df.columns,
                        cellLoc='center', loc='center',
                        colWidths=[0.25, 0.2, 0.25, 0.25])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.8)
        
        # Style header
        for i in range(4):
            cell = table[(0, i)]
            cell.set_facecolor('#FFC000')
            cell.set_text_props(weight='bold', color='black', fontsize=11)
        
        # Style rows - highlight HealChain
        for i in range(1, len(df) + 1):
            for j in range(4):
                cell = table[(i, j)]
                
                # HealChain rows (last 2)
                if i > len(df) - 2:
                    cell.set_facecolor('#FFF2CC')
                    cell.set_text_props(weight='bold')
                # Alternate colors
                elif i % 2 == 0:
                    cell.set_facecolor('#F2F2F2')
                else:
                    cell.set_facecolor('white')
        
        # Title and notes
        fig.suptitle('TABLE VI: Digital Signature Verification Overhead',
                    fontsize=14, fontweight='bold', y=0.98)
        
        fig.text(0.5, 0.02, 
                'Note: All measurements in seconds. HealChain uses secp256r1 with batch verification.',
                ha='center', fontsize=9, style='italic', color='#555555')
        
        # Save
        output_file = self.output_dir / 'TABLE_VI_Signature_Overhead.png'
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_file
    
    def render_table_vii_fairness_metrics(self) -> Path:
        """Render TABLE VII: Fairness & Payment Guarantees as PNG"""
        
        # Create data
        fairness_data = [
            ('Payment Guarantee', 'None', 'Partial', 'Partial', 'None', '✓ Yes'),
            ('Task Honesty Verification', 'None', 'None', 'None', 'None', '✓ Yes'),
            ('Quality Contribution Scoring', 'Equal', 'Stake-w.', 'Stake-w.', 'None', '✓ Gradient-Norm'),
            ('Free-Rider Mitigation', 'None', 'Stake req', 'Stake req', 'None', '✓ Yes'),
            ('Byzantine Tolerance', 'None', 'f < n/2', 'f < n/2', 'None', '✓ f < n/2'),
        ]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6.5), dpi=self.dpi)
        ax.axis('tight')
        ax.axis('off')
        
        # Prepare table data
        table_rows = [[item[0], item[1], item[2], item[3], item[4], item[5]] 
                      for item in fairness_data]
        
        table = ax.table(cellText=table_rows,
                        colLabels=['Mechanism', 'FL', 'BSR-FL', 'ESB-FL', 'PBFL', 'HealChain'],
                        cellLoc='center', loc='center',
                        colWidths=[0.25, 0.12, 0.12, 0.12, 0.12, 0.22])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.5)
        
        # Style header
        for i in range(6):
            cell = table[(0, i)]
            cell.set_facecolor('#C55A11')
            cell.set_text_props(weight='bold', color='white', fontsize=11)
        
        # Style rows
        for i in range(1, len(fairness_data) + 1):
            for j in range(6):
                cell = table[(i, j)]
                
                # HealChain column (last column)
                if j == 5:
                    cell.set_facecolor('#FADBD8')
                    cell.set_text_props(weight='bold', color='#922B1D')
                # Alternate row colors
                elif i % 2 == 0:
                    cell.set_facecolor('#F2F2F2')
                else:
                    cell.set_facecolor('white')
        
        # Title and notes
        fig.suptitle('TABLE VII: Fairness & Payment Guarantees (HealChain Innovation)',
                    fontsize=14, fontweight='bold', y=0.98)
        
        fig.text(0.5, 0.01, 
                'Note: ✓ indicates mechanism present. HealChain provides three novel fairness enhancements absent in competing frameworks.',
                ha='center', fontsize=9, style='italic', color='#555555')
        
        # Save
        output_file = self.output_dir / 'TABLE_VII_Fairness_Metrics.png'
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_file
    
    def render_performance_comparison_chart(self) -> Path:
        """Render performance comparison as bar chart"""
        
        # Get data
        table_data = self.benchmark.generate_time_consumption_table()
        
        # Extract data
        frameworks = [fw['Framework'] for fw in table_data['frameworks']]
        total_times = [fw['Total_Time_h'] for fw in table_data['frameworks']]
        accuracies = [fw['Accuracy_%'] for fw in table_data['frameworks']]
        
        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=self.dpi)
        
        # Color scheme: highlight HealChain
        colors = ['#4472C4' if fw != 'HealChain' else '#DD2B1F' for fw in frameworks]
        
        # Plot 1: Total Time
        bars1 = ax1.bar(range(len(frameworks)), total_times, color=colors, edgecolor='black', linewidth=1.5)
        ax1.set_xticks(range(len(frameworks)))
        ax1.set_xticklabels(frameworks, rotation=45, ha='right', fontsize=10)
        ax1.set_ylabel('Total Time (hours)', fontsize=11, fontweight='bold')
        ax1.set_title('Total Execution Time Comparison', fontsize=12, fontweight='bold', pad=10)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.set_axisbelow(True)
        
        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars1, total_times)):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1f}h', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        # Plot 2: Accuracy
        bars2 = ax2.bar(range(len(frameworks)), accuracies, color=colors, edgecolor='black', linewidth=1.5)
        ax2.set_xticks(range(len(frameworks)))
        ax2.set_xticklabels(frameworks, rotation=45, ha='right', fontsize=10)
        ax2.set_ylabel('Accuracy (%)', fontsize=11, fontweight='bold')
        ax2.set_title('Model Accuracy Comparison', fontsize=12, fontweight='bold', pad=10)
        ax2.set_ylim([80, 100])
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)
        
        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars2, accuracies)):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        fig.suptitle('Performance Comparison: HealChain vs Related Frameworks',
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Save
        output_file = self.output_dir / 'Performance_Comparison_Chart.png'
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_file
    
    def render_fairness_features_chart(self) -> Path:
        """Render fairness features as visual comparison"""
        
        frameworks = ['FL', 'BSR-FL', 'ESB-FL', 'PBFL', 'HealChain']
        features = {
            'Payment\nGuarantee': [0, 1, 1, 0, 2],           # 0=no, 1=partial, 2=yes
            'Task\nHonesty': [0, 0, 0, 0, 2],
            'Quality\nScoring': [0, 1, 1, 0, 2],
            'Free-Rider\nMitigation': [0, 1, 1, 0, 2],
            'Byzantine\nTolerance': [0, 1, 1, 0, 1],
        }
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6), dpi=self.dpi)
        
        # Set up data
        x = np.arange(len(frameworks))
        width = 0.15
        
        # Color scheme: red=no (0), yellow=partial (1), green=yes (2)
        colors_map = {0: '#D62728', 1: '#FF7F0E', 2: '#2CA02C'}
        
        # Plot grouped bars
        for idx, (feature, values) in enumerate(features.items()):
            offset = width * (idx - len(features)//2)
            bars = ax.bar(x + offset, values, width, label=feature, 
                         color=[colors_map[v] for v in values],
                         edgecolor='black', linewidth=1)
        
        # Customize
        ax.set_ylabel('Implementation Level', fontsize=11, fontweight='bold')
        ax.set_xlabel('Framework', fontsize=11, fontweight='bold')
        ax.set_title('Fairness Features Comparison: HealChain Innovations', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(frameworks, fontsize=10)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(['None', 'Partial', 'Full'], fontsize=10)
        ax.set_ylim([0, 2.3])
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=5, fontsize=9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # Add legend for colors
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#D62728', edgecolor='black', label='Not Implemented'),
            Patch(facecolor='#FF7F0E', edgecolor='black', label='Partial'),
            Patch(facecolor='#2CA02C', edgecolor='black', label='Full'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        # Save
        output_file = self.output_dir / 'Fairness_Features_Chart.png'
        plt.tight_layout()
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_file
    
    def generate_all_table_pngs(self) -> List[Path]:
        """Generate all benchmark tables as PNG images"""
        
        print("\n" + "="*80)
        print("Generating Benchmark Tables as PNG Images")
        print("="*80 + "\n")
        
        output_files = []
        
        # TABLE IV
        print("[*] Rendering TABLE IV (Time Consumption)...")
        file_iv = self.render_table_iv_time_consumption()
        output_files.append(file_iv)
        print(f"✓ {file_iv.name}")
        
        # TABLE V
        print("[*] Rendering TABLE V (Crypto Overhead)...")
        file_v = self.render_table_v_crypto_overhead()
        output_files.append(file_v)
        print(f"✓ {file_v.name}")
        
        # TABLE VI
        print("[*] Rendering TABLE VI (Signature Overhead)...")
        file_vi = self.render_table_vi_signature_overhead()
        output_files.append(file_vi)
        print(f"✓ {file_vi.name}")
        
        # TABLE VII
        print("[*] Rendering TABLE VII (Fairness Metrics)...")
        file_vii = self.render_table_vii_fairness_metrics()
        output_files.append(file_vii)
        print(f"✓ {file_vii.name}")
        
        # Performance Comparison Chart
        print("[*] Rendering Performance Comparison Chart...")
        file_perf = self.render_performance_comparison_chart()
        output_files.append(file_perf)
        print(f"✓ {file_perf.name}")
        
        # Fairness Features Chart
        print("[*] Rendering Fairness Features Chart...")
        file_fair = self.render_fairness_features_chart()
        output_files.append(file_fair)
        print(f"✓ {file_fair.name}")
        
        print("\n" + "="*80)
        print("✅ All PNG Tables Generated Successfully!")
        print("="*80)
        print(f"\nOutput directory: {self.output_dir}")
        print(f"Total files: {len(output_files)}")
        print("\nGenerated files:")
        for f in output_files:
            size_kb = f.stat().st_size / 1024
            print(f"  • {f.name:<40} ({size_kb:.1f} KB)")
        
        return output_files


if __name__ == '__main__':
    # Generate all PNG tables
    visualizer = BenchmarkTableVisualizer(dpi=300)  # 300 DPI for print quality
    output_files = visualizer.generate_all_table_pngs()
    
    print("\n✅ Ready to use in presentations! Copy-paste the PNG files directly into your slides.")

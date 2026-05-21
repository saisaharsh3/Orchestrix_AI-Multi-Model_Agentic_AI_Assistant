"""
generate_graphs.py - Publication-quality visualizations for Orchest​rix research experiments

Generates 4 high-quality graphs suitable for academic papers from the 5-experiment results.
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set publication-quality style
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10

# Load results
with open('results_exp1.json') as f:
    exp1 = json.load(f)
with open('results_exp2.json') as f:
    exp2 = json.load(f)
with open('results_exp3.json') as f:
    exp3 = json.load(f)
with open('results_exp5.json') as f:
    exp5 = json.load(f)

output_dir = Path('graphs')
output_dir.mkdir(exist_ok=True)

print("Generating publication-quality graphs...")

# ============================================================================
# GRAPH 1: Experiment 1 - LLM Dependency (Stage Distribution)
# ============================================================================
fig, ax = plt.subplots(figsize=(8, 5))

stages = ['Design\n(No LLM)', 'Simple\nRouting', 'Pattern\nMatching', 'LLM\nDependent']
percentages = [
    exp1['stage_distribution']['1']['percentage'],
    exp1['stage_distribution']['2']['percentage'],
    exp1['stage_distribution']['3']['percentage'],
    exp1['stage_distribution']['4']['percentage']
]
colors = ['#2ecc71', '#f39c12', '#e74c3c', '#c0392b']

bars = ax.bar(stages, percentages, color=colors, edgecolor='black', linewidth=1.5, alpha=0.8)

# Add value labels on bars
for i, (bar, pct) in enumerate(zip(bars, percentages)):
    if pct > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')

ax.set_ylabel('Percentage of Queries (%)', fontweight='bold')
ax.set_title('Experiment 1: LLM Dependency in Request Routing\n(N=39 test queries)', 
             fontweight='bold', pad=15)
ax.set_ylim(0, 100)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('graphs/exp1_llm_dependency.png', dpi=300, bbox_inches='tight')
print("✓ Saved: exp1_llm_dependency.png")
plt.close()

# ============================================================================
# GRAPH 2: Experiment 2 - Confidence Calibration Distribution
# ============================================================================
fig, ax = plt.subplots(figsize=(9, 5))

confidence_ranges = ['Very Low\n(0.0-0.3)', 'Low\n(0.3-0.6)', 'High\n(0.6-0.8)', 'Very High\n(0.8-1.0)']
confidence_counts = [
    exp2['distribution']['very_low_0_0_0_3'],
    exp2['distribution']['low_0_3_0_6'],
    exp2['distribution']['high_0_6_0_8'],
    exp2['distribution']['very_high_0_8_1_0']
]
colors_conf = ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71']

bars = ax.bar(confidence_ranges, confidence_counts, color=colors_conf, 
              edgecolor='black', linewidth=1.5, alpha=0.8)

# Add value labels
for bar, count in zip(bars, confidence_counts):
    if count > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{int(count)}', ha='center', va='bottom', fontweight='bold')

ax.axhline(y=exp2['total_scores']/4, color='red', linestyle='--', linewidth=2, 
           label=f'Perfectly Calibrated (n={exp2["total_scores"]/4:.0f})', alpha=0.7)

ax.set_ylabel('Number of Queries', fontweight='bold')
ax.set_title('Experiment 2: Model Confidence Distribution\nMean Confidence = 0.371 (Underconfident)', 
             fontweight='bold', pad=15)
ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, max(confidence_counts) * 1.15)

plt.tight_layout()
plt.savefig('graphs/exp2_confidence_calibration.png', dpi=300, bbox_inches='tight')
print("✓ Saved: exp2_confidence_calibration.png")
plt.close()

# ============================================================================
# GRAPH 3: Experiment 3 - Latency vs Accuracy Tradeoff
# ============================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# Left: Latency comparison
query_types = ['Simple', 'Complex', 'RAG']
local_latencies = [
    exp3['latency_comparison']['simple']['local_avg_ms'],
    exp3['latency_comparison']['complex']['local_avg_ms'],
    exp3['latency_comparison']['rag']['local_avg_ms']
]
api_latencies = [
    exp3['latency_comparison']['simple']['api_avg_ms'],
    exp3['latency_comparison']['complex']['api_avg_ms'],
    exp3['latency_comparison']['rag']['api_avg_ms']
]

x = np.arange(len(query_types))
width = 0.35

bars1 = ax1.bar(x - width/2, local_latencies, width, label='Local Model', 
                color='#3498db', edgecolor='black', linewidth=1.5, alpha=0.8)
bars2 = ax1.bar(x + width/2, api_latencies, width, label='API Model', 
                color='#e74c3c', edgecolor='black', linewidth=1.5, alpha=0.8)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, height + 50, 
                    f'{int(height)}ms', ha='center', va='bottom', fontsize=9, fontweight='bold')

ax1.set_ylabel('Latency (milliseconds)', fontweight='bold')
ax1.set_title('Latency Comparison by Query Type', fontweight='bold', pad=12)
ax1.set_xticks(x)
ax1.set_xticklabels(query_types)
ax1.legend(loc='upper left')
ax1.grid(axis='y', alpha=0.3)

# Right: Speedup factor
speedups = [
    1 / exp3['latency_comparison']['simple']['speedup'],  # API is faster, so invert
    exp3['latency_comparison']['complex']['speedup'],
    exp3['latency_comparison']['rag']['speedup']
]
speedup_labels = ['API ~9x faster', 'Local ~7x faster', 'Local ~5x faster']
colors_speedup = ['#e74c3c', '#2ecc71', '#2ecc71']

bars_speedup = ax2.barh(query_types, speedups, color=colors_speedup, 
                        edgecolor='black', linewidth=1.5, alpha=0.8)

# Add value labels
for i, (bar, label) in enumerate(zip(bars_speedup, speedup_labels)):
    ax2.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, 
            label, va='center', fontweight='bold', fontsize=9)

ax2.axvline(x=1, color='black', linestyle='-', linewidth=1, alpha=0.5)
ax2.set_xlabel('Speedup Factor (x)', fontweight='bold')
ax2.set_title('Performance Advantage', fontweight='bold', pad=12)
ax2.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('graphs/exp3_latency_accuracy.png', dpi=300, bbox_inches='tight')
print("✓ Saved: exp3_latency_accuracy.png")
plt.close()

# ============================================================================
# GRAPH 4: Experiment 5 - Stylometric Defense Effectiveness
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 6))

defenses = ['Baseline\n(No Defense)', 'Paraphrase', 'Normalize', 'Obfuscate', 'Combined\n(Normalize+Obfuscate)']
similarity_scores = [
    exp5['baseline']['mean_max_similarity'],
    exp5['defenses']['paraphrase']['mean_max_similarity'],
    exp5['defenses']['normalize']['mean_max_similarity'],
    exp5['defenses']['obfuscate']['mean_max_similarity'],
    exp5['combined']['mean_max_similarity']
]

colors_defense = ['#c0392b', '#e67e22', '#f39c12', '#f1c40f', '#2ecc71']
bars = ax.bar(defenses, similarity_scores, color=colors_defense, 
              edgecolor='black', linewidth=1.5, alpha=0.8)

# Add value labels and effectiveness percentages
for i, (bar, score) in enumerate(zip(bars, similarity_scores)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
            f'{score:.3f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # Add reduction from baseline
    if i > 0:
        reduction = (exp5['baseline']['mean_max_similarity'] - score) / exp5['baseline']['mean_max_similarity'] * 100
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2, 
                f'-{reduction:.1f}%', ha='center', va='center', fontweight='bold', 
                fontsize=9, color='white', bbox=dict(boxstyle='round', facecolor='black', alpha=0.6))

# Add vulnerability threshold line
ax.axhline(y=0.7, color='red', linestyle='--', linewidth=2, label='Vulnerability Threshold (0.70)', alpha=0.7)
ax.axhline(y=0.5, color='green', linestyle='--', linewidth=2, label='Safe Threshold (0.50)', alpha=0.7)

ax.set_ylabel('Mean Maximum Similarity Score', fontweight='bold')
ax.set_title('Experiment 5: Stylometric Attack - Defense Effectiveness\nLower similarity = Better privacy protection', 
             fontweight='bold', pad=15)
ax.set_ylim(0, 1.0)
ax.legend(loc='upper right', fontsize=9)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('graphs/exp5_stylometry_defense.png', dpi=300, bbox_inches='tight')
print("✓ Saved: exp5_stylometry_defense.png")
plt.close()

# ============================================================================
# BONUS: Summary Statistics Table as Image
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 6))
ax.axis('tight')
ax.axis('off')

table_data = [
    ['Experiment', 'Key Metric', 'Value', 'Interpretation'],
    ['1: Orchestration', 'LLM Dependency', '87.2%', 'System routes through LLM for most queries'],
    ['', 'Non-LLM Handling', '12.8%', 'Direct rule-based handling without LLM'],
    ['2: Calibration', 'Mean Confidence', '0.371', 'Model is underconfident (should be ~0.60)'],
    ['', 'ECE Score', '0.100', 'Expected calibration error; room for improvement'],
    ['3: Efficiency', 'Simple Query Best', 'API (9x faster)', 'Use cloud for simple questions'],
    ['', 'Complex Query Best', 'Local (7x faster)', 'Local model excels at reasoning'],
    ['', 'RAG Best', 'Local (5x faster)', 'Privacy benefit outweighs latency gain'],
    ['5: Privacy', 'Baseline Vulnerability', '84.6% linking', 'Users linkable across modes without defense'],
    ['', 'Normalize Defense', '-18.5% improvement', 'Stealth Mode reduces stylometric similarity'],
    ['', 'Combined Defense', '-18.5% improvement', 'Limited effectiveness; stronger defenses needed'],
    ['', 'Recommendation', 'Phase 1+2', 'Deploy normalize now, add paraphrasing next'],
]

table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                colWidths=[0.15, 0.20, 0.20, 0.45])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2.2)

# Style header row
for i in range(4):
    table[(0, i)].set_facecolor('#34495e')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Alternate row colors
for i in range(1, len(table_data)):
    color = '#ecf0f1' if i % 2 == 0 else 'white'
    for j in range(4):
        table[(i, j)].set_facecolor(color)
        if j == 0 and i > 1 and table_data[i][0] == '':  # Indent sub-rows
            table[(i, j)].set_text_props(ha='left')

plt.title('Research Summary: Key Findings from 5 Experiments', 
         fontweight='bold', fontsize=13, pad=20)

plt.savefig('graphs/summary_statistics.png', dpi=300, bbox_inches='tight')
print("✓ Saved: summary_statistics.png")
plt.close()

print("\n" + "="*60)
print("✅ All graphs generated successfully!")
print("="*60)
print("\nGenerated files in 'graphs/' directory:")
print("  1. exp1_llm_dependency.png")
print("  2. exp2_confidence_calibration.png")
print("  3. exp3_latency_accuracy.png")
print("  4. exp5_stylometry_defense.png")
print("  5. summary_statistics.png")
print("\nAll graphs are publication-ready (300 DPI, professional styling)")

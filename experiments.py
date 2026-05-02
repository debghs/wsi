"""
Experiment Runner
Runs all comparison experiments: uniform, random, adaptive
"""

import os
import json
import subprocess
from datetime import datetime
import pandas as pd

from config import CONFIG


def run_experiment(dataset, mode, epochs=10):
    """Run single experiment"""
    print(f"\n{'='*70}")
    print(f"Running {mode.upper()} tiling on {dataset.upper()}")
    print(f"{'='*70}\n")
    
    cmd = [
        'python', 'train.py',
        '--dataset', dataset,
        '--mode', mode,
        '--epochs', str(epochs),
        '--cache',
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running experiment: {result.stderr}")
        return None
    
    print(result.stdout)
    
    return result.returncode == 0


def run_all_experiments(datasets=['camelyon16'], modes=['uniform', 'random', 'adaptive']):
    """Run all comparison experiments"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_dir = os.path.join(CONFIG['result_save_dir'], f'experiments_{timestamp}')
    os.makedirs(experiment_dir, exist_ok=True)
    
    results_summary = []
    
    for dataset in datasets:
        for mode in modes:
            success = run_experiment(dataset, mode, epochs=CONFIG['num_epochs'])
            
            if success:
                results_summary.append({
                    'dataset': dataset,
                    'mode': mode,
                    'status': 'success',
                })
            else:
                results_summary.append({
                    'dataset': dataset,
                    'mode': mode,
                    'status': 'failed',
                })
    
    # Save summary
    summary_df = pd.DataFrame(results_summary)
    summary_path = os.path.join(experiment_dir, 'experiment_summary.csv')
    summary_df.to_csv(summary_path, index=False)
    
    print(f"\n{'='*70}")
    print(f"Experiment Summary saved to: {summary_path}")
    print(f"{'='*70}\n")
    print(summary_df)
    
    return summary_df


def run_ablation_study(dataset='camelyon16'):
    """Run ablation study"""
    print(f"\n{'='*70}")
    print(f"Running Ablation Study on {dataset.upper()}")
    print(f"{'='*70}\n")
    
    ablation_configs = [
        {'name': 'baseline_uniform', 'mode': 'uniform'},
        {'name': 'baseline_random', 'mode': 'random'},
        {'name': 'adaptive_tiling', 'mode': 'adaptive'},
    ]
    
    results = []
    
    for config in ablation_configs:
        print(f"\nRunning: {config['name']}")
        success = run_experiment(dataset, config['mode'], epochs=CONFIG['num_epochs'])
        
        results.append({
            'ablation': config['name'],
            'status': 'success' if success else 'failed',
        })
    
    # Save results
    ablation_df = pd.DataFrame(results)
    ablation_path = os.path.join(CONFIG['result_save_dir'], 'ablation_results.csv')
    ablation_df.to_csv(ablation_path, index=False)
    
    print(f"\nAblation results saved to: {ablation_path}")
    
    return ablation_df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, default='full',
                       choices=['full', 'ablation', 'single'])
    parser.add_argument('--dataset', type=str, default='camelyon16')
    parser.add_argument('--tiling_mode', type=str, default='adaptive')
    parser.add_argument('--epochs', type=int, default=CONFIG['num_epochs'])
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        run_all_experiments(datasets=[args.dataset])
    elif args.mode == 'ablation':
        run_ablation_study(dataset=args.dataset)
    elif args.mode == 'single':
        run_experiment(args.dataset, args.tiling_mode, args.epochs)

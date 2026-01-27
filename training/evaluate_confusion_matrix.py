"""
Confusion Matrix Evaluation Script for YOLOv8 Classification Model

This script evaluates the trained YOLOv8 classification model and generates:
- Confusion matrix visualization
- Per-class metrics (precision, recall, F1-score)
- Overall accuracy
- Classification report

Usage:
    python evaluate_confusion_matrix.py [--model MODEL_PATH] [--dataset DATASET_PATH] [--output OUTPUT_DIR]

Requirements:
    pip install ultralytics matplotlib seaborn scikit-learn numpy
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from ultralytics import YOLO
from PIL import Image


def get_all_images(dataset_path: Path) -> List[Tuple[Path, str]]:
    """
    Get all images from dataset directory with their true class labels.
    
    Args:
        dataset_path: Path to dataset root directory
        
    Returns:
        List of tuples: (image_path, true_class_name)
    """
    images = []
    
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_path}")
    
    # Iterate through class folders
    for class_folder in sorted(dataset_path.iterdir()):
        if not class_folder.is_dir():
            continue
        
        class_name = class_folder.name
        
        # Find all images in this class folder
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            for img_path in class_folder.glob(ext):
                images.append((img_path, class_name))
    
    return images


def evaluate_model(
    model_path: Path,
    dataset_path: Path,
    output_dir: Path,
    device: str = 'cpu',
    max_samples: int = None
) -> None:
    """
    Evaluate YOLOv8 classification model and generate confusion matrix.
    
    Args:
        model_path: Path to trained model (.pt file)
        dataset_path: Path to dataset root directory
        output_dir: Directory to save confusion matrix and metrics
        device: Device to use ('cpu' or 'cuda')
        max_samples: Maximum number of samples per class (None for all)
    """
    print(f"Loading model from: {model_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    model = YOLO(str(model_path), task="classify")
    print("Model loaded successfully!")
    
    # Get all images with their true labels
    print(f"\nLoading images from: {dataset_path}")
    all_images = get_all_images(dataset_path)
    
    if len(all_images) == 0:
        raise ValueError(f"No images found in dataset directory: {dataset_path}")
    
    print(f"Found {len(all_images)} images")
    
    # Limit samples per class if specified
    if max_samples:
        from collections import defaultdict
        class_counts = defaultdict(int)
        limited_images = []
        for img_path, class_name in all_images:
            if class_counts[class_name] < max_samples:
                limited_images.append((img_path, class_name))
                class_counts[class_name] += 1
        all_images = limited_images
        print(f"Limited to {max_samples} samples per class: {len(all_images)} total images")
    
    # Get class names from model
    model_classes = list(model.names.values())
    num_classes = len(model_classes)
    print(f"\nModel has {num_classes} classes:")
    for i, class_name in enumerate(model_classes):
        print(f"  {i}: {class_name}")
    
    # Prepare predictions
    print("\nRunning inference on all images...")
    y_true = []
    y_pred = []
    y_probs = []
    
    for idx, (img_path, true_class) in enumerate(all_images):
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(all_images)} images...")
        
        try:
            # Load and preprocess image
            image = Image.open(img_path).convert('RGB')
            
            # Run inference
            results = model(image, verbose=False)
            result = results[0]
            
            # Get prediction
            if hasattr(result, 'probs'):
                top1_idx = result.probs.top1
                pred_class = model.names[top1_idx]
                confidence = float(result.probs.top1conf)
                
                y_true.append(true_class)
                y_pred.append(pred_class)
                y_probs.append(confidence)
            else:
                print(f"Warning: Unexpected output format for {img_path}")
                continue
                
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            continue
    
    print(f"\nSuccessfully processed {len(y_true)} images")
    
    if len(y_true) == 0:
        raise ValueError("No images were successfully processed")
    
    # Get unique classes (union of true and predicted)
    all_unique_classes = sorted(set(y_true + y_pred))
    
    # Ensure model classes match (handle case where dataset has different classes)
    if set(all_unique_classes) != set(model_classes):
        print(f"\nWarning: Dataset classes don't match model classes!")
        print(f"  Dataset classes: {sorted(set(y_true))}")
        print(f"  Model classes: {model_classes}")
        print(f"  Using intersection: {sorted(set(all_unique_classes) & set(model_classes))}")
        all_unique_classes = sorted(set(all_unique_classes) & set(model_classes))
    
    # Create confusion matrix
    print("\nGenerating confusion matrix...")
    cm = confusion_matrix(y_true, y_pred, labels=all_unique_classes)
    
    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)
    
    # Per-class metrics (handle case where some classes might not appear)
    precision = precision_score(y_true, y_pred, labels=all_unique_classes, average=None, zero_division=0)
    recall = recall_score(y_true, y_pred, labels=all_unique_classes, average=None, zero_division=0)
    f1 = f1_score(y_true, y_pred, labels=all_unique_classes, average=None, zero_division=0)
    
    # Print results
    print("\n" + "="*70)
    print("EVALUATION RESULTS")
    print("="*70)
    print(f"\nOverall Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"\nTotal Samples: {len(y_true)}")
    print(f"Classes Evaluated: {len(all_unique_classes)}")
    
    # Print per-class metrics
    print("\n" + "-"*70)
    print("Per-Class Metrics:")
    print("-"*70)
    print(f"{'Class':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    print("-"*70)
    
    for i, class_name in enumerate(all_unique_classes):
        # Count support (true samples for this class)
        support = sum(1 for y in y_true if y == class_name)
        print(f"{class_name:<20} {precision[i]:<12.4f} {recall[i]:<12.4f} {f1[i]:<12.4f} {support:<10}")
    
    # Print macro and weighted averages
    macro_precision = np.mean(precision)
    macro_recall = np.mean(recall)
    macro_f1 = np.mean(f1)
    weighted_precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    weighted_recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    
    print("-"*70)
    print(f"{'Macro Avg':<20} {macro_precision:<12.4f} {macro_recall:<12.4f} {macro_f1:<12.4f} {len(y_true):<10}")
    print(f"{'Weighted Avg':<20} {weighted_precision:<12.4f} {weighted_recall:<12.4f} {weighted_f1:<12.4f} {len(y_true):<10}")
    
    # Generate confusion matrix plot
    print("\nGenerating confusion matrix visualization...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(12, 10))
    
    # Normalize confusion matrix to percentages
    cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_normalized = np.nan_to_num(cm_normalized)  # Handle division by zero
    
    # Create heatmap
    sns.heatmap(
        cm_normalized,
        annot=True,
        fmt='.2f',
        cmap='Blues',
        xticklabels=all_unique_classes,
        yticklabels=all_unique_classes,
        cbar_kws={'label': 'Normalized Count'},
        linewidths=0.5,
        linecolor='gray'
    )
    
    plt.title(f'Confusion Matrix\nOverall Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)', 
              fontsize=14, fontweight='bold', pad=20)
    plt.xlabel('Predicted Class', fontsize=12, fontweight='bold')
    plt.ylabel('True Class', fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    # Save confusion matrix
    cm_path = output_dir / 'confusion_matrix.png'
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    print(f"Confusion matrix saved to: {cm_path}")
    plt.close()
    
    # Also save raw confusion matrix (counts)
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=all_unique_classes,
        yticklabels=all_unique_classes,
        cbar_kws={'label': 'Count'},
        linewidths=0.5,
        linecolor='gray'
    )
    
    plt.title(f'Confusion Matrix (Raw Counts)\nTotal Samples: {len(y_true)}', 
              fontsize=14, fontweight='bold', pad=20)
    plt.xlabel('Predicted Class', fontsize=12, fontweight='bold')
    plt.ylabel('True Class', fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    cm_counts_path = output_dir / 'confusion_matrix_counts.png'
    plt.savefig(cm_counts_path, dpi=300, bbox_inches='tight')
    print(f"Confusion matrix (counts) saved to: {cm_counts_path}")
    plt.close()
    
    # Save classification report to text file
    report = classification_report(y_true, y_pred, labels=all_unique_classes, target_names=all_unique_classes)
    report_path = output_dir / 'classification_report.txt'
    with open(report_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("CLASSIFICATION REPORT\n")
        f.write("="*70 + "\n\n")
        f.write(f"Overall Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)\n")
        f.write(f"Total Samples: {len(y_true)}\n")
        f.write(f"Classes Evaluated: {len(all_unique_classes)}\n\n")
        f.write(report)
        f.write("\n" + "="*70 + "\n")
        f.write("Per-Class Details:\n")
        f.write("="*70 + "\n")
        for i, class_name in enumerate(all_unique_classes):
            support = sum(1 for y in y_true if y == class_name)
            f.write(f"\n{class_name}:\n")
            f.write(f"  Precision: {precision[i]:.4f}\n")
            f.write(f"  Recall: {recall[i]:.4f}\n")
            f.write(f"  F1-Score: {f1[i]:.4f}\n")
            f.write(f"  Support: {support}\n")
    
    print(f"Classification report saved to: {report_path}")
    
    # Save confusion matrix as numpy array
    cm_array_path = output_dir / 'confusion_matrix.npy'
    np.save(cm_array_path, cm)
    print(f"Confusion matrix array saved to: {cm_array_path}")
    
    print("\n" + "="*70)
    print("Evaluation completed successfully!")
    print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate YOLOv8 classification model and generate confusion matrix'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='../backend/models/best.pt',
        help='Path to trained model file (default: ../backend/models/best.pt)'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='dataset',
        help='Path to dataset directory (default: dataset)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='evaluation_results',
        help='Output directory for results (default: evaluation_results)'
    )
    parser.add_argument(
        '--device',
        type=str,
        default='cpu',
        choices=['cpu', 'cuda'],
        help='Device to use for inference (default: cpu)'
    )
    parser.add_argument(
        '--max-samples',
        type=int,
        default=None,
        help='Maximum number of samples per class to evaluate (default: None = all samples)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths relative to script directory
    script_dir = Path(__file__).parent
    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = script_dir / model_path
    
    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = script_dir / dataset_path
    
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir
    
    try:
        evaluate_model(
            model_path=model_path,
            dataset_path=dataset_path,
            output_dir=output_dir,
            device=args.device,
            max_samples=args.max_samples
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

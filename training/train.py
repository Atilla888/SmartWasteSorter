"""
YOLOv8 Classification Training Script for Waste Sorting

This script trains a YOLOv8 classification model on the garbage classification dataset.
Uses transfer learning from pre-trained YOLOv8 classification models.

Adjust the configuration variables below to change training parameters.
Models are automatically saved to the model_output folder.
After training, manually copy the best model to backend/models/best.pt

Requirements:
    pip install ultralytics
"""

from pathlib import Path
from ultralytics import YOLO


# ============================================================================
# CONFIGURATION - Adjust these values to change training parameters
# ============================================================================

# Model selection: 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (extra large)
MODEL_SIZE = 's'

# Dataset path (relative to this script)
DATASET_PATH = 'dataset'

# Training parameters
EPOCHS = 50
BATCH_SIZE = 32
IMAGE_SIZE = 224
DEVICE = 'cpu'  # 'cpu' or 'cuda'

# Early stopping: stop training after N epochs with no improvement (0 to disable)
PATIENCE = 10

# Learning rate and optimizer
LEARNING_RATE = 0.01
LR_FINAL_FACTOR = 0.01
OPTIMIZER = 'auto'  # 'auto', 'SGD', 'Adam', 'AdamW', or 'RMSProp' (auto lets YOLOv8 choose)
MOMENTUM = 0.937
WEIGHT_DECAY = 0.0005

# Warmup
WARMUP_EPOCHS = 3.0
WARMUP_MOMENTUM = 0.8
WARMUP_BIAS_LR = 0.0

# Data augmentation
HSV_H = 0.015
HSV_S = 0.7
HSV_V = 0.4
DEGREES = 10.0
TRANSLATE = 0.1
SCALE = 0.5
FLIPUD = 0.0
FLIPLR = 0.5
MOSAIC = 0.0
MIXUP = 0.1
AUTO_AUGMENT = 'randaugment'  # Auto augmentation method
ERASING = 0.4  # Random erasing probability

# Classification specific
DROPOUT = 0.5

# Output directory
PROJECT_NAME = 'model_output'
EXPERIMENT_NAME = 'run'

# Resume training: set to path of checkpoint file to resume, or None to start fresh
# Example: RESUME = 'model_output/run/weights/last.pt'
RESUME = None


# ============================================================================
# TRAINING CODE - Do not modify below unless you know what you're doing
# ============================================================================

def get_model_path(model_size: str) -> str:
    """Get YOLOv8 classification model path based on size."""
    model_map = {
        'n': 'yolov8n-cls.pt',
        's': 'yolov8s-cls.pt',
        'm': 'yolov8m-cls.pt',
        'l': 'yolov8l-cls.pt',
        'x': 'yolov8x-cls.pt',
    }
    return model_map.get(model_size.lower(), 'yolov8s-cls.pt')


def main():
    script_dir = Path(__file__).parent
    dataset_path = script_dir / DATASET_PATH
    
    if not dataset_path.exists():
        print(f"Error: Dataset directory not found at {dataset_path}")
        print(f"\nExpected structure: {dataset_path}/class1/, {dataset_path}/class2/, ...")
        print("\nDataset should contain subfolders for each class:")
        print("  - battery/")
        print("  - biological/")
        print("  - brown-glass/")
        print("  - cardboard/")
        print("  - clothes/")
        print("  - green-glass/")
        print("  - metal/")
        print("  - paper/")
        print("  - plastic/")
        print("  - shoes/")
        print("  - trash/")
        print("  - white-glass/")
        return
    
    class_folders = [d for d in dataset_path.iterdir() if d.is_dir()]
    if len(class_folders) == 0:
        print(f"Error: No class subfolders found in {dataset_path}")
        return
    
    print(f"Found {len(class_folders)} class folders:")
    for folder in sorted(class_folders):
        image_count = len(list(folder.glob('*.jpg'))) + len(list(folder.glob('*.png'))) + len(list(folder.glob('*.jpeg')))
        print(f"  - {folder.name}: {image_count} images")
    
    if RESUME:
        resume_path = Path(RESUME)
        if not resume_path.exists():
            print(f"Error: Resume checkpoint not found at {resume_path}")
            return
        print(f"\nResuming training from: {resume_path}")
        model_path = str(resume_path)
        resume = True
    else:
        # TRANSFER LEARNING: Get pre-trained model name (e.g., 'yolov8s-cls.pt')
        # This model was pre-trained on ImageNet with 1000 classes
        model_path = get_model_path(MODEL_SIZE)
        resume = False
    
    print(f"\nTraining Configuration:")
    if resume:
        print(f"  Mode: Resuming from checkpoint")
        print(f"  Checkpoint: {model_path}")
    else:
        print(f"  Mode: Starting from pre-trained model")
        print(f"  Model: {model_path} ({MODEL_SIZE.upper()})")
    print(f"  Dataset: {dataset_path}")
    print(f"  Max epochs: {EPOCHS}")
    print(f"  Early stopping patience: {PATIENCE if PATIENCE > 0 else 'Disabled'}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Image size: {IMAGE_SIZE}")
    print(f"  Device: {DEVICE}")
    print(f"\nHyperparameters:")
    print(f"  Learning rate: {LEARNING_RATE}")
    print(f"  LR final factor: {LR_FINAL_FACTOR}")
    print(f"  Optimizer: {OPTIMIZER}")
    print(f"  Momentum: {MOMENTUM}")
    print(f"  Weight decay: {WEIGHT_DECAY}")
    print(f"  Warmup epochs: {WARMUP_EPOCHS}")
    print(f"  Dropout: {DROPOUT}")
    
    # TRANSFER LEARNING: Load pre-trained model
    # This loads weights that were trained on ImageNet (1.2M images, 1000 classes)
    # The model already knows how to recognize basic image features
    print(f"\nLoading pre-trained model: {model_path}")
    print("  (Transfer learning: using ImageNet pre-trained weights)")
    model = YOLO(model_path)
    
    output_dir = script_dir / PROJECT_NAME / EXPERIMENT_NAME / "weights"
    print(f"\nModels will be saved to: {output_dir}")
    
    print("\nStarting training...")
    print("  (Fine-tuning pre-trained model on the 12 waste classes)")
    if PATIENCE > 0:
        print(f"Note: Training will stop early if no improvement for {PATIENCE} epochs")
    
    # TRANSFER LEARNING: Fine-tuning step
    # The model.train() method automatically:
    # 1. Keeps most pre-trained feature extraction layers
    # 2. Replaces final classification layer for 12 classes
    # 3. Fine-tunes the model on the waste dataset
    results = model.train(
        data=str(dataset_path),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        device=DEVICE,
        project=PROJECT_NAME,
        name=EXPERIMENT_NAME,
        task='classify',
        resume=resume,
        patience=PATIENCE if PATIENCE > 0 else 0,
        
        lr0=LEARNING_RATE,
        lrf=LR_FINAL_FACTOR,
        momentum=MOMENTUM,
        weight_decay=WEIGHT_DECAY,
        optimizer=OPTIMIZER,
        
        warmup_epochs=WARMUP_EPOCHS,
        warmup_momentum=WARMUP_MOMENTUM,
        warmup_bias_lr=WARMUP_BIAS_LR,
        
        hsv_h=HSV_H,
        hsv_s=HSV_S,
        hsv_v=HSV_V,
        degrees=DEGREES,
        translate=TRANSLATE,
        scale=SCALE,
        flipud=FLIPUD,
        fliplr=FLIPLR,
        mosaic=MOSAIC,
        mixup=MIXUP,
        auto_augment=AUTO_AUGMENT,
        erasing=ERASING,
        
        dropout=DROPOUT,
        
        verbose=True
    )
    
    print("\n" + "="*70)
    print("Training completed!")
    print("="*70)
    
    print(f"\nModels saved in: {output_dir}")
    print(f"After training, copy the best model to backend/models/best.pt")
    
    print(f"\nTraining results saved in: {script_dir / PROJECT_NAME / EXPERIMENT_NAME}")


if __name__ == "__main__":
    main()

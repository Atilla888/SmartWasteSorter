# Machine Learning / Computer Vision Code Explanation

This document explains the machine learning (ML) and computer vision–related code at a function and pipeline level, and how it integrates into the overall system.

Covered files:
- `training/train.py`
- `backend/services/camera_service.py`
- `backend/utils/image_utils.py`

> Note: Paths are relative to the project root.

---

## 1. File: `training/train.py`

**Purpose:**

Script for training a YOLOv8 *classification* model on a dataset organized in subfolders by class name under `training/dataset/`. It also handles checkpoint-based resume and exports the best model to ONNX.

### 1.1. Function: `get_classes_from_dataset(dataset_path: str) -> list`

**Role:**

Detects class labels from the directory structure of the dataset. This defines the classification classes for YOLOv8.

**Inputs:**
- `dataset_path` (str): Path to the dataset directory.

**Outputs:**
- `list[str]`: Alphabetically sorted list of class names, one per subfolder under the dataset directory.

**Logic / Pipeline:**
1. Converts `dataset_path` to a `Path` object.
2. Checks that the directory exists; raises `ValueError` if not.
3. Iterates over directory entries and collects names of subdirectories (each subdirectory is treated as a class).
4. Validates that at least one class was found; raises `ValueError` otherwise.
5. Sorts the class names alphabetically and prints them.
6. Returns the sorted list.

**Data Input / Preprocessing:**
- Assumes dataset structured as:
  - `training/dataset/<class_name_1>/...`
  - `training/dataset/<class_name_2>/...`
- The function does **not** inspect image files, only folder names.

**Assumptions:**
- Each subfolder name corresponds to a class label.
- All class subfolders are direct children of `dataset_path`.

**Performance / Constraints:**
- Only filesystem scanning; overhead is negligible compared to training.

---

### 1.2. Function: `train_model(...)`

```python
def train_model(
    dataset_path: str = "dataset",
    model_size: str = "s",  # Options: 's', 'm', 'l'
    imgsz: int = 224,
    batch: int = 32,
    epochs: int = 50,
    output_dir: str = "model_output",
):
```

**Role:**

Trains a YOLOv8 classification model on the dataset and exports the best model to ONNX.

**Inputs (parameters):**
- `dataset_path` (str): Relative path to dataset directory from `training/` (default: `"dataset"`).
- `model_size` (str): Model size key for YOLOv8 (`"s"`, `"m"`, or `"l"`).
- `imgsz` (int): Training image size; YOLO will resize/normalize internally.
- `batch` (int): Batch size.
- `epochs` (int): Maximum number of training epochs.
- `output_dir` (str): Root output directory for training results (default: `"model_output"`).

**Outputs:**
- Returns `results` from `model.train(...)` (Ultralytics training results object).
- Writes model weights and artifacts to disk under: `training/{output_dir}/run/weights/`.
- Exports best weights to ONNX if available.

**Pipeline Steps:**

1. **Resolve Paths:**
   - `script_dir = Path(__file__).parent` (the `training/` directory).
   - `dataset_full_path = script_dir / dataset_path`.
   - `output_full_path = script_dir / output_dir`.
   - `weights_dir = output_full_path / "run" / "weights"`.
   - Creates `output_full_path` if it does not exist.

2. **Class Discovery (Data Input):**
   - Calls `get_classes_from_dataset(dataset_full_path)`.
   - Prints the discovered classes and general training configuration.

3. **Model Loading (Training Side):**
   - Checks for checkpoint at `output_full_path / "run" / "weights" / "last.pt"`.
   - If checkpoint exists:
     - Prints resume message.
     - Loads model with `YOLO(str(last_ckpt), task="classify")`.
     - Sets `resume_flag = True`.
   - Else:
     - Prints message about starting new training.
     - Constructs `model_name = f"yolov8{model_size}-cls.pt"`.
     - Loads base model with `YOLO(model_name)`.
     - Sets `resume_flag = False`.

4. **Training Configuration (Model.train Call):**

   Calls `model.train(...)` with:
   - **Data & core params:**
     - `data=str(dataset_full_path)` (path where YOLO will look for class subfolders).
     - `imgsz=imgsz` (e.g., 224).
     - `batch=batch`.
     - `epochs=epochs`.
   - **Regularization and Augmentations:**
     - `label_smoothing=0.1`.
     - `dropout=0.5`.
     - `weight_decay=0.0005`.
     - Color and geometric augmentations (e.g., `hsv_*`, `degrees`, `translate`, `scale`, `fliplr`, `mixup`).
   - **Training settings:**
     - `patience=10` (early stopping).
     - `save=True`, `save_period=10` (checkpoints).
     - `val=True` (runs validation).
     - `resume=resume_flag` (resume from checkpoint if available).
   - **Output:**
     - `project=str(output_full_path)`.
     - `name="run"` (all artifacts under `model_output/run`).
   - **Other:**
     - `verbose=True`, `plots=True`.
     - `device="cpu"` (explicitly forces CPU training).

5. **Post-Training Logging:**
   - Prints completion messages.

6. **Export to ONNX (Post-Processing):**
   - Sets `best_model_path = weights_dir / "best.pt"`.
   - If file exists:
     - Prints message about exporting.
     - Loads `best_model = YOLO(str(best_model_path))`.
     - Calls `best_model.export(format="onnx", imgsz=imgsz, dynamic=False, simplify=True)`.
     - Intended save path is `onnx_path = output_full_path / "run" / "weights" / "best.onnx"`.
   - Else:
     - Prints warning that best model not found.
   - Logs final output path: `output_full_path / 'run'`.

**Data Input / Preprocessing:**
- The script **does not** implement custom pixel-level preprocessing; it relies entirely on YOLOv8’s built-in handling. The main data step is class discovery (`get_classes_from_dataset`) and passing dataset path; YOLO handles:
  - Image loading
  - Resizing to `imgsz`
  - Normalization and augmentations

**Model Loading (Training):**
- Uses `YOLO(last_checkpoint, task="classify")` when resuming.
- Uses `YOLO("yolov8{size}-cls.pt")` when starting from scratch.

**Inference (Within Training Context):**
- Inference is handled internally by YOLO during training and validation; this script does **not** expose a standalone inference function.

**Post-Processing / Outputs to Other Components:**
- Produces:
  - `best.pt` – best-performing classification model weights.
  - `last.pt` – last epoch weights.
  - `best.onnx` – ONNX export of best model.
- These artifacts are **consumed by the backend**:
  - At runtime, `backend/services/camera_service.py` expects the model at `backend/models/best.pt`.
  - A **manual copy or move step** is implied: copying `training/model_output/run/weights/best.pt` to `backend/models/best.pt`.
  - The ONNX export (`best.onnx`) could be used for deployment in environments that prefer ONNX, but current backend code uses the PyTorch/Ultralytics API.

**Assumptions:**
- Dataset is correctly organized at `training/dataset/` with class subfolders.
- Enough disk space for checkpoints and ONNX export.
- Training runs on CPU (`device="cpu"`), so no GPU is assumed.

**Performance / Design Constraints:**
- **CPU-only Training:** `device="cpu"` will make training significantly slower than GPU; appropriate for small experiments or CPU-only environments.
- **Checkpoint Resume:** The script is optimized to resume from `last.pt` if available, avoiding complete retraining after interruptions.
- **Heavy Augmentation:** Multiple augmentations (HSV, rotation, translation, mixup) can increase training time but improve generalization.
- **Output Location Mismatch:**
  - Training outputs to `training/model_output/run/weights/`.
  - Inference backend expects `backend/models/best.pt`.
  - This introduces a manual step or external process to sync weights.

---

### 1.3. `if __name__ == "__main__":` Block

**Role:**

Provides default configuration and starts training when the script is executed directly.

**Configuration:**
- `DATASET_PATH = "dataset"`
- `MODEL_SIZE = "s"`
- `IMG_SIZE = 224`
- `BATCH_SIZE = 32`
- `EPOCHS = 50`
- `OUTPUT_DIR = "model_output"`

**Execution:**
- Calls `train_model(...)` with the above parameters.

**Assumptions:**
- Script is executed from a Python environment with the required dependencies (`ultralytics`, etc.).
- Dataset exists at `training/dataset`.

---

## 2. File: `backend/services/camera_service.py`

**Purpose:**

Runtime ML **inference** service. Handles:
- Loading the YOLOv8 classification model (trained via `training/train.py`).
- Running inference on uploaded images.
- Returning prediction and confidence.
- Passing prediction to the robotics subsystem.

### 2.1. Global Configuration & Paths

**Key variables:**

- `BASE_DIR = Path(__file__).resolve().parent.parent`
  - Resolves to `backend/` directory.

- `FRAMES_DIR = BASE_DIR / "frames"`
  - Directory where captured frames are saved.

- `_model: Optional[YOLO] = None`
  - Global cache for YOLO model instance.

- `model_path_str = os.getenv("YOLO_MODEL_PATH")`
  - If set, overrides model path via environment variable.

- `MODEL_PATH`:
  - If `YOLO_MODEL_PATH` is set: `Path(model_path_str)`.
  - Else: `BASE_DIR / "models" / "best.pt"` (i.e., `backend/models/best.pt`).

- `MODEL_DEVICE = os.getenv("YOLO_DEVICE", "cpu")`
  - Device selector for inference; currently **not passed** into `YOLO()` or inference call in this file, so device usage is determined by Ultralytics defaults or environment.

**Assumptions:**
- Trained model weights are available at `backend/models/best.pt` **or** at the path specified by `YOLO_MODEL_PATH`.
- `backend/frames/` is writeable for saving images.

---

### 2.2. Function: `_load_model() -> YOLO`

**Role:**

Lazily loads the YOLO classification model and caches it in the `_model` global variable.

**Inputs:**
- None.

**Outputs:**
- `YOLO`: Ultralytics YOLO model configured for classification.

**Logic:**
1. If `_model` is `None`:
   - Checks if `MODEL_PATH` exists; raises `FileNotFoundError` if missing.
   - Calls `YOLO(str(MODEL_PATH), task="classify")` to load the classifier.
   - Stores the model in `_model`.
2. Returns `_model`.

**Data Input / Preprocessing:**
- No image-level preprocessing here; this function is purely model loading.

**Assumptions:**
- `MODEL_PATH` points to a valid YOLO classification checkpoint (e.g., `best.pt` from training).

**Performance / Constraints:**
- **Lazy Loading:** Model is loaded only on first inference; subsequent calls reuse the loaded model.
- **File Existence:** If model file is not found, inference will fail immediately with a clear error.

---

### 2.3. Function: `ensure_frames_directory() -> None`

**Role:**

Ensures `backend/frames/` directory exists before saving images.

**Side Effects:**
- Filesystem: Creates directory `backend/frames/` if it does not exist.

---

### 2.4. Function: `run_inference(image: Image.Image) -> dict`

**Role:**

Runs YOLOv8 **classification** inference on a PIL Image and returns the top-1 prediction and confidence.

**Inputs:**
- `image` (`PIL.Image.Image`): Input image in (ideally) RGB mode.

**Outputs:**
- `dict` with keys:
  - `"prediction"` (str): Predicted class name (e.g., `"plastic"`).
  - `"confidence"` (float): Confidence score in `[0.0, 1.0]`.

**Pipeline:**
1. Calls `_load_model()` to get cached YOLO model.
2. If `image.mode != "RGB"`, converts the image to RGB.
3. Calls `results = model(image, verbose=False)`.
4. Extracts first result: `result = results[0]`.
5. Expects classification probabilities in `result.probs`:
   - `top1_idx = result.probs.top1`.
   - `confidence = float(result.probs.top1conf)`.
   - `class_name = result.names[top1_idx]`.
6. Returns `{"prediction": class_name, "confidence": confidence}`.

**Data Input / Preprocessing:**
- Ensures input is RGB; no resizing done here – YOLO performs internal resizing/normalization.

**Model Loading / Inference:**
- Uses the same YOLO model for all requests (cached).
- Inference is done on a single image at a time (no batching in this function).

**Post-Processing:**
- Converts internal indices and probabilities to a human-readable dictionary.
- No thresholding or multi-label logic; strictly top-1 classification.

**Assumptions:**
- `result.probs` exists and follows Ultralytics classification API.
- The model is a classification model (not detection or segmentation).

**Performance / Constraints:**
- Single-image inference; throughput depends on model size and hardware.
- No explicit device selection is passed here; device behavior follows Ultralytics defaults.

---

### 2.5. Function: `process_frame(file: UploadFile) -> dict`

**Role:**

Orchestrates the runtime ML inference pipeline for a single uploaded image and integrates with the robot control subsystem.

**Inputs:**
- `file` (`fastapi.UploadFile`): Uploaded image from HTTP request.

**Outputs:**
- `dict` with keys:
  - `"success"` (bool): Indicates if processing succeeded.
  - `"saved_as"` (str): Filename the image was saved as (if success).
  - `"prediction"` (str): Predicted class name.
  - `"confidence"` (float): Confidence score.
  - `"robot_action"` (str): Message indicating robot sorting result or error.
  - On errors: `{"success": False, "error": str(e)}`.

**Pipeline:**

1. **Directory Preparation:**
   - Calls `ensure_frames_directory()` to ensure `backend/frames/` exists.

2. **Data Input / Preprocessing:**
   - Calls `image = read_upload_image(file)` from `backend/utils/image_utils.py` to decode the uploaded image into a PIL Image in RGB format.

3. **File Saving (for logging/audit):**
   - Generates timestamp string: `YYYYMMDD_HHMMSS_mmm`.
   - Constructs filename: `f"frame_{timestamp}.jpg"`.
   - Constructs `filepath = os.path.join(FRAMES_DIR, filename)`.
   - Saves image as JPEG at `filepath` (`quality=95`).

4. **ML Inference:**
   - Calls `inference_result = run_inference(image)`.
   - `inference_result` contains `"prediction"` and `"confidence"`.

5. **Integration with Robot:**
   - Logs separator and prediction to stdout.
   - Calls `robot_success, robot_message = sort_with_robot(inference_result["prediction"])` from `backend/services/dobot_service.py`.
   - Catches exceptions during robot sorting; sets `robot_success = False` and `robot_message` to error info if an exception occurs.

6. **Response Assembly (Post-Processing):**
   - Builds base `response` dict:
     ```python
     response = {
         "success": True,
         "saved_as": filename,
         "prediction": inference_result["prediction"],
         "confidence": inference_result["confidence"],
     }
     ```
   - Adds `"robot_action"` field:
     - If `robot_success`: `response["robot_action"] = robot_message`.
     - Else: `response["robot_action"] = f"Robot error: {robot_message}"`.

7. **Error Handling:**
   - On any exception in the outer try block, returns:
     ```python
     {"success": False, "error": str(e)}
     ```

**How Outputs Are Passed to Other Components:**
- The FastAPI `/capture` endpoint in `backend/main.py` calls `process_frame(file)` and directly returns this dictionary as JSON.
- The Next.js API route `/api/capture` proxies this JSON unchanged to the frontend.
- The React component `SplineSceneBasic` (in `components/ui/demo.tsx`) reads this JSON and extracts:
  - `json.saved_as`
  - `json.prediction`
  - `json.confidence`
- The frontend displays prediction, confidence (as percentage), and the combined status message.
- `robot_action` is primarily for logging and user feedback on the backend side.

**Assumptions:**
- Uploads are single images compatible with PIL.
- Robot sorting is synchronous and may take several seconds; API stays open until complete.

**Performance / Constraints:**
- **Synchronous Pipeline:**
  - File I/O (save), ML inference, and robot sorting all run sequentially.
  - All work happens in the request/response cycle; the HTTP request is blocked until robot completes.
- **Disk Usage:**
  - Every inference saves a JPEG frame; disk usage grows with number of requests.
- **No Batching:**
  - Designed for single-image usage, not batch processing.

---

## 3. File: `backend/utils/image_utils.py`

**Purpose:**

Provides image decoding/preprocessing utilities used by the ML inference pipeline.

### 3.1. Function: `read_upload_image(file: UploadFile) -> Image.Image`

**Role:**

Converts a FastAPI `UploadFile` into a PIL Image in RGB format.

**Inputs:**
- `file` (`fastapi.UploadFile`): File object representing uploaded image.

**Outputs:**
- `PIL.Image.Image`: Image converted to RGB.

**Pipeline:**
1. Reads all bytes from `file.file.read()`.
2. Wraps bytes in a `BytesIO` stream.
3. Calls `Image.open(BytesIO(...))` to decode the image.
4. Calls `image.convert("RGB")` to ensure 3-channel RGB.
5. Returns the image.

**Integration:**
- Used exclusively by `backend/services/camera_service.py` in `process_frame()`.
- Provides a standardized input format for `run_inference()`.

**Assumptions:**
- Uploaded file is a valid image format supported by PIL.

**Performance / Constraints:**
- Reads entire file into memory; acceptable for single-image uploads of moderate size.

---

## 4. ML Inference Pipeline Summary

From a system perspective, the ML portion of the application operates as follows:

1. **Training (Offline, one-time or periodic):**
   - Run `python training/train.py`.
   - Script discovers classes from `training/dataset/` subfolders.
   - Trains YOLOv8 classification model with specified hyperparameters.
   - Writes:
     - `training/model_output/run/weights/best.pt`
     - `training/model_output/run/weights/last.pt`
     - `training/model_output/run/weights/best.onnx`

2. **Deployment/Preparation:**
   - Copy or move `best.pt` from training outputs to `backend/models/best.pt` (or set `YOLO_MODEL_PATH` to the training location).

3. **Runtime Inference (Online):**
   - Frontend captures a frame via `/api/snapshot` → FastAPI `/snapshot` (DroidCam MJPEG extraction).
   - Frontend uploads JPEG via `/api/capture` → FastAPI `/capture`.
   - FastAPI `/capture` endpoint calls `process_frame(file)`.

4. **Backend Inference Steps inside `process_frame`:**
   - `read_upload_image(file)` → PIL Image (RGB).
   - Save image to `backend/frames/` with timestamp filename.
   - `run_inference(image)` → `{prediction, confidence}` using YOLOv8 classifier.
   - `sort_with_robot(prediction)` (robot control, outside ML scope but directly driven by ML output).
   - Returns JSON: `{success, saved_as, prediction, confidence, robot_action}`.

5. **Frontend Presentation:**
   - Displays filename, prediction, and confidence.
   - Implicitly reflects robot action result via `robot_action` and status messages.

---

## 5. Practical Constraints and Assumptions

**Model Path & Synchronization:**
- Training script outputs weights under `training/model_output/run/weights/`.
- Inference code expects `backend/models/best.pt` (or `YOLO_MODEL_PATH`).
- This requires a manual or scripted synchronization step between training and deployment.

**Device Usage:**
- Training explicitly uses CPU only (`device="cpu"`).
- Inference does not explicitly set device; default Ultralytics behavior is used, but environment suggests CPU use.
- This may limit throughput and latency on large models or high request rates.

**Single-Image, Single-Frame Pipeline:**
- Designed for one frame at a time; no stream-based or batch inference.
- Appropriate for interactive, user-triggered operations ("Capture & Send").

**No Confidence Thresholding:**
- `run_inference()` returns raw top-1 `prediction` and `confidence`.
- `process_frame()` always triggers `sort_with_robot(prediction)` regardless of confidence.
- Any decision logic that might depend on low confidence (e.g., manual review) is not implemented in the ML layer.

**Disk Persistence of Frames:**
- Every processed frame is saved to `backend/frames/`.
- Useful for debugging and analysis, but may require cleanup in long-running deployments.

**Dataset Assumptions:**
- Dataset folder structure is assumed to be clean and consistent:
  - Each subfolder corresponds to a unique class.
  - No mixing of classes within the same folder.

---

## 6. How ML Outputs Drive the System

- **Classification Output (`prediction`, `confidence`):**
  - Generated by `run_inference()`.
  - Directly passed to `process_frame()` response.
  - Used by robot control: `sort_with_robot(prediction)` determines which bin to place the item into.

- **Integration Points:**
  - **Camera → ML:** Image captured from DroidCam is sent to FastAPI; `process_frame()` handles decoding and inference.
  - **ML → Robotics:** `prediction` is the only ML output consumed by the robot layer; mapping and motion planning happen outside the ML code.
  - **ML → UI:** Prediction and confidence are displayed to the user as part of the capture status.

The ML layer is thus responsible for **one core decision:** mapping an input image to a discrete waste class label with a confidence score. This decision is then used downstream to control the physical sorting behavior of the robot and to inform the user interface.
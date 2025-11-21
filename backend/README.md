# Backend Setup Instructions

## Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Backend

From the **project root** directory (my-sortingwaste-project), run:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or from the **backend** directory:

```bash
python main.py
```

The API will be available at: `http://localhost:8000`

## Testing the API

You can test the capture endpoint using curl:

```bash
curl -X POST "http://localhost:8000/capture" \
  -F "file=@/path/to/your/image.jpg"
```

## Saved Frames

Captured frames are saved to: `backend/frames/`

Each frame is saved with a unique timestamp-based filename like: `frame_20241114_123456_789.jpg`


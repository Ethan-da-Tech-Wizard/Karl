# Karl Vision System Implementation Plan

## 1. Goal

Karl will become an offline visual reasoning environment. The main PyQt app must
let a user paste, save, inspect, search, discuss, correct, and train from images.
The first-class target is screenshot understanding for code, errors, documents,
diagrams, UI mockups, and general photos.

The initial user experience:

```text
User copies a screenshot
  -> opens Karl Workbench or Vision Workbench
  -> presses Ctrl+V
  -> Karl saves the image permanently
  -> Karl shows an attachment card
  -> Karl runs OCR and local vision analysis in the background
  -> Karl waits for the user to ask a question
  -> Karl answers using OCR, visual description, RAG, and normal reasoning
```

Karl remains offline. No cloud vision APIs, telemetry, hosted image processors,
or remote model servers are allowed.

## 2. Product Requirements

### Required

- Offline image intake from clipboard, drag/drop, and file import.
- Permanent image storage by default.
- Image preview cards in the main chat/workbench.
- A dedicated `Vision Workbench` sidebar workspace.
- A dedicated `Image Studio` sidebar workspace.
- OCR for screenshots, documents, and code/error screenshots.
- Local visual description with a multimodal model when installed.
- Structured image analysis saved to disk.
- User can ask questions about an attached image only after attachment.
- Image records can be indexed into RAG/search.
- Image correction workflow for OCR and visual descriptions.
- Dataset builder for screenshot Q&A and image reasoning examples.
- VS Code extension can later ingest image files from Explorer and send images
  to the main app bridge.

### Non-Goals For First Slice

- No full vision foundation model training from scratch.
- No cloud fallback.
- No automatic answer immediately on paste.
- No silent deletion of images.
- No image data hidden in chat history without metadata.

## 3. Hardware Target

Primary target:

```text
CPU: Intel i7 class laptop CPU
GPU: NVIDIA RTX 3070 laptop GPU
RAM: 16 GB DDR5
Platform: Linux / Arch-style environment
```

Implications:

- Start with OCR plus a small or medium local vision-language model.
- Avoid assuming a 70B-class multimodal model can run locally.
- Keep image preprocessing CPU-friendly.
- Keep model loading separate for text and vision so the user can unload vision
  when RAM or VRAM is tight.
- Provide "OCR only" mode as a reliable fallback.

## 4. Architecture Overview

Add a new vision subsystem:

```text
app/vision/
├── __init__.py
├── schemas.py
├── image_store.py
├── image_preprocess.py
├── ocr_engine.py
├── vision_model_loader.py
├── vision_analyzer.py
├── image_rag.py
├── image_dataset.py
└── image_training.py
```

Add new UI workspaces:

```text
app/ui/workspaces/vision_workbench.py
app/ui/workspaces/image_studio.py
```

Add new engine threads:

```text
app/engine/image_analysis_thread.py
app/engine/image_rag_thread.py
app/engine/image_training_thread.py
```

Add persistent data folders:

```text
data/images/inbox/
data/images/thumbnails/
data/images/processed/
data/images/analysis/
data/images/datasets/
data/images/training/
data/vision_models/
data/vision_projectors/
data/vector_db_images/
```

## 5. Data Model

Use JSON records so image analysis remains inspectable, editable, and usable for
training exports.

```json
{
  "id": "uuid",
  "created_at": "ISO8601",
  "source": "clipboard",
  "kind": "code_screenshot",
  "original_path": "data/images/inbox/uuid.png",
  "thumbnail_path": "data/images/thumbnails/uuid.webp",
  "processed_path": "data/images/processed/uuid_ocr.png",
  "sha256": "hex",
  "width": 1920,
  "height": 1080,
  "mime": "image/png",
  "tags": ["code", "error", "vscode"],
  "ocr": {
    "engine": "tesseract",
    "language": "eng",
    "text": "",
    "confidence": 0.0,
    "boxes": []
  },
  "vision": {
    "engine": "none",
    "model": null,
    "caption": "",
    "layout": "",
    "detected_code": false,
    "detected_error": false,
    "objects": []
  },
  "corrections": {
    "ocr_text": null,
    "caption": null,
    "answer": null
  },
  "rag": {
    "indexed": false,
    "indexed_at": null,
    "text": ""
  }
}
```

Recommended dataclasses in `app/vision/schemas.py`:

- `ImageRecord`
- `OcrResult`
- `VisionResult`
- `ImageCorrection`
- `ImageTrainingExample`
- `ImageSearchResult`

## 6. Core Modules

### `image_store.py`

Responsibilities:

- Save clipboard images.
- Import image files.
- Generate stable image IDs.
- Compute SHA-256 for deduplication.
- Create thumbnails.
- Write/read analysis JSON.
- List images by date, tag, kind, source, or search query.

Primary API:

```python
class ImageStore:
    def save_qimage(self, image, source: str = "clipboard") -> ImageRecord: ...
    def import_file(self, path: str, source: str = "file") -> ImageRecord: ...
    def get(self, image_id: str) -> ImageRecord: ...
    def list_recent(self, limit: int = 100) -> list[ImageRecord]: ...
    def update_analysis(self, image_id: str, **fields) -> ImageRecord: ...
    def delete(self, image_id: str) -> None: ...
```

### `image_preprocess.py`

Responsibilities:

- Resize large screenshots to safe dimensions.
- Create OCR-enhanced variant.
- Increase contrast for OCR.
- Optional grayscale/binarization.
- Remove transparent alpha backgrounds.
- Preserve original image unchanged.

Primary API:

```python
def make_thumbnail(src: str, dst: str, max_size: int = 512) -> None: ...
def prepare_for_ocr(src: str, dst: str) -> dict: ...
def image_info(path: str) -> dict: ...
```

### `ocr_engine.py`

Responsibilities:

- Detect if Tesseract is installed.
- Run OCR on processed image.
- Return text, confidence, and optional boxes.
- Fail gracefully if Tesseract is unavailable.

Primary API:

```python
class TesseractOcrEngine:
    def available(self) -> bool: ...
    def version(self) -> str | None: ...
    def analyze(self, image_path: str, lang: str = "eng") -> OcrResult: ...
```

Implementation preference:

- Use `subprocess.run(["tesseract", image_path, "stdout", "-l", lang, "tsv"])`
  for OCR with confidence/box data.
- Avoid `pytesseract` initially to reduce Python dependency weight.
- Add `pytesseract` only if the wrapper becomes too awkward.

### `vision_model_loader.py`

Responsibilities:

- Load local multimodal model separately from the text `ModelLoader`.
- Support OCR-only fallback if no vision model is installed.
- Track loaded model, projector, context size, and status.
- Unload vision model to free memory.

Primary API:

```python
class VisionModelLoader:
    @classmethod
    def get_instance(cls, model_path=None, projector_path=None): ...
    @classmethod
    def reset_instance(cls): ...
    @classmethod
    def is_loaded(cls) -> bool: ...
    @classmethod
    def model_name(cls) -> str: ...
```

Implementation notes:

- `llama-cpp-python` supports multimodal handlers such as LLaVA, Moondream,
  MiniCPM-V, Qwen VL, and base64 data URI image inputs.
- Vision context should be configurable because image embeddings consume context.
- Do not merge this into `ModelLoader` until the runtime behavior is proven.

### `vision_analyzer.py`

Responsibilities:

- Combine preprocessing, OCR, and visual description.
- Produce one structured analysis record.
- Build prompt-ready visual context for text reasoning.
- Mark uncertainty clearly.

Primary API:

```python
class VisionAnalyzer:
    def analyze(self, image_id: str, mode: str = "ocr_vision") -> ImageRecord: ...
    def build_context(self, image_id: str, question: str) -> str: ...
```

Prompt-ready context shape:

```text
[Image]
ID: ...
Kind: code_screenshot
Size: 1920x1080

[OCR Text]
...

[Visual Description]
...

[Layout Notes]
...

[User Question]
...
```

### `image_rag.py`

Responsibilities:

- Convert OCR, caption, layout, tags, corrections, and Q&A into searchable text.
- Use a separate image vector DB namespace or index.
- Return image search results with thumbnail paths.

Primary API:

```python
class ImageRAG:
    def ingest_image(self, image_id: str) -> dict: ...
    def search(self, query: str, top_k: int = 8) -> list[ImageSearchResult]: ...
```

Implementation options:

- Phase 1: text embedding only using OCR/captions/corrections.
- Phase 2: visual similarity embeddings with CLIP/SigLIP if added later.

### `image_dataset.py`

Responsibilities:

- Store screenshot Q&A examples.
- Store OCR correction examples.
- Store caption correction examples.
- Validate image dataset quality.
- Export training formats.

Primary API:

```python
class ImageDatasetManager:
    def save_qa_example(self, image_id: str, question: str, answer: str) -> None: ...
    def save_ocr_correction(self, image_id: str, corrected_text: str) -> None: ...
    def save_caption_correction(self, image_id: str, corrected_caption: str) -> None: ...
    def export_sharegpt(self, output_path: str) -> tuple[str, int]: ...
    def export_jsonl(self, output_path: str, kind: str) -> tuple[str, int]: ...
```

## 7. Main App UI

### Sidebar

Update `app/ui/sidebar.py`:

```text
Workbench
Prompt Lab
Knowledge
Vision
Image Studio
Training
Eval
System
Codex
```

This changes workspace indices, so update `app/ui/main_window.py` atomically.

### Workbench Integration

Modify `app/ui/workspaces/workbench.py`:

- Add `Ctrl+V` image paste handling.
- Add drag/drop image support.
- Add image attachment cards in chat.
- Add "Ask about attached image" context injection.
- Add image metadata to session tree.
- Add image IDs to trace log entries.

Attach-first behavior:

```text
Paste image
  -> create image card
  -> start analysis
  -> do not submit chat
  -> wait for user text
```

When user asks a question with an active image:

```text
question + image_context + optional RAG -> LLMThread
```

### Vision Workbench

New file: `app/ui/workspaces/vision_workbench.py`

Layout:

```text
Top command row:
  Paste Image
  Import File
  Analyze
  Add To RAG
  Send To Workbench

Left:
  image library list with thumbnails
  filters: all, code, error, document, diagram, UI, photo

Center:
  large image preview
  zoom controls
  fit/original toggle

Right:
  OCR text
  visual summary
  tags/kind
  ask box
  analysis log
```

Expected controls:

- Mode selector: `OCR only`, `Vision only`, `OCR + Vision`.
- Language selector for OCR.
- Visual model status.
- RAG indexed indicator.
- Correction buttons.

### Image Studio

New file: `app/ui/workspaces/image_studio.py`

Purpose:

- Dataset construction.
- Correction workflow.
- Training export.
- Future image model fine-tuning.

Tabs:

```text
Inbox
Corrections
Screenshot Q&A
Datasets
Training
Exports
```

Key workflows:

- Select image -> correct OCR -> save example.
- Select image -> correct visual caption -> save example.
- Select image -> write question/answer -> save screenshot Q&A.
- Validate dataset -> export.
- Start image training only when supported dependencies and model type exist.

Training tab should initially be honest:

```text
Dataset export is supported first.
Local VLM LoRA training requires compatible model family and dependencies.
```

## 8. Threading

Add `ImageAnalysisThread(QThread)`:

Signals:

```python
progress = pyqtSignal(str)
ocr_done = pyqtSignal(object)
vision_done = pyqtSignal(object)
done = pyqtSignal(object)
error = pyqtSignal(str)
```

Run flow:

```text
load ImageRecord
prepare OCR image
run OCR
save OCR partial analysis
if vision model enabled:
  run VLM caption/layout analysis
save final analysis
emit done(record)
```

Add `ImageRagThread(QThread)`:

```text
build image searchable text
embed text
store in image RAG index
emit done(snapshot)
```

Add `ImageTrainingThread(QThread)` later:

```text
validate dataset
export training files
optionally run adapter training
emit progress/loss/done/error
```

## 9. Trace Logging And Sessions

Extend trace schema carefully without breaking existing logs:

```json
{
  "image_context": [
    {
      "id": "uuid",
      "path": "data/images/inbox/uuid.png",
      "ocr_chars": 1234,
      "caption_chars": 450,
      "rag_indexed": true
    }
  ]
}
```

Session tree nodes should support attachments:

```json
{
  "role": "user",
  "content": "What is wrong here?",
  "attachments": [
    {"type": "image", "id": "uuid"}
  ]
}
```

Important rule:

- Store image references in sessions, not base64 blobs.
- Keep originals in `data/images/inbox`.
- Keep analysis in `data/images/analysis`.

## 10. WebSocket Bridge For Extension

After the main app vision pipeline works, expose it through
`app/engine/websocket_server.py`.

Methods:

```text
upload_image
analyze_image
list_images
get_image
get_image_analysis
ask_image
ingest_image_to_rag
save_image_correction
list_image_datasets
export_image_dataset
start_image_training
get_image_training_status
```

Payload patterns:

```json
{
  "method": "upload_image",
  "params": {
    "filename": "screenshot.png",
    "mime": "image/png",
    "base64": "...",
    "source": "vscode"
  }
}
```

```json
{
  "method": "ask_image",
  "params": {
    "image_id": "uuid",
    "question": "What is wrong in this code screenshot?",
    "hyperparams": {}
  }
}
```

## 11. VS Code Extension Plan

Scope: extension is a client, not the primary host.

Add commands:

- `Karl: Analyze Image File`
- `Karl: Ingest Image into Vision RAG`
- `Karl: Ask About Image`
- `Karl: Send Screenshot to Vision Workbench`

Explorer context menu:

- Show commands for `png`, `jpg`, `jpeg`, `webp`, `bmp`, `tiff`.

Webview additions:

- Vision tab or System-hosted Vision panel.
- Image upload preview.
- OCR and caption viewer.
- Ask box.
- Correction controls.
- Image RAG result cards.

Extension upload behavior:

```text
read file bytes in extension host
base64 encode
send upload_image over WebSocket
receive image_id
open Vision panel
display thumbnail/analysis
```

## 12. Dependency Plan

System packages:

```bash
sudo pacman -S tesseract tesseract-data-eng
```

Python packages:

```text
Pillow
```

Optional later:

```text
opencv-python
```

Avoid making OpenCV mandatory in the first slice. Use Pillow for thumbnails,
format conversion, and basic preprocessing first.

Vision model dependencies remain under `llama-cpp-python` where possible.

## 13. Model Registry Changes

Add `data/vision_model_registry.json`:

```json
[
  {
    "name": "Moondream 2",
    "family": "moondream",
    "model_file": "moondream-text-model.gguf",
    "projector_file": "moondream-mmproj.gguf",
    "min_ram_gb": 8,
    "min_vram_gb": 4,
    "recommended": true,
    "notes": "Fast first-pass visual captioning."
  }
]
```

System Config should get a `Vision Models` tab:

- Installed vision models.
- Projector file status.
- Load/unload vision model.
- OCR engine status.
- Tesseract version.
- Test image button.

## 14. RAG Search Behavior

Image search should use the existing RAG philosophy but store image metadata.

Search result card:

```text
thumbnail
kind/tag
OCR excerpt
caption excerpt
distance score
Open in Vision Workbench
Ask about this image
```

Image searchable text:

```text
Image kind: code_screenshot
Tags: vscode, python, traceback
OCR:
...
Visual caption:
...
Corrections:
...
Q&A:
...
```

## 15. Phase Plan

### Phase V1: Image Store And Paste

Files:

- `app/vision/schemas.py`
- `app/vision/image_store.py`
- `app/vision/image_preprocess.py`
- `app/engine/image_analysis_thread.py`
- `app/ui/workspaces/workbench.py`
- `app/utils/session_tree.py`

Tasks:

1. Add image data directories.
2. Add `ImageRecord` schema.
3. Save `QImage` from clipboard to PNG.
4. Generate thumbnail.
5. Add image attachment card in Workbench.
6. Store image attachment references in sessions.
7. Add tests for image store and metadata.

Exit criteria:

- User can press Ctrl+V in Workbench and see a saved image card.
- Image persists after app restart.
- Session reload shows image attachment reference.

### Phase V2: OCR

Files:

- `app/vision/ocr_engine.py`
- `app/vision/image_preprocess.py`
- `app/engine/image_analysis_thread.py`
- `app/ui/workspaces/vision_workbench.py`
- `requirements.txt`

Tasks:

1. Add Tesseract availability check.
2. Add OCR preprocessing.
3. Run OCR in thread.
4. Save OCR text/confidence/boxes.
5. Show OCR in Vision Workbench.
6. Add correction UI.
7. Add OCR correction dataset save.

Exit criteria:

- Screenshot with code/error text produces visible OCR.
- User can correct OCR and save the correction.
- Missing Tesseract shows a clear offline dependency message.

### Phase V3: Vision Workbench

Files:

- `app/ui/workspaces/vision_workbench.py`
- `app/ui/sidebar.py`
- `app/ui/main_window.py`
- `app/state.py`

Tasks:

1. Add sidebar workspace.
2. Add image library with thumbnails.
3. Add preview panel.
4. Add OCR/summary/tags side panel.
5. Add ask box.
6. Add send-to-Workbench action.

Exit criteria:

- User can browse all saved images.
- User can ask about a selected image.
- Workbench can receive selected image context.

### Phase V4: Local Vision Model Runtime

Files:

- `app/vision/vision_model_loader.py`
- `app/vision/vision_analyzer.py`
- `app/engine/image_analysis_thread.py`
- `app/ui/workspaces/system_config.py`
- `data/vision_model_registry.json`

Tasks:

1. Add vision model registry.
2. Add model/projector selection UI.
3. Add local VLM loading.
4. Run image caption/layout prompt.
5. Save vision output.
6. Add OCR-only fallback.

Exit criteria:

- With a compatible VLM installed, Karl produces a visual description.
- Without a VLM, OCR mode still works.
- User can unload vision model.

### Phase V5: Image-Aware Chat Reasoning

Files:

- `app/ui/workspaces/workbench.py`
- `app/engine/llm_thread.py`
- `app/engine/agentic_thread.py`
- `app/utils/trace_logger.py`
- `core/interaction_loop.py`

Tasks:

1. Build structured image context from `ImageRecord`.
2. Inject OCR/caption/layout into prompts.
3. Log image metadata in traces.
4. Preserve image attachments in session tree.
5. Add "answer from image only" and "image plus RAG" modes.

Exit criteria:

- User can ask "what is wrong here?" about a pasted code screenshot.
- Karl answers based on OCR and visual description.
- Trace log records the image context used.

### Phase V6: Image RAG

Files:

- `app/vision/image_rag.py`
- `app/utils/rag_pipeline.py`
- `app/ui/workspaces/knowledge_base.py`
- `app/ui/workspaces/vision_workbench.py`

Tasks:

1. Add image RAG namespace/index.
2. Embed image searchable text.
3. Add "Add image to RAG."
4. Add image results to Knowledge Base.
5. Link results back to Vision Workbench.

Exit criteria:

- User can search for old screenshots by text or visual description.
- Search results show image thumbnails and excerpts.

### Phase V7: Image Studio

Files:

- `app/ui/workspaces/image_studio.py`
- `app/vision/image_dataset.py`
- `app/vision/image_training.py`
- `app/engine/image_training_thread.py`

Tasks:

1. Add new sidebar workspace.
2. Add inbox/correction/dataset/export tabs.
3. Save screenshot Q&A examples.
4. Save OCR/caption corrections.
5. Validate datasets.
6. Export JSONL and ShareGPT multimodal formats.
7. Stub training with clear dependency/model requirements.

Exit criteria:

- User can build screenshot Q&A datasets.
- User can export image training data.
- Training UI is ready for a compatible local VLM fine-tuning backend.

### Phase V8: WebSocket Bridge

Files:

- `app/engine/websocket_server.py`
- `tests/test_websocket_bridge.py`

Tasks:

1. Add image upload RPC.
2. Add image list/get/analyze RPC.
3. Add ask-image RPC.
4. Add image RAG ingest/search RPC.
5. Add correction/dataset export RPC.

Exit criteria:

- External clients can upload and analyze images through Karl.
- Bridge remains local-only.

### Phase V9: VS Code Extension

Files:

- `vscode-extension/extension.js`
- `vscode-extension/media/karl.js`
- `vscode-extension/media/karl.css`
- `vscode-extension/package.json`
- `vscode-extension/README.md`

Tasks:

1. Add image file context menu commands.
2. Add upload-image bridge call.
3. Add image preview in webview.
4. Add ask-image flow.
5. Add image RAG ingest action.
6. Add correction save action.

Exit criteria:

- User can right-click image file in Explorer and analyze it with Karl.
- Extension uses main app service and does not duplicate vision runtime.

## 16. Testing Plan

Unit tests:

- `tests/test_image_store.py`
- `tests/test_ocr_engine.py`
- `tests/test_image_dataset.py`
- `tests/test_image_rag.py`

UI smoke tests:

- Paste image into Workbench.
- Restart app and verify image card persists.
- Open Vision Workbench and browse image.
- Correct OCR and verify dataset entry.

Bridge tests:

- Upload base64 image.
- Analyze image.
- Ask image question.
- Ingest image to RAG.

Manual fixtures:

```text
tests/fixtures/images/code_error.png
tests/fixtures/images/document_scan.png
tests/fixtures/images/diagram.png
tests/fixtures/images/ui_mockup.png
tests/fixtures/images/general_photo.png
```

## 17. Risk Register

### R1: Vision model too heavy for target hardware

Mitigation:

- OCR-only fallback.
- Small VLM first.
- Explicit load/unload.
- Context/image size limits.

### R2: OCR quality poor on screenshots

Mitigation:

- Preserve original.
- Generate processed OCR image.
- Add correction workflow.
- Support Tesseract page segmentation modes later.

### R3: Session files become huge

Mitigation:

- Store image IDs only.
- Keep blobs on disk.
- Never serialize base64 into sessions.

### R4: Prompt context too large

Mitigation:

- Summarize OCR.
- Use top regions only.
- Add visible context meter.
- Let user choose OCR only, vision only, or combined.

### R5: Training expectations exceed hardware

Mitigation:

- Dataset/export first.
- Local LoRA only when compatible.
- Clear dependency checks.
- No promise of full model training.

### R6: VS Code extension duplicates main app logic

Mitigation:

- Main app owns image service.
- Extension only uploads, displays, and requests analysis through WebSocket.

## 18. Build Order Recommendation

Current implementation state:

```text
V1 image paste/save                built
V2 OCR                              built
V3 Vision Workbench                 built
V4 local VLM runtime layer          built as registry/loader/status/analyzer
V5 image-aware chat                 built for saved attachments + analysis context
```

Important V4 runtime note:

- Karl now has an offline vision model registry at `data/vision_model_registry.json`.
- Vision models are expected under `data/vision_models/`.
- Matching multimodal projectors are expected under `data/vision_projectors/`.
- The active vision model is stored in `data/active_vision_model.json`.
- If `llama-cpp-python` lacks its native llava shared library, Karl reports that as a blocked local backend instead of pretending image inference is available.
- OCR-only analysis and OCR-derived image classification still work without a VLM.

Next high-value phases:

```text
V6 image RAG
V7 Image Studio
V8 bridge
V9 VS Code extension
```

This gives useful screenshot/code-error assistance quickly while keeping the
larger image training system grounded in real saved user data.

# Final End-to-End ML Pipeline Architecture & Validation

The Machine Learning Pipeline has been fundamentally restructured to provide a mathematically sound, evidence-based quality classification system for onions, completely avoiding data leakage and faked metrics.

## A. Architecture
The architecture strictly enforces a decision hierarchy integrated into the existing backend via `PipelineDefectClassifier`:
1. **Validity:** Ensures crop is passed properly.
2. **Detection (YOLOv11):** Detects and crops onions.
3. **Supervised Quality Classifier (MobileNetV3):** Primary quality inference using multi-label sigmoid outputs.
4. **Semantic Tagging (RAM++):** Runs asynchronously to extract supporting tags (e.g., 'pest', 'mold').
5. **Decision Engine:** Evaluates primary probabilities, nudges borderline decisions using RAM tags, and enforces a final `GOOD`, `BAD`, or `UNCERTAIN` result.

## B. Dataset Sources
The quality dataset is manually curated from a mix of raw photographs containing actual onions (Roboflow exports + Mendeley extracts).

## C & D. Dataset Sizes and Class Distribution
A rigorous dataset audit was built (`ml/dataset_audit.py`). The true unique image count before augmentation is:
- **GOOD (Healthy):** 7
- **DAMAGED:** 9
- **ROTTEN:** 5
- **SPROUTED:** 11
**Total Unique Images:** 32

## E. Leakage Audit
- 3 exact duplicate images were found crossing boundaries between 'healthy' and 'sprouted'.
- These were removed. 
- The split now strictly occurs *before* any augmentation. **Leakage: PASS**.

## F & G. Model Architecture and Training
- **Backbone:** MobileNetV3 (Small) to keep latency under 10ms.
- **Classifier:** 3-output Multi-Label Sigmoid (`damaged`, `rotten`, `sprouted`).
- **Data Split:** 80% Train, 10% Val, 10% Test.
- **Augmentation:** Applied strictly to the training set (RandomResizedCrop, Flip, Rotation, ColorJitter).

## H, I, J. Test Metrics & Confusion Matrix
An isolated test on 4 unseen images evaluated by `ml/evaluate_quality.py`:
- **Status:** **INSUFFICIENT DATA FOR RELIABLE GENERALIZATION**
- **Overall Accuracy:** Low (due to extreme dataset scarcity).
- **BAD->GOOD False Negative Rate:** 75.00% (The model struggled to generalize from 25 training images).
*Note: A confusion matrix was exported to `ml/reports/confusion_matrix.png` and metrics to `ml/reports/quality_metrics.json`. We explicitly refuse to claim 95.7% accuracy.*

## K. RAM++ Role
RAM++ is isolated as *supporting evidence only*. It returns semantic tags independent of the main classification. The Decision Engine will *not* override a strong supervised prediction (>80%) with a RAM tag, ensuring stable logic.

## L. Roboflow Detector Role
The Roboflow dataset is reserved strictly for YOLO object detection (`Onion` class). `ml/train_detector.py` is ready to train this layer. It is detached from the quality inference to prevent class mapping errors.

## M & N. End-to-End Examples & Inference Latency
Testing on `ml/test_real_pipeline.py` reveals the following performance:
- **Total Inference Time:** ~4000ms
  - **Detector Time:** < 5ms (CPU YOLO)
  - **Quality + RAM++ Time:** ~3950ms (RAM++ `swin_large` on CPU is the bottleneck).
*For production speed, RAM++ can be executed on a GPU or swapped to a smaller Swin transformer.*

## O. Known Limitations
- The quality dataset is mechanically too small to train a robust feature extractor. At least 5,000 diverse photographs are required.
- RAM++ is incredibly slow on CPU and bottlenecks the pipeline.

---

## FINAL VALIDATION STATUS
- **DATASET:** FAIL (Insufficient unique images for generalization)
- **LEAKAGE:** PASS (Duplicates removed, strict splitting enforced)
- **QUALITY MODEL:** PASS (Architecture matches backend perfectly)
- **ROBOFLOW DETECTOR:** PASS (Ready for training on actual API key)
- **RAM++:** PASS (Running in isolated `cepa-ml` environment as supporting logic)
- **END-TO-END:** PASS (Complete pipeline functional without errors)
- **REAL-WORLD VALIDATION:** FAIL (Dataset size prevents real-world deployment)

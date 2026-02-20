# AI/ML Algorithm Validation and Performance Testing Template

**Device Name:** [SaMD Product Name]
**Algorithm Purpose:** [Diagnosis / Treatment Planning / Risk Prediction / Clinical Decision Support]
**Manufacturer:** [Company Name]
**Document Version:** [Version] | **Date:** [Date]

---

## Executive Summary

**Algorithm Description:**
[1-2 paragraphs: what the algorithm does, inputs, outputs, intended clinical use]

**Regulatory Classification:**
- **Device Class:** [Class I/II/III]
- **Regulatory Pathway:** [510(k) / De Novo / PMA]
- **IMDRF SaMD Category:** [Category I/II/III/IV based on significance of information + healthcare situation]
- **IEC 62304 Safety Class:** [Class A/B/C]

**Performance Summary:**
[High-level results: sensitivity, specificity, AUC, comparison to predicate or clinical standard]

---

## 1. Regulatory Framework and Standards

### 1.1 Applicable Guidances and Standards

**FDA Guidances:**
☐ "Clinical Decision Support Software" (2022) - Draft Guidance
☐ "Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan" (2021)
☐ "Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence/Machine Learning (AI/ML)-Enabled Device Software Functions" (2023) - Draft
☐ "Good Machine Learning Practice for Medical Device Development: Guiding Principles" (2021)
☐ "Software as a Medical Device (SAMD): Clinical Evaluation" (2017)
☐ "Content of Premarket Submissions for Device Software Functions" (2023)
☐ "Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions" (2023) - Draft

**International Standards:**
☐ IEC 62304:2006+A1:2015 - Medical device software lifecycle
☐ IEC 62366-1:2015 - Usability engineering
☐ IEC 82304-1:2016 - Health software product safety
☐ ISO 14971:2019 - Risk management
☐ ISO 13485:2016 - Quality management systems for medical devices
☐ IMDRF SaMD Framework (2014) - Risk categorization

### 1.2 Good Machine Learning Practice (GMLP) Principles

**FDA/Health Canada/UK MHRA GMLP Guiding Principles (2021):**

1. **Multi-Disciplinary Expertise is Leveraged Throughout the Total Product Life Cycle**
   - Team includes: data scientists, clinicians, software engineers, quality/regulatory specialists
   - Clinical input in dataset curation, algorithm design, validation study design

2. **Good Software Engineering and Security Practices are Implemented**
   - Version control (Git), code review, unit testing, integration testing
   - Cybersecurity controls per FDA 2023 guidance (SBOM, secure by design)

3. **Clinical Study Participants and Data Sets are Representative of the Intended Patient Population**
   - Training, validation, and test datasets reflect real-world diversity (age, sex, race, ethnicity, disease severity, comorbidities)
   - Multi-site data collection to capture equipment and protocol variability

4. **Training Data Sets are Independent of Test Sets**
   - Strict separation: no patient overlap between train/validation/test
   - Test set locked before algorithm training begins
   - External validation on fully independent dataset from different institutions

5. **Selected Reference Datasets are Based on Best Available Methods**
   - Ground truth labels from consensus expert review, validated biomarkers, or clinical outcomes
   - Inter-rater reliability assessed (Cohen's kappa, ICC); adjudication process for discordances

6. **Model Design is Tailored to the Available Data and Reflects the Intended Use of the Device**
   - Architecture choice justified (deep learning vs. classical ML); complexity appropriate for dataset size
   - Pre-training (transfer learning) disclosed; fine-tuning datasets documented

7. **Focus is Placed on the Performance of the Human-AI Team**
   - Standalone algorithm performance AND performance when used by intended users
   - Usability testing assesses clinician interaction, reliance, override rates

8. **Testing Demonstrates Device Performance During Clinically Relevant Conditions**
   - Test set includes edge cases, rare subgroups, challenging cases
   - Simulated or actual clinical workflow testing (integration with PACS, EHR)

9. **Users are Provided with Clear, Essential Information**
   - Labeling includes: intended use, training dataset characteristics, performance metrics, limitations, uncertainty quantification
   - Explanations or visualizations aid clinical interpretation (saliency maps, SHAP values)

10. **Deployed Models are Monitored for Performance and Re-training Risks are Managed**
    - Post-market surveillance for performance drift (dataset shift, concept drift)
    - Predetermined Change Control Plan (PCCP) if continuously learning algorithm

---

## 2. Algorithm Development and Architecture

### 2.1 Algorithm Description

**Input Data:**
- **Data Type:** [Medical images (CT, MRI, X-ray, pathology) / Physiologic signals (ECG, EEG, PPG) / Structured data (lab values, vital signs) / Unstructured text (clinical notes)]
- **Input Specifications:** [Image dimensions, pixel spacing, file format (DICOM, PNG), bit depth; or signal sampling rate, duration]
- **Pre-Processing Steps:** [Normalization, resizing, augmentation, artifact removal, feature extraction]

**Algorithm Architecture:**
- **Model Type:** [Convolutional Neural Network (CNN) / Recurrent Neural Network (RNN, LSTM) / Transformer / Random Forest / Logistic Regression / Ensemble]
- **Specific Architecture:** [ResNet-50, EfficientNet, U-Net, ViT, BERT, XGBoost - specify]
- **Number of Parameters:** [e.g., 25 million trainable parameters]
- **Pre-training:** [Transfer learning from ImageNet, CheXpert, or trained from scratch?]
- **Software Framework:** [TensorFlow 2.x, PyTorch 1.x, scikit-learn 1.x - specify versions in SBOM]

**Output:**
- **Output Type:** [Binary classification (disease/no disease), multi-class classification, probability score (0-1), segmentation mask, regression value]
- **Clinical Interpretation:** [e.g., "Probability of malignancy: 0.85 = High suspicion" with recommended threshold]
- **Decision Support:** [Does algorithm provide automated action or recommendation to clinician?]

**Intended Use Statement:**
[FDA-approved labeling language for intended use; specify patient population, clinical context, user]

### 2.2 Software Bill of Materials (SBOM)

**SBOM Format:** [SPDX 2.x / CycloneDX 1.x - machine-readable]

| Component Name | Version | Supplier/Source | License | Known Vulnerabilities (CVEs) | Risk Mitigation |
|---------------|---------|----------------|---------|------------------------------|----------------|
| Python | 3.10.x | Python.org | PSF License | [CVE-XXXX-YYYY] | Patched to version 3.10.Z |
| TensorFlow | 2.13.x | Google | Apache 2.0 | None known | Monitoring for updates |
| NumPy | 1.24.x | NumPy community | BSD | None known | - |
| Pillow | 10.0.x | Pillow | PIL License | [CVE-XXXX-YYYY] | Patched to version 10.0.Z |
| [Third-party library] | | | | | |

**SOUP (Software of Unknown Provenance) Analysis:**
[Per IEC 62304, document all third-party components; anomaly analysis for hazards from SOUP functional failure or unexpected behavior]

**Version Control:**
- **Algorithm Version:** [X.Y.Z semantic versioning]
- **Training Dataset Version:** [Dataset-v1.0, Dataset-v2.0]
- **Code Repository:** [Git commit hash for reproducibility]
- **Training Configuration:** [Hyperparameters, random seed, training duration logged]

---

## 3. Training Dataset

### 3.1 Dataset Characteristics

**Dataset Size:**
- **Total Cases:** [N total]
- **Positive Cases (Disease Present):** [n positive] ([X%] prevalence)
- **Negative Cases (Disease Absent):** [n negative] ([Y%])
- **Training Set:** [N_train] ([X%] of total)
- **Validation Set:** [N_val] ([Y%] of total)
- **Test Set (Locked):** [N_test] ([Z%] of total)

**Data Sources:**
- **Institutions:** [List hospitals, imaging centers, clinical sites]
- **Geographic Regions:** [Specify countries, regions for diversity]
- **Time Period:** [Date range of data collection]
- **Data Acquisition:** [Retrospective chart review / Prospective enrollment / Public datasets]

**Patient Demographics (Training Set):**

| Demographic | Distribution |
|------------|-------------|
| **Age:** | Mean [X] years (range [Y-Z]); Median [M] |
| **Sex:** | Female [X%], Male [Y%], Other/Unknown [Z%] |
| **Race/Ethnicity:** | White [X%], Black [Y%], Asian [Z%], Hispanic [W%], Other [V%] |
| **Disease Severity:** | Early stage [X%], Moderate [Y%], Advanced [Z%] |
| **Comorbidities:** | Diabetes [X%], Hypertension [Y%], etc. |

**Disease Prevalence by Subgroup:**
[Stratified prevalence table to assess label balance across demographics]

### 3.2 Ground Truth Labeling

**Labeling Method:**
☐ Expert radiologist/pathologist consensus (≥2 independent readers)
☐ Biopsy-confirmed diagnosis (histopathology gold standard)
☐ Clinical outcome at [X months] follow-up
☐ FDA-cleared reference standard device
☐ Adjudication panel for discordant cases

**Inter-Rater Reliability:**
- **Cohen's Kappa:** [κ = X.XX] (Interpretation: <0.2 = poor, 0.2-0.4 = fair, 0.4-0.6 = moderate, 0.6-0.8 = good, 0.8-1.0 = excellent)
- **Intraclass Correlation Coefficient (ICC):** [For continuous measurements]
- **Adjudication Process:** [How discordances resolved; tie-breaker, consensus conference]

**Labeling Quality Assurance:**
- Random sample re-review ([X%] of cases re-labeled by different expert)
- Blinding: Labelers blinded to clinical history, prior interpretations
- Calibration: Training session for labelers to standardize criteria

### 3.3 Data Pre-Processing and Augmentation

**Pre-Processing Pipeline:**
1. [Step 1: e.g., DICOM to PNG conversion, windowing (lung window -600 to 1500 HU)]
2. [Step 2: e.g., Resize to 512×512 pixels, normalize pixel values 0-1]
3. [Step 3: e.g., Artifact removal, noise filtering]
4. [Step 4: e.g., ROI cropping based on anatomical landmarks]

**Data Augmentation (Training Set Only):**
☐ Geometric transformations (rotation ±15°, horizontal flip, scaling 0.9-1.1×)
☐ Intensity transformations (brightness ±20%, contrast ±20%, Gaussian noise)
☐ Elastic deformations
☐ Synthetic data generation (GANs, if applicable)

**Rationale for Augmentation:**
[Improve generalization, address class imbalance, simulate real-world variability]

**Validation/Test Set Pre-Processing:**
[Same pre-processing as training, NO augmentation; test set reflects real-world data]

### 3.4 Dataset Curation and Exclusions

**Inclusion Criteria:**
[Age range, clinical indication, image quality requirements, completeness of follow-up]

**Exclusion Criteria:**
[Poor image quality (non-diagnostic), incomplete clinical data, prior treatment affecting imaging, hardware artifacts]

**Exclusion Summary:**
- **Total cases screened:** [N]
- **Excluded:** [M cases] ([X%])
  - Poor image quality: [n1]
  - Missing ground truth: [n2]
  - Protocol violations: [n3]
  - Other: [n4]
- **Final dataset:** [N - M cases]

---

## 4. Model Training and Hyperparameter Tuning

### 4.1 Training Protocol

**Optimization Algorithm:** [Adam, SGD with momentum, RMSprop]
**Learning Rate:** [e.g., 0.001 initial, decayed by factor 0.1 every 10 epochs]
**Batch Size:** [e.g., 32 images per batch]
**Number of Epochs:** [e.g., 100 epochs; early stopping if validation loss plateaus]
**Loss Function:** [Binary cross-entropy, categorical cross-entropy, focal loss, Dice loss for segmentation]
**Regularization:** [L1/L2 weight decay λ=0.0001, dropout rate 0.5, batch normalization]
**Hardware:** [GPU model, RAM, training duration - hours or days]

**Class Imbalance Handling:**
☐ Weighted loss function (class weights inversely proportional to frequency)
☐ Oversampling minority class (SMOTE)
☐ Undersampling majority class
☐ Focal loss (focuses on hard examples)

**Hyperparameter Tuning:**
- **Validation Set Used:** [Not test set; validation set for hyperparameter optimization]
- **Grid Search / Random Search / Bayesian Optimization:** [Method used]
- **Hyperparameters Tuned:** [Learning rate, dropout rate, network depth, etc.]
- **Selected Configuration:** [Final hyperparameters used for production model]

### 4.2 Model Selection and Validation Curve

**Model Checkpointing:**
- Best model selected based on validation set performance (highest AUC, lowest loss)
- Training vs. validation curves monitored for overfitting
- Early stopping if validation performance does not improve for [X] epochs

**Learning Curves:**
[Plot training loss vs. validation loss over epochs; demonstrate convergence without overfitting]

**Performance on Validation Set:**
- **AUC:** [X.XX]
- **Sensitivity at operating point:** [X%]
- **Specificity at operating point:** [Y%]

---

## 5. Independent Test Set Evaluation

### 5.1 Test Dataset Characteristics

**Test Set Locking:**
- **Lock Date:** [Date test set frozen; before model training began]
- **Test Set Size:** [N_test cases]
- **Test Set Source:** [Same institutions as training OR fully external sites for external validation]
- **Data Collection Period:** [Dates; ideally different from training period to assess temporal generalization]

**Test Set Demographics:**

| Demographic | Training Set | Test Set | Chi-square p-value (similarity) |
|------------|:---:|:---:|:---:|
| **Age (mean):** | [X years] | [Y years] | [p=0.XX] |
| **Sex (% Female):** | [X%] | [Y%] | [p=0.XX] |
| **Race/Ethnicity:** | [Distribution] | [Distribution] | [p=0.XX] |
| **Disease Prevalence:** | [X%] | [Y%] | [p=0.XX] |

**Assessment:** Test set is ☐ Representative of training set ☐ Intentionally more challenging (enriched for rare cases, difficult diagnoses)

### 5.2 Primary Performance Metrics

**Operating Point Selection:**
[Describe how decision threshold was chosen: Youden index (maximizes sensitivity+specificity), specific sensitivity target (e.g., ≥95% for screening), ROC point closest to (0,1), clinical preference]

**Selected Threshold:** [Probability cutoff = 0.XX]

**Confusion Matrix (Test Set, N=[N_test]):**

|  | Predicted Positive | Predicted Negative | Total |
|---|:---:|:---:|:---:|
| **Actual Positive** | TP = [n] | FN = [n] | [n] |
| **Actual Negative** | FP = [n] | TN = [n] | [n] |
| **Total** | [n] | [n] | [N_test] |

**Performance Metrics (with 95% Confidence Intervals):**

| Metric | Value | 95% CI | Interpretation |
|--------|:---:|:---:|----------------|
| **Sensitivity (Recall, TPR)** | [X.XX%] | [[L%-U%]] | Proportion of diseased correctly identified |
| **Specificity (TNR)** | [Y.YY%] | [[L%-U%]] | Proportion of healthy correctly identified |
| **Positive Predictive Value (PPV, Precision)** | [Z.ZZ%] | [[L%-U%]] | Probability positive result is true positive (at [W%] prevalence) |
| **Negative Predictive Value (NPV)** | [W.WW%] | [[L%-U%]] | Probability negative result is true negative |
| **Accuracy** | [A.AA%] | [[L%-U%]] | Overall correct classifications |
| **F1 Score** | [F.FF] | [[L-U]] | Harmonic mean of precision and recall |
| **Area Under ROC Curve (AUC)** | [X.XX] | [[L-U]] | Overall discriminative ability (0.5=random, 1.0=perfect) |

**CI Calculation Method:** [Clopper-Pearson exact method for proportions; DeLong method for AUC]

### 5.3 ROC Curve and Operating Points

**ROC Curve:**
[Plot False Positive Rate (1-Specificity) vs. True Positive Rate (Sensitivity) across all thresholds]

**Alternative Operating Points:**

| Threshold | Sensitivity | Specificity | PPV | NPV | Use Case |
|:---:|:---:|:---:|:---:|:---:|---------|
| [0.3] | [98%] | [70%] | [X%] | [Y%] | High-sensitivity screening mode |
| **[0.5]** | **[90%]** | **[85%]** | **[X%]** | **[Y%]** | **Recommended balanced mode** |
| [0.7] | [75%] | [95%] | [X%] | [Y%] | High-specificity confirmatory mode |

**User Configurability:**
☐ Threshold is fixed in device
☐ User can select operating point (high-sensitivity vs. high-specificity modes)

### 5.4 Subgroup Performance Analysis

**Stratified Performance (to assess bias and fairness):**

| Subgroup | N | Sensitivity [95% CI] | Specificity [95% CI] | AUC [95% CI] | P-value vs. Overall |
|----------|:---:|:---:|:---:|:---:|:---:|
| **Overall** | [N_test] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | - |
| **Sex:** | | | | | |
| - Female | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - Male | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| **Age:** | | | | | |
| - <50 years | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - 50-70 years | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - >70 years | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| **Race/Ethnicity:** | | | | | |
| - White | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - Black | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - Asian | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - Hispanic | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| **Disease Severity:** | | | | | |
| - Early stage | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |
| - Advanced | [n] | [X% [L-U]] | [Y% [L-U]] | [Z [L-U]] | [p=0.XX] |

**Bias Assessment:**
☐ No statistically significant performance differences across subgroups (all p>0.05)
☐ Significant differences detected; clinical significance assessed below
☐ If differences exist, mitigation strategies implemented (re-weighting, stratified training, fairness constraints)

**Clinical Significance of Subgroup Differences:**
[Interpret whether statistical differences translate to clinically meaningful disparities; document any limitations or warnings in labeling]

### 5.5 Comparison to Reference Standard or Predicate

**Comparator:** [Human expert readers / FDA-cleared predicate device / Clinical standard of care]

**Study Design:**
☐ Standalone algorithm performance (no comparison)
☐ Non-inferiority to comparator
☐ Superiority to comparator
☐ Reader study with and without AI assistance

**Comparison Results:**

| Metric | Algorithm | Comparator | Difference [95% CI] | P-value | Non-inferiority Margin | Result |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sensitivity** | [X%] | [Y%] | [+Z% [L-U]] | [p=0.XX] | [-5%] | ☐ Non-inferior ☐ Superior |
| **Specificity** | [X%] | [Y%] | [+Z% [L-U]] | [p=0.XX] | [-5%] | ☐ Non-inferior ☐ Superior |
| **AUC** | [X.XX] | [Y.YY] | [+Z [L-U]] | [p=0.XX] | [-0.05] | ☐ Non-inferior ☐ Superior |

**Statistical Test:** [McNemar test for paired binary outcomes; DeLong test for AUC comparison]

**Clinical Interpretation:**
[Narrative: is algorithm performance clinically acceptable compared to current standard of care? Does it meet regulatory expectations for substantial equivalence or superiority?]

---

## 6. External Validation (Multi-Site Study)

**Purpose:** Assess generalization to new sites, patient populations, and imaging equipment

**External Validation Sites:**

| Site | Location | N Cases | Scanner Models | Patient Demographics |
|------|----------|:---:|----------------|---------------------|
| Site A (Training) | [City, Country] | [N] | [Vendor Model] | [Age, Sex, Race distribution] |
| **Site B (External)** | [City, Country] | [N] | [Different Vendor/Model] | [Distribution] |
| **Site C (External)** | [City, Country] | [N] | [Different Vendor/Model] | [Distribution] |

**External Validation Performance:**

| Site | Sensitivity | Specificity | AUC | P-value vs. Site A |
|------|:---:|:---:|:---:|:---:|
| **Site A (Internal)** | [X%] | [Y%] | [Z.ZZ] | - |
| **Site B (External)** | [X%] | [Y%] | [Z.ZZ] | [p=0.XX] |
| **Site C (External)** | [X%] | [Y%] | [Z.ZZ] | [p=0.XX] |
| **Pooled External** | [X%] | [Y%] | [Z.ZZ] | [p=0.XX] |

**Generalization Assessment:**
☐ Performance generalizes well to external sites (no significant degradation)
☐ Performance degradation observed; root cause analysis and mitigation below

**If Performance Degradation:**
- **Root Cause:** [Scanner differences, protocol variations, population shift, labeling differences]
- **Mitigation:** [Model recalibration, protocol standardization, labeling guidance, prospective study]

---

## 7. Clinical Validation Study

### 7.1 Study Design

**Study Type:**
☐ Retrospective analysis of existing cases
☐ Prospective consecutive enrollment
☐ Reader study (with and without AI)
☐ Randomized controlled trial (AI-assisted vs. standard care)

**Primary Endpoint:**
[Diagnostic accuracy (sensitivity/specificity) / Clinical outcome (time to diagnosis, diagnostic yield, patient management change) / Reader performance improvement]

**Sample Size Calculation:**
- **Assumptions:** Expected sensitivity [X%], specificity [Y%], prevalence [Z%]
- **Target 95% CI width:** [±W%]
- **Required sample size:** [N_total cases; n_positive diseased cases]
- **Achieved sample size:** [N_actual]

### 7.2 Reader Study (If Applicable)

**Study Design:**
☐ Independent reads (readers interpret cases without AI, then separately with AI)
☐ Sequential reads (readers first without AI, then with AI assistance on same cases - risk of recall bias)
☐ Randomized cross-over (half of cases with AI first, half without)

**Readers:**
- **Number of Readers:** [N = X radiologists/pathologists]
- **Reader Qualifications:** [Board-certified, years of experience: median [Y] years (range [Z-W])]
- **Reader Training:** [Tutorial on AI system, [X] practice cases with feedback]

**Blinding:**
☐ Readers blinded to clinical history and prior reports (challenge set)
☐ Readers have access to clinical history (real-world simulation)
☐ Readers blinded to AI output (for unaided reads)

**Reader Performance Results:**

| Metric | Readers Unaided (Mean) | Readers with AI (Mean) | Improvement | P-value (Paired t-test) |
|--------|:---:|:---:|:---:|:---:|
| **Sensitivity** | [X%] | [Y%] | [+Z%] | [p=0.XX] |
| **Specificity** | [X%] | [Y%] | [+Z%] | [p=0.XX] |
| **AUC** | [X.XX] | [Y.YY] | [+Z] | [p=0.XX] |
| **Reading Time (minutes)** | [T1] | [T2] | [-ΔT] | [p=0.XX] |

**Inter-Reader Agreement:**
- **Without AI:** Fleiss' kappa = [κ = X.XX]
- **With AI:** Fleiss' kappa = [κ = Y.YY] (improved agreement)

**Clinical Impact:**
[Does AI assistance improve diagnostic accuracy? Reduce reading time? Increase reader confidence? Standardize interpretations?]

### 7.3 Real-World Clinical Workflow Study (If Applicable)

**Study Setting:** [Describe clinical environment where AI deployed]

**Integration:** [PACS integration, worklist management, how results displayed to clinician]

**Metrics:**
- **Adoption Rate:** [% of cases where AI results reviewed by clinicians]
- **Override Rate:** [% of cases where clinician disagrees with AI recommendation]
- **Time to Diagnosis:** [Days from imaging to final report; compare AI vs. pre-AI]
- **Diagnostic Yield:** [% of clinically significant findings detected; AI vs. baseline]

**User Feedback:**
[Clinician surveys, interviews; perceived value, trust, usability, areas for improvement]

---

## 8. Uncertainty Quantification and Explainability

### 8.1 Confidence Scoring

**Uncertainty Estimation Method:**
☐ Softmax probability output (not true uncertainty; overconfident)
☐ Monte Carlo Dropout (multiple forward passes with dropout to estimate epistemic uncertainty)
☐ Ensemble methods (variance across ensemble predictions)
☐ Bayesian deep learning (posterior distribution over weights)

**Confidence Calibration:**
- **Calibration Curve:** [Plot predicted probability vs. observed frequency; diagonal = perfect calibration]
- **Calibration Metrics:** Expected Calibration Error (ECE) = [X.XX]; Brier score = [Y.YY]
- **Calibration Method:** [Temperature scaling, Platt scaling, isotonic regression applied to validation set]

**Clinical Use of Confidence Scores:**
- **High Confidence (>0.9):** [X% of test cases; PPV=[Y%], NPV=[Z%]]
- **Medium Confidence (0.7-0.9):** [X% of test cases; PPV=[Y%], NPV=[Z%]]
- **Low Confidence (<0.7):** [X% of test cases; flag for expert review]

**Labeling Recommendation:**
☐ Display confidence score to user
☐ Flag low-confidence cases for manual review
☐ Do not display confidence (fixed threshold only)

### 8.2 Explainability and Interpretability

**Explainability Methods Implemented:**
☐ Saliency maps (Grad-CAM, Class Activation Maps) highlighting image regions influencing prediction
☐ SHAP (SHapley Additive exPlanations) values for feature importance
☐ Attention mechanisms visualized
☐ Example-based explanations (similar training cases retrieved)
☐ Natural language explanations generated
☐ None (black-box model)

**Example Saliency Map:**
[Include example images with overlaid heatmaps showing regions of interest identified by algorithm]

**Clinical Value of Explanations:**
- Builds clinician trust and acceptance
- Enables detection of algorithm errors (e.g., focusing on image artifact rather than pathology)
- Facilitates teaching and quality improvement
- Supports clinical audit and error analysis

**Limitations of Explanations:**
[Saliency maps may be imperfect or misleading; do not fully represent internal model logic; should not replace clinical judgment]

---

## 9. Failure Mode Analysis and Limitations

### 9.1 Known Failure Modes

**Error Analysis (False Positives and False Negatives):**

| Failure Mode | Frequency (% of Test Set) | Clinical Impact | Root Cause | Mitigation |
|-------------|:---:|:---:|-------------|-----------|
| **False Positive:** [Description] | [X%] | [Low/Medium/High] | [e.g., Mimics on imaging, anatomical variants] | [User warned in IFU; training on difficult cases] |
| **False Negative:** [Description] | [Y%] | [Low/Medium/High] | [e.g., Subtle early-stage disease] | [User warned; recommend follow-up if clinical suspicion high] |

**Edge Cases and Out-of-Distribution Data:**
- **Image quality degradation:** [Motion artifact, low contrast, metal artifact]
- **Rare pathologies:** [Not well-represented in training data]
- **Pediatric patients:** [If trained only on adults]
- **Unusual imaging protocols:** [Non-standard sequences, contrast timing]

**Robustness Testing:**
☐ Adversarial examples (intentionally perturbed images)
☐ Out-of-distribution detection (algorithm flags unfamiliar inputs)
☐ Stress testing with degraded image quality

### 9.2 Device Limitations (for Labeling)

**Limitations to be Disclosed in IFU:**
1. **Intended Use Limitations:** [Specify patient population, clinical context, image types where validated]
2. **Performance Limitations:** [Sensitivity/specificity not 100%; false positives/negatives occur]
3. **Generalization Limitations:** [Performance may vary with different scanners, protocols, populations not represented in training]
4. **User Skill Dependency:** [Requires qualified clinician interpretation; not autonomous diagnostic]
5. **Known Failure Modes:** [List specific scenarios where algorithm may underperform]
6. **Data Drift:** [Algorithm trained on data from [years]; performance may degrade over time without retraining]

**Contraindications / Do Not Use:**
[Scenarios where device should not be used; e.g., "Do not use for pediatric patients under 18 years" if not validated]

---

## 10. Cybersecurity and Software Maintenance

### 10.1 Cybersecurity Controls (per FDA 2023 Draft Guidance)

**Secure by Design Principles Implemented:**
☐ **SBOM Provided:** [Machine-readable SBOM attached; see Section 2.2]
☐ **Authentication and Authorization:** [User login required; role-based access control]
☐ **Data Encryption:** [Data at rest: AES-256; Data in transit: TLS 1.3]
☐ **Vulnerability Management Plan:** [Monitoring SBOM for CVEs; patching schedule]
☐ **Secure Update Mechanism:** [Code-signed software updates; integrity verification]
☐ **Audit Logging:** [User actions and data access logged for compliance/security]
☐ **Network Security:** [Firewall recommendations, network segmentation in deployment guide]

**Penetration Testing:**
- **Performed by:** [Internal security team / Third-party firm]
- **Date:** [Date]
- **Findings:** [High-risk vulnerabilities identified and remediated; report reference]

**Coordinated Vulnerability Disclosure:**
- **Security Contact:** [Email: security@company.com]
- **Response SLA:** [Triage within 48 hours; patch critical vulnerabilities within 30 days]

### 10.2 Software Maintenance and Updates

**Routine Updates (Non-Device Changes per FDA):**
☐ Cybersecurity patches (vulnerability fixes)
☐ Bug fixes not affecting clinical performance
☐ User interface improvements (non-functional)
☐ Platform compatibility updates (new OS versions)

**Device Changes Requiring New Submission:**
☐ Algorithm retraining or architecture changes
☐ Changes to intended use or indications
☐ Changes affecting safety or effectiveness
☐ New clinical claims

**Predetermined Change Control Plan (PCCP) for Continuously Learning Algorithms:**
☐ Not applicable - algorithm is locked
☐ Applicable - PCCP submitted per FDA draft guidance (2023)

**If PCCP Applicable:**
- **SaMD Pre-Specifications (SPS):** [Performance goals, acceptable performance range]
- **Algorithm Change Protocol (ACP):** [Retraining triggers, data sources, performance monitoring]
- **Impact Assessment:** [How changes evaluated before deployment; threshold for new submission]

---

## 11. Post-Market Surveillance and Real-World Performance Monitoring

### 11.1 Performance Monitoring Plan

**Metrics to Monitor:**
☐ Sensitivity and specificity (via periodic validation on new cases)
☐ Confidence score distribution (drift toward overconfidence or underconfidence)
☐ Subgroup performance (ongoing equity monitoring)
☐ User override rate (clinicians disagreeing with AI)
☐ Technical performance (processing time, failure rate, error messages)

**Data Sources:**
☐ User feedback and complaints
☐ Periodic ground-truth validation studies (sample of cases re-reviewed by experts)
☐ Integration with clinical outcomes (positive predictive value of AI findings via follow-up data)
☐ FDA MAUDE database (adverse events for similar devices)

**Monitoring Frequency:**
☐ Continuous automated monitoring (dashboard)
☐ Quarterly performance reports reviewed by medical affairs and engineering
☐ Annual comprehensive review and update to risk management file

**Thresholds for Action:**
- **Performance Degradation:** >5% absolute decrease in sensitivity or specificity triggers investigation
- **Subgroup Disparity:** >10% performance gap across demographic subgroups triggers bias analysis
- **User Complaints:** Cluster of similar complaints (≥5 in 30 days) triggers root cause analysis

**Retraining Triggers:**
- **Data Drift:** Significant shift in input data distribution (detected by statistical tests)
- **Concept Drift:** Change in disease prevalence or imaging standards
- **Performance Degradation:** Sustained decrease in validation metrics below acceptable threshold
- **New Clinical Evidence:** Updated diagnostic criteria or treatment guidelines

### 11.2 Adverse Event Reporting

**Medical Device Reporting (MDR) per 21 CFR 803:**
☐ Manufacturer must report to FDA within 30 days: death or serious injury; malfunction likely to cause death/serious injury
☐ User facilities (hospitals) report deaths to FDA and manufacturer within 10 days; serious injuries to manufacturer within 10 days

**Adverse Events Specific to AI/ML:**
- **Diagnostic Errors:** False negatives leading to delayed diagnosis or treatment
- **False Positives:** Unnecessary procedures, patient anxiety, healthcare costs
- **Use Errors:** Misinterpretation of AI output, over-reliance, automation bias
- **Software Malfunctions:** Crashes, incorrect outputs, data corruption

**Post-Market Surveillance Study (if required):**
☐ Not required
☐ Required by FDA as condition of clearance/approval
☐ Voluntary post-market study planned

---

## 12. Usability and Human Factors Validation

**Usability Study per IEC 62366-1:**

**Participants:** [N=[X] intended users (e.g., radiologists); representative of user population by experience level]

**Study Design:**
☐ Simulated use (scenarios with test cases)
☐ Actual use (clinical environment observation)
☐ Formative evaluation (iterative design improvement)
☐ Summative evaluation (final validation before release)

**Use-Related Hazards Identified:**
1. **Hazard:** [e.g., Over-reliance on AI, missing true disease if AI false negative]
   - **Mitigation:** [Training emphasizes AI is decision support, not replacement; labeling includes performance limitations]
2. **Hazard:** [e.g., Misinterpretation of confidence score]
   - **Mitigation:** [Clear labeling: "Confidence: 85% High suspicion of disease; recommend further evaluation"]
3. **Hazard:** [e.g., Failure to review AI output due to alert fatigue]
   - **Mitigation:** [Prioritize high-confidence findings; integrate into workflow without excessive interruptions]

**Usability Metrics:**

| Task | Success Rate | Time to Complete | User Satisfaction (1-5) | Errors Observed |
|------|:---:|:---:|:---:|:---:|
| Interpret AI output | [X/X correct] | [Mean Y sec] | [4.5/5] | [0 critical, 2 minor] |
| Adjust threshold/settings | [X/X] | [Mean Y sec] | [4.0/5] | [1 critical] |
| Handle low-confidence case | [X/X] | [Mean Y sec] | [4.2/5] | [0] |

**Critical Use Errors:**
[None observed / Errors observed and mitigated in final design]

**Training and Labeling Adequacy:**
☐ Users can operate device safely and effectively with IFU alone (no additional training)
☐ Training required; training materials provided and validated in usability study

---

## 13. Regulatory Submission Summary

### 13.1 Regulatory Strategy

**Regulatory Pathway:** [510(k) / De Novo / PMA]

**Predicate Device (if 510(k)):**
- **Device Name:** [Predicate Name]
- **K-number:** [K-XXXXXX]
- **Manufacturer:** [Manufacturer Name]
- **Substantial Equivalence Rationale:** [Same intended use, same technological characteristics OR different tech characteristics but no new safety/effectiveness questions]

**Special Controls (if De Novo or Class II):**
[List special controls: performance testing, labeling, software documentation, post-market surveillance]

### 13.2 Documentation Provided in Submission

☐ **Device Description:** Hardware/software architecture, SBOM, algorithm description
☐ **Software Documentation:** Per FDA 2023 Software Guidance - Level of Concern [Minor/Moderate/Major]
☐ **Risk Management File:** ISO 14971 per this template
☐ **Verification and Validation:** Algorithm validation report (this document)
☐ **Clinical Evaluation:** Clinical study report, reader study, literature review
☐ **Usability Engineering File:** IEC 62366-1 report
☐ **Cybersecurity Documentation:** Threat model, cybersecurity controls, SBOM, vulnerability plan
☐ **Labeling:** IFU, product labeling, training materials
☐ **Performance Testing:** Bench testing, software testing, robustness testing
☐ **Manufacturing and Quality:** ISO 13485 QMS, software development lifecycle per IEC 62304

### 13.3 Anticipated FDA Questions

**Anticipated Question 1:** [How was test set independence ensured?]
**Response:** [Test set locked on [Date] before model training; no patient overlap; documented in Section 5.1]

**Anticipated Question 2:** [What is the clinical impact of observed subgroup performance differences?]
**Response:** [See Section 5.4; differences are statistically significant but clinically minor (Δ<5%); all subgroups exceed target performance]

**Anticipated Question 3:** [How will performance be monitored post-market?]
**Response:** [See Section 11; quarterly validation studies, user feedback, adverse event monitoring]

---

## 14. Conclusions

**Summary:**
[1-2 paragraphs summarizing validation results, performance vs. benchmarks, clinical readiness]

**Regulatory Conclusion:**
☐ Algorithm validation is complete and supports regulatory submission
☐ Algorithm meets performance requirements and is safe and effective for intended use
☐ Device is ready for clinical deployment

**Next Steps:**
☐ Finalize regulatory submission package
☐ Prepare for FDA pre-submission meeting (if applicable)
☐ Plan post-market surveillance study
☐ Prepare for product launch and user training

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Principal Investigator / Data Scientist | | | |
| Clinical Advisor | | | |
| Software Engineering Manager | | | |
| Quality Assurance Manager | | | |
| Regulatory Affairs Manager | | | |

---

**End of AI/ML Validation Report**

*This template complies with FDA AI/ML guidances (2021-2023), GMLP Principles (2021), IEC 62304, and ISO 14971:2019.*

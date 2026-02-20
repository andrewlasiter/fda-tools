# openFDA Device API Data Dictionary

> Source: openFDA API (https://open.fda.gov/apis/device/)
> Endpoints: 9
> Last reviewed: 2026-02-08
> Scope: Key fields used by plugin commands, correctly attributed per endpoint

This reference documents the searchable and response fields for each openFDA Device API endpoint. Fields are organized by endpoint to prevent misattribution. For the complete field list, see the [official openFDA API documentation](https://open.fda.gov/apis/device/).

## Quick Reference: Endpoint → Plugin Command

| Endpoint | Plugin Commands | Purpose |
|----------|----------------|---------|
| `device/event` | `/fda:safety` | MAUDE adverse event reports |
| `device/recall` | `/fda:safety`, `/fda:warnings` | Device recalls and enforcement |
| `device/510k` | `/fda:research`, `/fda:extract`, `/fda:validate` | 510(k) clearance data |
| `device/classification` | `/fda:research`, `/fda:guidance`, `/fda:pathway` | Product code classification |
| `device/registrationlisting` | `/fda:status` | Facility registration |
| `device/pma` | `/fda:research`, `/fda:pathway` | PMA approvals |
| `device/udi` | `/fda:udi` | UDI/GUDID device identifiers |
| `device/covid19serology` | — | COVID-19 serology test data |
| `device/premarket` | — | Premarket submissions (not yet used) |

---

## 1. device/event (MAUDE Adverse Events)

Used by: `/fda:safety`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `device.device_report_product_code` | string | 3-letter FDA product code |
| `event_type` | string | Outcome: "Death", "Injury", "Malfunction", etc. |
| `date_of_event` | string | Date of first onset of the adverse event |
| `date_received` | string | Date FDA received the report |
| `product_problem_flag` | string | "Y" if report is about device quality/performance/safety |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `mdr_report_key` | string | Unique identifier for the report |
| `adverse_event_flag` | string | Whether the report involves an adverse outcome |
| `report_number` | string | Identifying number for the adverse event report |
| `report_source_code` | string | Source of the report (manufacturer, user facility, etc.) |
| `date_report` | string | Date the initial reporter provided info |
| `date_report_to_fda` | string | Date the report was sent to FDA |
| `date_report_to_manufacturer` | string | Date the report was sent to manufacturer |
| `health_professional` | string | Whether initial reporter was a health professional |
| `reporter_occupation_code` | string | Initial reporter occupation |
| `event_location` | string | Where the event occurred |
| `event_key` | string | Internal event key |
| `number_devices_in_event` | string | Number of devices noted (usually "1") |
| `number_patients_in_event` | string | Number of patients noted (usually "1") |
| `product_problem_flag` | string | Whether report is about device quality/safety |
| `product_problems` | array | Product problems reported |
| `removal_correction_number` | string | Corrective action number (21 USC 360i) |
| `report_to_fda` | string | Whether report was sent to FDA |
| `report_to_manufacturer` | string | Whether report was sent to manufacturer |
| `reprocessed_and_reused_flag` | string | Whether device was single-use and reprocessed |
| `single_use_flag` | string | Whether device was labeled for single use |
| `source_type` | array | Manufacturer-reported source of report |
| `summary_malfunction_reporting` | string | Voluntary Malfunction Summary Reporting flag |
| `type_of_report` | array | Type of report |
| `initial_report_to_fda` | string | Whether initial reporter also notified FDA |
| `manufacturer_link_flag` | string | Whether report has manufacturer follow-up |
| `previous_use_code` | string | Initial use, reuse, or unknown |
| `remedial_action` | array | Follow-up actions taken by manufacturer |

### Nested: `device.*` (Device Information)

| Field | Type | Description |
|-------|------|-------------|
| `device.brand_name` | string | Trade/proprietary name of suspect device |
| `device.catalog_number` | string | Catalog/reference number |
| `device.generic_name` | string | Generic/common name of suspect device |
| `device.model_number` | string | Model number |
| `device.lot_number` | string | Lot number |
| `device.manufacturer_d_name` | string | Device manufacturer name |
| `device.manufacturer_d_city` | string | Device manufacturer city |
| `device.manufacturer_d_state` | string | Device manufacturer state |
| `device.manufacturer_d_country` | string | Device manufacturer country |
| `device.device_operator` | string | Person using the device at time of event |
| `device.device_availability` | string | Whether device is available for evaluation |
| `device.device_evaluated_by_manufacturer` | string | Whether manufacturer evaluated the device |
| `device.implant_flag` | string | Whether device was implanted |
| `device.date_removed_flag` | string | Whether implanted device was removed |
| `device.device_age_text` | string | Age of the device |
| `device.expiration_date_of_device` | string | Device expiration date |
| `device.device_sequence_number` | string | Sequential device number in report |
| `device.openfda` | object | Nested openFDA enrichment fields |

### Nested: `patient.*` (Patient Information)

| Field | Type | Description |
|-------|------|-------------|
| `patient.patient_age` | string | Patient age |
| `patient.patient_sex` | string | Patient gender |
| `patient.patient_race` | string | Patient race |
| `patient.patient_ethnicity` | string | Patient ethnicity |
| `patient.patient_weight` | string | Patient weight |
| `patient.patient_problems` | array | Adverse effects related to device problem |
| `patient.sequence_number_outcome` | array | Outcome for this patient |
| `patient.sequence_number_treatment` | array | Treatment received |
| `patient.date_received` | string | Date patient report was received |

### Nested: `mdr_text.*` (Narrative Text)

| Field | Type | Description |
|-------|------|-------------|
| `mdr_text.text` | string | Narrative text or problem description |
| `mdr_text.text_type_code` | string | Type of narrative |
| `mdr_text.date_report` | string | Date of initial report |

### Nested: `manufacturer_*` (Suspect Device Manufacturer)

| Field | Type | Description |
|-------|------|-------------|
| `manufacturer_name` | string | Suspect device manufacturer name |
| `manufacturer_address_1` | string | Address line 1 |
| `manufacturer_city` | string | City |
| `manufacturer_state` | string | State code |
| `manufacturer_country` | string | Country code |
| `manufacturer_postal_code` | string | Postal code |
| `manufacturer_contact_f_name` | string | Contact first name |
| `manufacturer_contact_l_name` | string | Contact last name |
| `manufacturer_contact_phone_number` | string | Contact phone |

---

## 2. device/recall (Enforcement/Recalls)

Used by: `/fda:safety`, `/fda:warnings`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_code` | string | 3-letter FDA product code (via openfda enrichment) |
| `recalling_firm` | string | Firm that initiated the recall |
| `recall_status` | string | Current recall status (Ongoing, Terminated, etc.) |
| `classification` | string | Recall class: "Class I", "Class II", "Class III" |
| `k_numbers` | array | Associated 510(k) numbers |
| `pma_numbers` | array | Associated PMA numbers |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `res_event_number` | string | FDA recall event tracking number |
| `recall_number` | string | Recall tracking number |
| `event_id` | string | Recall event identifier |
| `action` | string | Action taken as part of the recall |
| `classification` | string | Recall class (I, II, III) |
| `recall_status` | string | Current status (Ongoing, Terminated, etc.) |
| `product_description` | string | Brief product description |
| `product_quantity` | string | Amount of defective product |
| `reason_for_recall` | string | How the product is defective |
| `code_info` | string | Lot/serial numbers, use-by dates |
| `distribution_pattern` | string | Area of initial distribution |
| `recalling_firm` | string | Firm initiating the recall |
| `country` | string | Country of recalling firm |
| `firm_fei_number` | string | FDA Facility Establishment Identifier |
| `event_date_initiated` | string | Date firm began notifying public |
| `event_date_created` | string | Date record created in FDA database |
| `event_date_posted` | string | Date FDA classified the recall |
| `event_date_terminated` | string | Date FDA terminated the recall |
| `recall_initiation_date` | string | Date firm began notifying public |
| `initial_firm_notification` | string | Method of public notification |
| `voluntary_mandated` | string | Who initiated: "Voluntary" or "FDA Mandated" |
| `root_cause_description` | string | FDA-determined general recall cause |
| `other_submission_description` | string | Other regulatory description if not 510k/PMA |
| `product_res_number` | string | Product recall number |
| `report_date` | string | Date FDA issued enforcement report |
| `status` | string | Record status |
| `termination_date` | string | Termination date |
| `cfres_id` | string | cfRes internal recall identifier |

---

## 3. device/510k (510(k) Clearances)

Used by: `/fda:research`, `/fda:extract`, `/fda:validate`, `/fda:lineage`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_code` | string | 3-letter FDA product code |
| `applicant` | string | Company that submitted the 510(k) |
| `k_number` | string | FDA-assigned 510(k) number (e.g., K241335) |
| `decision_date` | string | Date FDA rendered final decision |
| `decision_code` | string | Decision code (SESE, SESP, etc.) |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `k_number` | string | FDA-assigned 510(k) number |
| `applicant` | string | Manufacturer/submitter name |
| `device_name` | string | Proprietary/trade name of cleared device |
| `product_code` | string | 3-letter product code |
| `decision_date` | string | Date of FDA decision |
| `decision_code` | string | Decision code (4 letters) |
| `decision_description` | string | Full decision description |
| `clearance_type` | string | Submission method (Traditional, Special, Abbreviated) |
| `statement_or_summary` | string | Whether Summary or Statement was filed |
| `date_received` | string | Date FDA received submission |
| `advisory_committee` | string | Review panel code |
| `advisory_committee_description` | string | Review panel name |
| `review_advisory_committee` | string | Review division (since 2014) |
| `expedited_review_flag` | string | Priority review eligibility |
| `third_party_flag` | string | Third-party review eligibility |
| `submission_type_id` | string | Submission type limitation |
| `contact` | string | Official correspondent |
| `address_1` | string | Applicant address line 1 |
| `address_2` | string | Applicant address line 2 |
| `city` | string | Applicant city |
| `state` | string | Applicant state |
| `country_code` | string | Applicant country (ISO 3166-1 alpha-2) |
| `zip` | string | Applicant zip code |
| `zip_ext` | string | Applicant zip+4 extension |
| `street_1` | string | Applicant delivery address 1 |
| `street_2` | string | Applicant delivery address 2 |

### Nested: `openfda.*` (Enrichment)

| Field | Type | Description |
|-------|------|-------------|
| `openfda.device_class` | string | Risk classification (1, 2, 3) |
| `openfda.device_name` | string | Device common name |
| `openfda.medical_specialty_description` | string | Review panel specialty |
| `openfda.regulation_number` | array | 21 CFR regulation number(s) |

---

## 4. device/classification (Device Classification)

Used by: `/fda:research`, `/fda:guidance`, `/fda:pathway`, `/fda:ask`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_code` | string | 3-letter FDA product code |
| `regulation_number` | string | 21 CFR regulation number |
| `device_name` | string | Official device type name |
| `device_class` | string | Risk class: "1", "2", or "3" |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_code` | string | 3-letter product code |
| `device_name` | string | Official device type name |
| `device_class` | string | Risk classification (1, 2, 3) |
| `definition` | string | Compositional definition of the device |
| `regulation_number` | string | 21 CFR regulation number |
| `medical_specialty` | string | Medical specialty code |
| `medical_specialty_description` | string | Medical specialty name |
| `review_panel` | string | Review panel code |
| `review_code` | string | Review processing code |
| `implant_flag` | string | "Y" if device is an implant |
| `life_sustain_support_flag` | string | "Y" if life-sustaining/supporting |
| `gmp_exempt_flag` | string | "Y" if exempt from GMP (21 CFR 820) |
| `submission_type_id` | string | Required submission type |
| `third_party_flag` | string | Third-party review eligibility |
| `unclassified_reason` | string | Reason if unclassified (Pre-Amendment, etc.) |

### Nested: `openfda.*`

| Field | Type | Description |
|-------|------|-------------|
| `openfda.k_number` | array | Associated 510(k) numbers |
| `openfda.pma_number` | string | Associated PMA number |

---

## 5. device/registrationlisting (Facility Registration & Listing)

Used by: `/fda:status`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `registration.fei_number` | string | FDA Facility Establishment Identifier |
| `registration.name` | string | Facility name |
| `products.product_code` | string | Listed product code |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `registration.fei_number` | string | FEI number |
| `registration.registration_number` | string | Registration number |
| `registration.name` | string | Facility name |
| `registration.address_line_1` | string | Address |
| `registration.city` | string | City |
| `registration.state_code` | string | State/province |
| `registration.iso_country_code` | string | Country code |
| `registration.postal_code` | string | Postal code |
| `registration.zip_code` | string | US zip code |
| `registration.status_code` | string | Registration status |
| `registration.reg_expiry_date_year` | string | Expiration year |
| `registration.initial_importer_flag` | string | Initial importer indicator |
| `registration.owner_operator` | object | Owner/operator info |
| `registration.us_agent` | object | US agent info (foreign firms) |
| `establishment_type` | array | Facility activity type(s) |
| `products.product_code` | string | 3-letter product code |
| `products.created_date` | string | Listing creation date |
| `products.exempt` | string | Exempt flag |
| `products.owner_operator_number` | string | CDRH owner/operator number |
| `products.openfda` | object | openFDA enrichment |
| `proprietary_name` | array | Brand/model names |

---

## 6. device/pma (PMA Approvals)

Used by: `/fda:research`, `/fda:pathway`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `product_code` | string | 3-letter FDA product code |
| `applicant` | string | PMA applicant name |
| `pma_number` | string | FDA-assigned PMA number |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `pma_number` | string | PMA number (e.g., P123456) |
| `trade_name` | string | Proprietary device name |
| `generic_name` | string | Common/generic name |
| `applicant` | string | Applicant company name |
| `ao_statement` | string | Approval order statement |
| `decision_date` | string | Date of FDA decision |
| `decision_code` | string | Decision code |
| `product_code` | string | Product code |
| `supplement_number` | string | Supplement number |
| `supplement_reason` | string | Reason for supplement |
| `supplement_type` | string | Supplement type |
| `docket_number` | string | Federal Register docket number |
| `fed_reg_notice_date` | string | Federal Register notice date |
| `advisory_committee` | string | Advisory committee code |
| `advisory_committee_description` | string | Advisory committee name |
| `expedited_review_flag` | string | Priority review flag |

---

## 7. device/udi (UDI/GUDID)

Used by: `/fda:udi`

### Key Search Fields

| Field | Type | Description |
|-------|------|-------------|
| `identifiers.id` | string | UDI (primary device identifier) |
| `product_codes.code` | string | 3-letter FDA product code |
| `brand_name` | string | Trade/brand name |
| `company_name` | string | Labeler company name |

### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand_name` | string | Trade/brand name |
| `catalog_number` | string | Catalog/reference number |
| `company_name` | string | Labeler company name |
| `device_description` | string | Device description text |
| `device_count_in_base_package` | integer | Devices per package |
| `version_or_model_number` | string | Version or model |
| `labeler_duns_number` | string | DUNS number |
| `record_key` | string | Stable record identifier |
| `record_status` | string | DI record status |
| `publish_date` | date | Publication date |
| `public_version_number` | string | Version number |
| `public_version_date` | date | Version date |

### Boolean Flags

| Field | Type | Description |
|-------|------|-------------|
| `is_combination_product` | boolean | Contains two or more regulated products |
| `is_direct_marking_exempt` | boolean | Exempt from direct marking (21 CFR 801.45) |
| `is_hct_p` | boolean | Contains human cells/tissues |
| `is_kit` | boolean | Is a convenience/IVD/procedure kit |
| `is_labeled_as_nrl` | boolean | Contains natural rubber latex (21 CFR 801.437) |
| `is_labeled_as_no_nrl` | boolean | Labeled as NOT containing NRL |
| `is_otc` | boolean | Over-the-counter (no prescription) |
| `is_pm_exempt` | boolean | Exempt from premarket notification |
| `is_rx` | boolean | Requires prescription |
| `is_single_use` | boolean | Single use / single patient |
| `has_donation_id_number` | boolean | Has HCT/P donation ID |
| `has_expiration_date` | boolean | Has expiration date on label |
| `has_lot_or_batch_number` | boolean | Has lot/batch number |
| `has_manufacturing_date` | boolean | Has manufacturing date |
| `has_serial_number` | boolean | Has serial number |

### Nested: `identifiers.*`

| Field | Type | Description |
|-------|------|-------------|
| `identifiers.id` | string | UDI value |
| `identifiers.type` | string | Primary, Secondary, Direct Marking, Package, etc. |
| `identifiers.issuing_agency` | string | UDI issuing agency (GS1, HIBCC, ICCBBA) |
| `identifiers.package_type` | string | Package type |
| `identifiers.quantity_per_package` | integer | Quantity per package |
| `identifiers.package_status` | string | Commercial distribution status |
| `identifiers.package_discontinue_date` | date | Package discontinue date |
| `identifiers.unit_of_use_id` | string | Unit-of-use DI |

### Nested: `sterilization.*`

| Field | Type | Description |
|-------|------|-------------|
| `sterilization.is_sterile` | boolean | Device is sterile (ISO/TS 11139) |
| `sterilization.is_sterilization_prior_use` | boolean | Requires sterilization before use |
| `sterilization.sterilization_methods` | string | Sterilization method(s) |

### Nested: `storage.*`

| Field | Type | Description |
|-------|------|-------------|
| `storage.type` | string | Storage/handling requirements |
| `storage.special_conditions` | string | Special storage requirements |
| `storage.high` | object | Upper storage limit |
| `storage.low` | object | Lower storage limit |

### Nested: `device_sizes.*`

| Field | Type | Description |
|-------|------|-------------|
| `device_sizes.type` | string | Dimension type |
| `device_sizes.value` | string | Size value |
| `device_sizes.unit` | string | Unit of measure |
| `device_sizes.text` | string | Additional size text |

### Nested: `product_codes.*`

| Field | Type | Description |
|-------|------|-------------|
| `product_codes.code` | string | 3-letter product code |
| `product_codes.name` | string | Product code name |
| `product_codes.openfda` | object | openFDA enrichment |

### Nested: `premarket_submissions.*`

| Field | Type | Description |
|-------|------|-------------|
| `premarket_submissions.submission_number` | string | Submission number (K-number, PMA, etc.) |
| `premarket_submissions.submission_type` | string | Submission type |
| `premarket_submissions.supplement_number` | string | Supplement number |

### Nested: `customer_contacts.*`

| Field | Type | Description |
|-------|------|-------------|
| `customer_contacts.phone` | string | Customer contact phone |
| `customer_contacts.email` | string | Customer contact email |

### Nested: `gmdn_terms.*`

| Field | Type | Description |
|-------|------|-------------|
| `gmdn_terms.code` | string | GMDN Preferred Term Code |
| `gmdn_terms.name` | string | GMDN term name |
| `gmdn_terms.definition` | string | GMDN term definition |
| `gmdn_terms.implantable` | boolean | GMDN implantable flag |
| `gmdn_terms.code_status` | boolean | Active or Obsolete |

### Additional UDI Fields

| Field | Type | Description |
|-------|------|-------------|
| `commercial_distribution_status` | string | Distribution status (21 CFR 807.3(b)) |
| `commercial_distribution_end_date` | date | Distribution end date |
| `mri_safety` | string | MRI safety info (per ASTM F2503-13) |

---

## 8. device/covid19serology (COVID-19 Serology Tests)

Not currently used by plugin commands.

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `manufacturer` | string | Test manufacturer |
| `device` | string | Test device name |
| `lot_number` | string | Lot number tested |
| `evaluation_id` | string | Evaluation identifier |
| `sample_id` | string | Sample identifier |
| `sample_no` | integer | Sample sequence number |
| `type` | string | Sample material type |
| `group` | string | Panel group (Positives, Negatives, etc.) |
| `panel` | string | Panel identifier |
| `date_performed` | date | Test date |
| `control` | string | Control line result |
| `antibody_agree` | string | Agreement with truth |
| `antibody_truth` | string | True qualitative result |
| `igg_result` | string | IgG detection result |
| `igm_result` | string | IgM detection result |
| `iga_result` | string | IgA detection result |
| `pan_result` | string | Pan-Ig detection result |
| `days_from_symptom` | string | Days from symptom onset |

---

## 9. device/premarket (Premarket Submissions)

Combines 510(k), PMA, De Novo, and HDE submissions in one endpoint. Not yet used directly by plugin commands; `/fda:research` uses device/510k and device/pma separately.

---

## Common Nested: `openfda.*` (Enrichment Block)

Most endpoints include an `openfda` enrichment block with fields cross-referenced from other databases:

| Field | Type | Description |
|-------|------|-------------|
| `openfda.device_class` | string | Risk classification (1, 2, 3) |
| `openfda.device_name` | string | Device common name |
| `openfda.medical_specialty_description` | string | Medical specialty |
| `openfda.regulation_number` | array | 21 CFR regulation number(s) |
| `openfda.k_number` | array | Associated 510(k) numbers |
| `openfda.pma_number` | string | Associated PMA number |
| `openfda.fei_number` | array | Facility FEI numbers |
| `openfda.registration_number` | array | Registration numbers |
| `openfda.product_type` | array | Product type (always "Devices") |

### Meta Fields (All Endpoints)

| Field | Type | Description |
|-------|------|-------------|
| `meta.disclaimer` | string | Data limitations notice |
| `meta.last_updated` | string | Endpoint last update date |
| `meta.license` | string | License terms URL |
| `meta.results.total` | integer | Total matching records |
| `meta.results.skip` | integer | Records skipped |
| `meta.results.limit` | integer | Records per page |

---

## API Query Patterns

### Count Queries

Append `&count=field.exact` to get term frequency counts:

```
/device/event.json?search=device.device_report_product_code:"OVE"&count=event_type.exact
```

### Sort Queries

Use `&sort=field:asc` or `&sort=field:desc`:

```
/device/510k.json?search=product_code:"OVE"&sort=decision_date:desc&limit=10
```

### Date Range Queries

Use bracket syntax for date ranges:

```
/device/event.json?search=date_received:[20230101+TO+20251231]+AND+device.device_report_product_code:"OVE"
```

### OR Queries

Use `+OR+` between terms:

```
/device/510k.json?search=product_code:"OVE"+OR+product_code:"OVF"
```

### Wildcard Queries

Use `*` for prefix matching:

```
/device/510k.json?search=applicant:"MEDTRONIC*"
```

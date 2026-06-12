# CareShot AI Product Classifier Dataset

Created: 2026-06-12

This folder contains LG official website image assets collected for the CareShot presentation MVP product classifier.

## Purpose

The classifier is for a lightweight presentation-stage AI step before Web Image Tracking AR.

Runtime intent:

1. Classify the camera frame as `wall_split_ac`, `floor_standing_ac`, `window_ac`, or `not_ac`.
2. Continue AR only when the product class is supported by the MVP guide flow.
3. Use MindAR image tracking to lock onto the selected reference image.
4. Render official-guide-based AR overlay and part map.

The classifier does not make final safety or AR permission decisions. Final guide permission remains controlled by Safety Rule, DecisionEngineV2, official evidence match, high-risk blocking, and guide/template availability.

## Collected Counts

| Class | Count | Role |
|---|---:|---|
| `wall_split_ac` | 100 | Main MVP AR target class |
| `floor_standing_ac` | 70 | MVP-supported product class; requires its own reference target, part map, and guide flow |
| `window_ac` | 43 | Product-type recognition class; MVP may show unsupported/limited guide |
| `not_ac` | 65 | Negative class to reduce false positives |

Total image files: 278

Manual / guide source text files: 4

## Files

| File | Description |
|---|---|
| `official_image_manifest.json` | Image class, local path, source page, source URL, official source metadata |
| `official_manual_manifest.json` | Filter-cleaning and AC guide source pages |
| `collection_summary.json` | Collection count and seed URL summary |
| `collection_errors.json` | Non-fatal pages/assets that failed during collection |
| `raw/<class>/` | Downloaded LG official image assets |
| `raw/manuals/` | Captured source text from LG official support/article pages |

## Source Policy

All collected sources are from LG official websites such as `lg.com/in`, `lg.com/in/business`, `lg.com/us`, and other LG regional/business pages.

These assets are collected for internal project MVP development and presentation prototyping. Verify licensing and redistribution permission before packaging, publishing, or distributing the images externally.

## Current MVP Direction

Recommended first implementation:

```text
Camera frame
-> ProductClassifierService
-> wall_split_ac / floor_standing_ac / window_ac / not_ac
-> supported class gate
-> MindAR image target load
-> reference image tracking
-> part map overlay
-> filter cleaning guide steps
```

For the first high-fidelity AR guide, use a wall-mounted split AC model with confirmed front-open official gallery images, such as `US-Q19BNZE` or `US-Q19YNZE3`.

For `floor_standing_ac`, the classifier dataset is prepared as an MVP-supported class, but the AR guide must be implemented with a separate floor-standing reference target, part map, and filter-cleaning guide template.

## Filter Cleaning Official Sources

The manual manifest includes LG official support/reference pages for:

- LG India split AC filter cleaning.
- LG India wall-mounted AC filter cleaning / panel-position guidance.
- LG US air-conditioner filter cleaning and replacement.
- LG India AC type/efficiency article used as product-category support context.

## Validation

Post-collection validation checked image headers for downloaded files:

```text
bad_image_header_count = 0
```

Cleanup performed:

- Removed 5 non-image video downloads from `not_ac`.
- Fixed 4 extension mismatches where the binary image type differed from the saved extension.

# UI state

Workflow stages: image, geometry, restoration, recognition, review. Restoration status: IDLE before processing, PROCESSING while polling QUEUED/RUNNING, COMPLETED after fetching result manifest, FAILED on API/worker error. OCR over restored derivatives is explicitly unavailable; original OCR remains separately labeled. Segmentation proposal and human approval remain distinct.


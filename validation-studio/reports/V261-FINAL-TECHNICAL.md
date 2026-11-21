# V2.6.1 experimental segmentation certification

## Cause of HTTP 405
Confirmed: the previous patch script used an exact textual anchor that did not match `app.py`; the assertion aborted before writing routes. The API was absent, and StaticFiles caught the POST. The final implementation creates `vision/api/segmentation_routes.py` with an APIRouter and includes it in the same `create_app()` before `app.mount('/')`.

## Implemented
Click-to-segment runs the OpenCV worker in the existing GPU OCR venv (CPU OpenCV; no CUDA claim). It estimates blue HSV bounds from a local seed patch, selects the connected component, closes small gaps, extracts a contour, and writes mask, RGBA and overlay PNGs. `refine` rasterizes the reviewer polygon into a new mask/RGBA; `confirm` atomically updates the proposal JSON to HUMAN_CONFIRMED. API never alters original photo, OCR prediction, or logistics. Frontend has smart click, aura visibility control, isolate/restore and confirm/discard; coordinates are intended as EXIF-normalized image pixels.

## Measured
FastAPI TestClient exercised actual `create_app()` and external OpenCV worker. Click on 20250929_075640.jpg returned HTTP 200, 4-point contour, area 2,245,896 px; transparent PNG returned 200 at 3060×4080. Clicks on the two copy regions of 20261120_005329.jpg each returned 200 and distinct proposal IDs. Invalid coordinate 422; unknown image 404. Refine, confirm, GET after re-instantiating service all passed. Original SHA checks remained equal. PNG alpha has 0 and 255 values.

## Limitations / certification state
No approved human pixel masks exist; IoU/Dice/boundary-F1 are unavailable. Alpha transparency alone does not prove no cardboard is included. RGB exact preservation and false background inclusion were not fully checked pixel-by-pixel in this run. Browser automation host reported unavailable, so no browser visual validation, aura alignment under zoom/pan/rotation, mobile viewport, screenshots or browser console validation. Two separate segmentation proposals were tested, but logistics consolidator was not rerun; one SSCC/quantity 72 remains unverified by this run. Treat as experimental, not certified.


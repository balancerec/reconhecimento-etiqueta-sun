# V2.7.2 UI audit

Inspected index.html, styles.css, app.js, FastAPI app and segmentation/restoration routers plus their workers. Existing 3-column dataset/viewer/inspector and original field validation were retained. 29 action controls were inventoried in V272-CONTROL-INVENTORY.json.

Existing functions include photo selection, zoom/pan/rotation, polygon editing, segmentation API, RGBA isolation, perspective preview, human save/approve/export, history/evaluation and restoration endpoint. Limitations found: restoration endpoint now returns queued job so former UI handler was incompatible; OCR of restored derivative is explicitly unavailable; rectification and restoration each had separate color sliders; restoration panel was stacked below preview; browser visual validation is not available in this session.


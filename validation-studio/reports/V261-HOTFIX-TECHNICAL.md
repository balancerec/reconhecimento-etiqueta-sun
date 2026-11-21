# V2.6.1 hotfix — segmentação interativa

## Diagnóstico
A causa do HTTP 405 foi confirmada: a rota de segmentação não estava presente na instância FastAPI. `scripts/patch_routes.py` procurava uma linha exata; a asserção falhava e impedia a alteração. O `StaticFiles('/')` permaneceu como última rota.

## Implementação
Foi criado `vision/api/segmentation_routes.py` com APIRouter versionado, incluído em `create_app()` antes do mount. `scripts/segment_label.py` segmenta componente azul conectado ao clique usando limiar HSV adaptado à mediana local, componentes conectados, fechamento morfológico e contorno. Gera máscara, overlay e PNG RGBA. A proposta inicia sem revisão; confirmação é explícita.

## Verificação real
POST para `20250929_075640.jpg` retornou 200, com quatro vértices e máscara. O PNG isolado retornou 200, dimensões 4080×2296, canal alpha com 2.691.363 pixels não transparentes e 6.676.317 transparentes. SHA-256 do original permaneceu igual. Em `20261120_005329.jpg`, o manifesto expõe duas vias independentes e foram geradas duas propostas; a segmentação não altera consolidação, SSCC ou quantidade.

## Limites
A qualidade do contorno não foi comparada a máscara humana, então não há IoU. Ainda falta validação visual no navegador; o endpoint não comprova alinhamento visual da aura nem precisão em sombra/reflexo. PNG preserva RGB original dentro da máscara, mas a máscara clássica pode incluir pixels de papelão; requer revisão humana.


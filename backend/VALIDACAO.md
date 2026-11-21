# Validação da versão 0.2.0

## Resultados registrados

O registro de desenvolvimento desta versão informa que 24 testes Python de regras, extração, correções, fila e contrato HTTP passaram. Nesses testes, a inferência visual é simulada. O registro também informa aprovação dos testes JavaScript de contrato, upload multipart, polling, cancelamento, descarte de resultado antigo e correção auditável; verificação sintática de scripts Python/PowerShell; e compilação do instalador .NET.

Esses números são resultados históricos documentados, não uma execução repetida durante a atualização desta página.

## Limites de execução

Na sessão registrada, o Docker Desktop foi localizado, mas o acesso ao named pipe recebeu `permission denied` e o WSL retornou acesso negado. A instalação local e o OCR das fotografias originais não foram executados naquela sessão.

O workflow **Local OCR and Windows installer** compila a imagem Docker e executa `smoke_vision.py`, com Tesseract e RapidOCR reais em imagens sintéticas DUN/SUN, rotação e múltiplas etiquetas. Consulte a execução correspondente em GitHub Actions. Esses testes verificam o pipeline em dados sintéticos; não medem acurácia em fotografias de operação.

O atalho **Testar Etiquetas** gera relatórios locais para fotos de `Pictures/ETIQUETAS`, sem publicá-las. O operador precisa conferir os resultados contra as imagens. Não há percentual de acerto homologado documentado para as fotos de operação.

## Reproduzir os testes

Na raiz do repositório:

```powershell
cd backend
python -m unittest discover -s tests -v
cd ..
node test-integration.cjs
node test-ui-flow.cjs
```

Para testes HTTP fora do Docker, instale `backend/requirements-dev.txt` (FastAPI, Pillow e NumPy). O pipeline completo usa Docker, que contém os pesos OCR e as bibliotecas nativas.

## Interpretação

- Testes com inferência simulada validam regras e contratos, não qualidade visual de OCR.
- Smoke tests em imagens sintéticas confirmam execução básica dos motores, não generalização para fotos industriais.
- Uma leitura ausente não deve ser contada automaticamente como leitura incorreta.
- Não calcular precisão, recall ou acurácia sem gabarito humano revisado e sem separação por identidade física da etiqueta.
- Confiança do OCR não é probabilidade calibrada.
- Revisão humana continua necessária antes de utilizar campos extraídos.

## Validation Studio V2.6/V2.7

O Validation Studio e o laboratório de restauração V2.7 estão em um workspace local experimental e não fazem parte deste repositório 0.2.0. Os resultados relatados para endpoints de segmentação foram registrados em desenvolvimento, mas a qualidade do isolamento no navegador e a avaliação contra máscaras humanas permanecem pendentes. A reanálise OCR/GS1 de derivados não está comprovada de ponta a ponta.

Consulte [../docs/VALIDATION-STUDIO-STATUS.md](../docs/VALIDATION-STUDIO-STATUS.md) para o status e os critérios de integração. Não interpretar o relatório do Studio como certificação desta versão do backend.
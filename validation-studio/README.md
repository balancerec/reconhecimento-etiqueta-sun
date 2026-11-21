# PRO-ACT Validation Studio ? c?digo experimental

Este diret?rio re?ne o c?digo fonte V2.6/V2.7.2, testes e relat?rios do workspace de desenvolvimento. O conte?do ? experimental e n?o est? integrado ao instalador nem ao aplicativo de produ??o da raiz.

## Conte?do

- `vision/`: API FastAPI, rotas de segmenta??o/restaura??o, valida??o humana e recupera??o de campos.
- `scripts/`: workers OpenCV/OCR, segmenta??o, retifica??o, testes e utilit?rios de desenvolvimento.
- `frontend/validation-studio/`: interface local do Studio.
- `vendor/legacy/`: componentes legados reaproveitados.
- `reports/`: relat?rios V2.6.1/V2.7.2, incluindo pend?ncias.
- `dataset-metadata/`: manifestos, predi??es, metadados de segmenta??o/restaura??o, registros de auditoria e revis?es em JSON, TXT e SQLite. Caminhos absolutos de m?quina foram removidos.
- `packages/`: dois pacotes de c?digo previamente inspecionados; nenhum cont?m entrada de foto.

## Dados e privacidade

Fotografias originais, recortes, retifica??es, m?scaras, previews e quaisquer PNGs/JPEGs n?o foram publicados. As pastas visuais locais `data/image-cache/` e os PNGs de `data/`, `evidence/` e `restoration/` foram exclu?dos. Os registros n?o visuais de OCR, revis?o, auditoria e configura??o foram inclu?dos conforme autoriza??o; os bancos SQLite verificados cont?m apenas registros textuais, sem colunas com imagem. Manifestos e resultados tiveram caminhos locais sanitizados.

Ambientes virtuais, wheels, caches de instala??o e sa?das tempor?rias n?o foram inclu?dos. O `.gitignore` bloqueia imagens e dados locais futuros.

Para executar, coloque as fotos em armazenamento local ignorado pelo Git e prepare um ambiente Python compat?vel. O workspace original usa um interpretador GPU configurado em `vision/api/app.py`; confira essa configura??o na m?quina antes de iniciar. N?o h? ainda um arquivo de depend?ncias completo validado em instala??o limpa.

## Limita??es declaradas

- O bot?o de isolamento recebeu corre??o de fluxo, mas sua qualidade visual ainda precisa ser validada no navegador.
- M?tricas de m?scara contra ground truth humano n?o foram homologadas.
- Rean?lise OCR/GS1 sobre imagem restaurada permanece pendente.
- N?o h? benchmark independente nem holdout por identidade f?sica.
- Integra??o com PRO-ACT Mobile, SAP e Zebra permanece desativada.

Consulte `reports/` e `../docs/VALIDATION-STUDIO-STATUS.md`. Relat?rios hist?ricos n?o equivalem a uma nova execu??o dos testes.


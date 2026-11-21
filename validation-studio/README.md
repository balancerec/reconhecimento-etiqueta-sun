# PRO-ACT Validation Studio — código experimental

Este diretório reúne o código fonte do Validation Studio V2.6/V2.7.2, testes e relatórios textuais/JSON do workspace de desenvolvimento. O conteúdo é experimental e não é integrado ao instalador nem ao aplicativo de produção da raiz.

## Conteúdo

- `vision/`: API FastAPI, rotas de segmentação/restauração, validação humana e recuperação de campos.
- `scripts/`: workers OpenCV, OCR, segmentação, retificação, testes e geração de relatórios.
- `frontend/validation-studio/`: interface do estúdio local.
- `vendor/legacy/`: componentes legados reaproveitados.
- `reports/`: relatórios V2.6.1/V2.7.2 em texto e JSON, incluindo pendências conhecidas.

## Dados e privacidade

Fotografias originais, recortes retificados, máscaras, PNGs RGBA e bancos SQLite não foram copiados para este repositório. As pastas locais `data/` e `evidence/` foram excluídas integralmente. Ambientes virtuais, wheels e arquivos ZIP de pacote também foram excluídos. O `.gitignore` desta pasta ignora esses tipos de arquivo e saídas locais.

Para executar, forneça fotografias localmente fora do Git e prepare o ambiente Python/API compatível com `scripts/Start-Studio.ps1` e `vision/api/app.py`. O workspace original configurava um Python GPU externo; confira a configuração local antes de rodar em outra máquina. Não há arquivo de dependências reprodutível validado neste pacote.

## Limitações declaradas

- O código de isolamento foi atualizado para solicitar a máscara quando necessário, mas a qualidade visual do recorte ainda precisa ser validada no navegador.
- As métricas de máscara contra ground truth humano não foram homologadas.
- A reanálise OCR/GS1 sobre imagem restaurada permanece pendente.
- Não há benchmark independente de precisão nem holdout por etiqueta física.
- Integração com PRO-ACT Mobile, SAP e Zebra permanece desativada.

Consulte `reports/` e `../docs/VALIDATION-STUDIO-STATUS.md`. Relatórios históricos não equivalem a uma nova execução dos testes.


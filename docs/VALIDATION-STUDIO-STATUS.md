# Estado do Validation Studio V2.6/V2.7

**Data:** 2026-11-21  
**Reposit?rio:** `balancerec/reconhecimento-etiqueta-sun`  
**C?digo experimental:** [`validation-studio/`](../validation-studio/)  
**Workspace de origem:** `%TEMP%\sun-v26-studio-20261120-01`

## Escopo e publica??o

O c?digo-fonte selecionado do Studio e seus relat?rios est?o em `validation-studio/`. Fotografias originais e derivados visuais foram exclu?dos. Registros JSON/TXT e SQLite sem pixels foram inclu?dos em `validation-studio/dataset-metadata/`; caminhos locais foram sanitizados. Os dois ZIPs de c?digo foram inspecionados e n?o cont?m entradas de imagem. Ambientes virtuais, wheels e cache visual foram exclu?dos. O `.gitignore` bloqueia imagens e dados locais futuros.

Este c?digo ? **experimental** e permanece separado do aplicativo 0.2.0: n?o est? integrado ao backend de produ??o, instalador, Docker Compose, Mobile, SAP ou Zebra.

## V2.6.1 ? sele??o e isolamento

O registro de desenvolvimento informa que as rotas de proposta, refinamento, confirma??o e recupera??o geraram m?scara e PNG RGBA em testes de API; foi registrado tamb?m hash original preservado nesses testes anteriores. A a??o **Isolar etiqueta** recebeu altera??o local para solicitar a m?scara caso ela ainda n?o esteja em mem?ria, partindo do centro do pol?gono ativo.

A verifica??o sint?tica do JavaScript e a resposta HTTP do arquivo servido foram registradas. **Isso n?o certifica a intera??o visual, precis?o do recorte ou transpar?ncia sem fundo.**

Pendente:

- validar clique, aura, ajuste de v?rtices, isolamento e exporta??o em navegador real;
- medir m?scara contra anota??o humana independente;
- comprovar alinhamento sob zoom, pan e rota??es;
- confirmar salvamento e recupera??o ap?s reiniciar;
- reexecutar duas vias em `20261120_005329.jpg` e verificar a consolida??o SSCC/QTDE.

## V2.7 ? restaura??o e rean?lise

A interface experimental oferece controles de restaura??o e worker local. O worker aplica denoise, unsharp masking (deblur conservador), CLAHE e ajustes de tom via OpenCV CPU; registra `ocr_status: pending` e `cuda_used: false`. N?o se deve anunciar deconvolu??o real ou acelera??o CUDA nessa etapa.

A rean?lise RapidOCR/ZXing sobre derivado n?o foi comprovada ponta a ponta. N?o h? prova reproduz?vel neste pacote de job real conclu?do, melhoria OCR ou compara??o de desempenho em imagem derivada.

## Resultados e valida??o

Os relat?rios V2.6.1/V2.7.2 est?o em `validation-studio/reports/`; metadados de predi??o e revis?o est?o em `validation-studio/dataset-metadata/`. Esses artefatos registram desenvolvimento e pend?ncias, n?o precis?o de produ??o.

- N?o h? holdout independente documentado.
- N?o se calculou nova acur?cia.
- Leituras restauradas n?o substituem previs?es hist?ricas nem ground truth.
- Nenhuma fotografia foi adicionada nesta atualiza??o.

## Reproduzir o workspace

Use Python compat?vel com Windows e instale as depend?ncias do projeto. O ambiente virtual local n?o foi publicado e ainda n?o h? arquivo de depend?ncias completo validado em instala??o limpa. A configura??o OCR hist?rica referencia um interpretador GPU externo; confira `validation-studio/vision/api/app.py` antes de executar. As fotografias devem permanecer em diret?rio local ignorado pelo Git.

O comando usado no workspace de desenvolvimento ?:

```powershell
.\.venv-api\Scripts\python.exe -m uvicorn vision.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Se a porta estiver em uso, verifique o servidor ativo antes de iniciar outra inst?ncia. Esse comando n?o comprova que os motores OCR estejam dispon?veis em instala??o limpa.

## Pr?ximos crit?rios

1. publicar depend?ncias reproduz?veis e configura??o sem caminhos espec?ficos desta m?quina;
2. executar testes automatizados e guardar logs reproduz?veis;
3. validar controles no navegador real, incluindo **Isolar etiqueta**;
4. medir m?scaras com refer?ncias humanas sem reutiliz?-las como holdout;
5. completar OCR/ZXing dos derivados sem sobrescrever resultados;
6. testar persist?ncia, duas vias e integridade dos originais;
7. manter integra??o com produ??o desativada at? homologa??o independente.


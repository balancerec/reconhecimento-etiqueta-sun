# Estado da documentação e do Validation Studio

**Data da revisão:** 2026-11-21  
**Repositório:** `balancerec/reconhecimento-etiqueta-sun`  
**Branch documental:** `docs/studio-v26-v27-status-2026-11-21`  
**Base consultada:** `main` em `60e3f7ecf66f0dda589580bb7e38af7c08275ad9`

## Escopo

O repositório Git contém o aplicativo local PRO-ACT Etiquetas versão 0.2.0: página integrada, API em `backend/`, instalador Windows e pipeline local DUN/SUN. A documentação dessa aplicação está no README da raiz e em `backend/VALIDACAO.md`.

O **Validation Studio V2.6/V2.7 não está incluído neste repositório**. Seu workspace de desenvolvimento é:

`C:\Users\balancerec\AppData\Local\Temp\sun-v26-studio-20261120-01`

Portanto, as funcionalidades do Studio descritas abaixo não fazem parte do instalador, do Docker Compose ou do GitHub Pages desta branch. Esta atualização registra a separação para que a documentação não apresente o protótipo como capacidade do pacote 0.2.0.

## Status do Studio experimental

### V2.6.1 — seleção e isolamento

Histórico de desenvolvimento registra endpoints de proposta, refinamento, confirmação e recuperação; geração de máscara/PNG RGBA; e preservação do hash original em testes de API anteriores. Esses resultados não foram repetidos durante esta atualização documental.

A ação **Isolar etiqueta** recebeu uma correção local para solicitar uma máscara quando ainda não existe segmentação em memória, usando o centro do polígono ativo como semente, e então carregar o PNG RGBA. A alteração passou pela verificação sintática de JavaScript e o servidor em `127.0.0.1:8000` serviu o novo `app.js`. Isso comprova que a alteração chegou ao arquivo servido; **não comprova a qualidade do recorte nem o funcionamento visual do botão**.

Ainda pendente:

- validação no navegador real do clique, overlay, edição, isolamento e exportação;
- medir inclusão de papelão/fundo contra máscara humana revisada;
- confirmar coordenadas sob zoom, pan e rotações;
- salvar e recuperar a geometria após reiniciar;
- testar novamente duas vias de `20261120_005329.jpg` e executar a consolidação SSCC/QTDE.

### V2.7 — restauração e reanálise

O workspace contém uma UI experimental de restauração e um worker local. A implementação é parcial: a reanálise RapidOCR/ZXing do derivado ainda não está integrada e verificada de ponta a ponta. Não há evidência reproduzível nesta atualização de um job real concluído, de OCR do derivado, de melhoria de leitura ou de comparação CPU/GPU do processamento.

Os controles de brilho, contraste, saturação, nitidez, denoise e CLAHE são ferramentas de transformação de imagem. Uma imagem aprimorada não confirma a verdade textual de SKU, lote, quantidade, validade ou SSCC.

## Separação de resultados e versões

- Resultados históricos V1–V2.5, gabaritos e fotografias originais permanecem fora deste repositório.
- Não se calculou nova acurácia nesta atualização.
- Não há holdout independente documentado para o Studio.
- As anotações humanas não devem ser usadas como lookup pelo reconhecimento automático.
- As fotos originais não devem ser editadas nem adicionadas ao Git.

## Reproduzir o aplicativo versionado neste repositório

Na raiz do checkout, a documentação da versão 0.2.0 usa:

```powershell
docker compose --project-name proact-etiquetas up --build -d
```

A página integrada é `http://localhost:8000/?local=1`; a documentação da API é `http://localhost:8000/docs`. Se a porta estiver ocupada, consulte primeiro o processo que já a está usando ou configure `LABEL_PORT` conforme o README. Não inicie uma segunda instância na mesma porta.

Os comandos de validação documentados para a versão 0.2.0 estão em `backend/VALIDACAO.md`. O escopo declarado ali inclui testes com inferência simulada e smoke tests com imagens sintéticas; não equivale a uma medição de acurácia em fotografias industriais.

## Próximos critérios para incorporar o Studio ao Git

Antes de documentar V2.6/V2.7 como funcionalidade disponível no produto, sincronizar o código do Studio para um caminho versionado e então:

1. executar e guardar logs de testes backend e frontend;
2. comprovar a validação visual no navegador, incluindo o botão Isolar etiqueta;
3. validar máscaras contra anotações humanas sem reutilizar o conjunto para estimar generalização;
4. comprovar persistência e preservação dos hashes originais;
5. executar OCR e ZXing nos derivados e registrar resultados sem substituir leituras históricas;
6. documentar explicitamente falhas, limitações e o status desativado da integração Mobile/SAP/Zebra.

Até esses critérios serem atendidos, classificar o Studio como **experimental, fora deste repositório e sem homologação de precisão**.

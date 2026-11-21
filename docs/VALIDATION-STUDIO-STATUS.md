# Estado do Validation Studio V2.6/V2.7

**Data:** 2026-11-21  
**Repositório:** `balancerec/reconhecimento-etiqueta-sun`  
**Código experimental:** [`validation-studio/`](../validation-studio/)  
**Workspace de origem:** `C:\Users\balancerec\AppData\Local\Temp\sun-v26-studio-20261120-01`

## Escopo e publicação

O código-fonte selecionado do Studio, seus relatórios de texto/JSON e a documentação estão versionados em `validation-studio/`. Fotografias originais e derivados visuais foram excluídos: as pastas locais `data/` e `evidence/` não foram copiadas. Também foram excluídos ambiente virtual, wheels e arquivos ZIP de pacote. O `.gitignore` do Studio bloqueia imagens, bancos locais, caches e saídas.

Este código é **experimental** e permanece separado do aplicativo 0.2.0: não está integrado ao backend de produção, instalador, Docker Compose, Mobile, SAP ou Zebra.

## V2.6.1 — seleção e isolamento

O registro de desenvolvimento informa que as rotas de proposta, refinamento, confirmação e recuperação geraram máscara e PNG RGBA em testes de API; foi registrado também hash original preservado nesses testes anteriores. A ação **Isolar etiqueta** recebeu alteração local para solicitar a máscara caso ela ainda não esteja em memória, partindo do centro do polígono ativo.

A verificação sintática do JavaScript e a resposta HTTP do arquivo servido foram registradas. **Isso não certifica a interação visual, precisão do recorte ou transparência sem fundo.**

Pendente:

- validar clique, aura, ajuste de vértices, isolamento e exportação em navegador real;
- medir máscara contra anotação humana independente;
- comprovar alinhamento sob zoom, pan e rotações;
- confirmar salvamento e recuperação após reiniciar;
- reexecutar duas vias em `20261120_005329.jpg` e verificar a consolidação SSCC/QTDE.

## V2.7 — restauração e reanálise

A interface experimental oferece controles de restauração e worker local. O worker atual aplica denoise, unsharp masking (rotulado como deblur conservador), CLAHE e ajustes de tom via OpenCV CPU; ele registra `ocr_status: pending` e `cuda_used: false`. Não se deve anunciar deconvolução real ou aceleração CUDA para essa etapa.

A reanálise RapidOCR/ZXing sobre derivado não foi comprovada ponta a ponta. Não há prova reproduzível neste pacote de job real concluído, melhoria OCR ou comparação de desempenho em imagem derivada.

## Resultados e validação

Os relatórios históricos V2.6.1/V2.7.2 foram preservados em `validation-studio/reports/`. Eles incluem pendências e resultados de desenvolvimento; não foram todos repetidos nesta publicação. Nenhum resultado constitui precisão de produção.

- Não há holdout independente documentado.
- Não se calculou nova acurácia.
- Leituras restauradas não substituem previsões históricas nem ground truth.
- Nenhuma fotografia foi adicionada ao repositório nesta alteração.

## Reproduzir o workspace

Use Python compatível com Windows e instale as dependências conforme os módulos importados pelo projeto. O ambiente virtual local não foi publicado e o workspace ainda não contém um arquivo de dependências completo e validado. A configuração OCR histórica referencia um interpretador GPU fora do repositório; adapte-a localmente antes de executar. As fotos devem permanecer em diretório local ignorado pelo Git.

O comando usado no workspace de desenvolvimento é:

```powershell
.\.venv-api\Scripts\python.exe -m uvicorn vision.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Se a porta estiver em uso, verifique o servidor ativo antes de iniciar outra instância. Este comando não comprova que os motores OCR estejam disponíveis em uma instalação limpa.

## Próximos critérios

Antes de habilitar o Studio ou alegar precisão:

1. publicar um arquivo de dependências e configuração sem caminhos específicos desta máquina;
2. executar os testes automatizados e guardar logs reproduzíveis;
3. validar cada controle no navegador real, incluindo **Isolar etiqueta**;
4. medir a qualidade das máscaras com referências humanas sem reutilizá-las como holdout;
5. completar OCR/ZXing dos derivados, com evidência de origem e sem sobrescrever resultados;
6. testar persistência, duas vias e integridade dos originais;
7. manter a integração com produção desativada até homologação independente.

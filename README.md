# PRO-ACT — Etiquetas DUN e SUN locais

Página de produção e inspeção industrial com leitura local em CPU. A versão 0.2.0 combina Tesseract (português/inglês), RapidOCR/ONNX e ZXing, sem enviar imagens para serviços de IA.

## Instalar no Windows

[Baixar Instalar-Etiquetas.exe](downloads/Instalar-Etiquetas.exe)

1. Execute o instalador na sua conta do Windows, com Docker Desktop instalado.
2. Aguarde o download e a preparação dos motores na primeira instalação. É necessário acesso à internet nessa etapa.
3. Abra **Abrir Etiquetas** na área de trabalho. O navegador acessará a página e a API no próprio computador.

O instalador procura o Docker primeiro em `%LOCALAPPDATA%\Programs\DockerDesktop`, incluindo a instalação informada nesta máquina. Não exige configurar o Ubuntu manualmente; o Docker Desktop pode usar seu WSL normalmente. É preciso que o Docker esteja em Linux containers e acessível à sua conta.

A instalação fica em `%LOCALAPPDATA%\PROACT\Etiquetas`. Fotos e histórico do backend ficam em `data`, relatórios em `reports` e logs de instalação em `logs`. Atualizações preservam essas pastas e a configuração `.env`. O histórico antigo da página continua no armazenamento do navegador e não é migrado automaticamente.

Atalhos criados: **Abrir Etiquetas**, **Parar Etiquetas**, **Diagnostico Etiquetas** e **Testar Etiquetas**. O teste procura imagens em `Pictures\ETIQUETAS` ou extrai `ETIQUETAS.rar` para uma nova pasta de relatórios. Envia somente ao servidor em localhost e gera JSON/HTML para conferência. As fotos fornecidas não são incluídas neste repositório nem no instalador.

Alternativa: extraia `downloads/Etiquetas-Windows.zip` e execute `Instalar.cmd`. Para gerar novamente o executável a partir do código:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File windows/build-installer.ps1
```

O executável é um bootstrap .NET com o projeto embarcado. Não instala drivers, não altera a distribuição Ubuntu e não apaga dados ao parar o aplicativo.

## O que mudou na leitura

- Localização de regiões brancas DUN e azuis SUN, com supressão de recortes duplicados.
- Retificação de perspectiva e tentativa das quatro orientações.
- Preservação das linhas, posições e texto bruto; extração de descrição e unidades como `750ML 12`.
- Múltiplas leituras Tesseract e uma leitura RapidOCR independente no mesmo recorte.
- Remoção auxiliar do fundo ciano e ajustes de contraste/limiarização.
- Consenso por campo; empates ficam ausentes e divergências são registradas. Não troca S por 5 silenciosamente.
- Leitura real de barras em variantes da imagem. Identificadores obtidos só das barras têm fonte `BARCODE`; isso não é apresentado como OCR concordante.
- Processamento em fila com progresso, limite de recursos e erros visíveis. A página descarta respostas de fotos anteriores.
- Regras de GTIN/SSCC, SKU, datas, LASTRO, capacidade e paletes parciais; revisão humana obrigatória.

## Usar sem instalador

Na raiz do projeto:

```powershell
docker compose --project-name proact-etiquetas up --build -d
```

Abra http://localhost:8000/?local=1. A documentação HTTP está em http://localhost:8000/docs. Configure `LABEL_PORT` em `.env` para outra porta. O instalador escolhe uma porta livre entre 8000, 8010, 8020 e 8030.

A API escuta apenas em localhost no compose. Antes de expor a outras máquinas, implemente autenticação, HTTPS, limites de acesso e política de retenção. A página no [GitHub Pages](https://balancerec.github.io/reconhecimento-etiqueta-sun/) continua disponível, mas não executa Docker: para usar o backend nela é necessária uma API HTTPS. Para este uso local, abra pelo atalho do Windows.

## Inspecionar e corrigir

Escolha o motor backend, envie a foto no scanner DUN ou SUN e selecione a etiqueta no painel de resultados. Confira os dados com a foto. As evidências indicam motor e fonte. Para salvar correções no servidor, edite os campos desse painel e informe operador e motivo. O JSON exportado preserva leituras originais, conflitos, barras, validações e correções.

O botão original de registro SUN mantém o parecer humano no histórico local do navegador. Esse parecer é separado do registro de correção no servidor. Nenhum resultado do OCR recebe aprovação automática.

## API

- `POST /v2/jobs`: upload multipart `image`, devolve tarefa com progresso.
- `GET /v2/jobs/{id}`: andamento ou resultado.
- `POST /v1/recognize`: interface síncrona compatível.
- `GET /v1/inspections/{id}` e `POST /v1/inspections/{id}/corrections`.
- `GET /health`: verifica os dois motores; resposta degradada se RapidOCR não carregar.

Limites: 12 MB, 24 megapixels, até seis regiões, uma inferência de cada vez, duas solicitações admitidas e orçamento aproximado de 210 segundos por imagem. Um processo Uvicorn nesta versão. A fila é transitória; resultados concluídos ficam em disco.

## Verificação e limites

Consulte [backend/VALIDACAO.md](backend/VALIDACAO.md). Testes de regras/HTTP usam motor simulado; o teste `smoke_vision.py` executa os motores reais em imagens sintéticas no Docker. A rotina GitHub Actions compila a imagem Docker e o instalador Windows.

Não há percentual de acerto comprovado para as fotos de operação. Detecção por cor/contornos ainda pode falhar em etiquetas encostadas, fundos brancos, cortes ou reflexos intensos. O consenso não torna uma leitura correta por si só; conflitos são expostos. Homologue com fotos reais de diferentes lotes e câmeras.

```powershell
cd backend
python -m unittest discover -s tests -v
cd ..
node test-integration.cjs
node test-ui-flow.cjs
```

Para testes HTTP fora do Docker, instale `backend/requirements-dev.txt` com FastAPI, Pillow e NumPy. Para o pipeline completo, use o Docker, que inclui pesos de OCR e bibliotecas nativas.

## Validation Studio V2.6/V2.7

O Validation Studio experimental e o laboratório de restauração V2.7 são desenvolvidos em um workspace local separado; não estão incluídos nesta versão 0.2.0 do repositório, do instalador ou do Docker. Os relatos anteriores de API não constituem validação visual, homologação do isolamento ou prova de melhoria do OCR. Consulte [docs/VALIDATION-STUDIO-STATUS.md](docs/VALIDATION-STUDIO-STATUS.md) para o escopo, limitações e critérios pendentes.
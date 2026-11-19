# Validação da versão 0.2.0

24 testes Python de regras, extração, correções, fila e contrato HTTP passaram no ambiente de desenvolvimento. Nesses testes a inferência visual é simulada. Passaram também os testes JavaScript de contrato, envio multipart, polling, cancelamento, descarte de resultado antigo e correção auditável. Sintaxe dos scripts Python e PowerShell verificada, e instalador .NET compilado.

Docker Desktop foi localizado no caminho informado, mas a sessão de desenvolvimento recebeu permission denied ao acessar o named pipe do motor; o WSL retornou acesso negado. Por isso a instalação na máquina e o OCR das fotos originais não foram executados daqui.

O workflow Local OCR and Windows installer executa o build Docker e smoke_vision.py: Tesseract e RapidOCR reais em imagens sintéticas DUN, SUN, rotação e múltiplas etiquetas. Consulte o resultado dessa execução no GitHub Actions. Esses testes não medem a acurácia em fotos de operação.

O atalho Testar Etiquetas gera relatórios locais para as fotos originais de Pictures/ETIQUETAS, sem publicá-las. É necessário conferir manualmente os resultados com as imagens. Não foi atribuída uma taxa de acerto ao sistema.

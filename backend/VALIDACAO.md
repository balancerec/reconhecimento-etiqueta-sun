# Estado da valida??o

Testes automatizados de regras executados no ambiente de entrega. Compila??o sint?tica Python verificada. Docker e Tesseract n?o estavam dispon?veis no PATH; a API e o OCR n?o foram executados nas fotos. N?o h? taxa de acerto medida.

Para homologar: iniciar o cont?iner; enviar cada imagem fornecida via /docs; conferir campos, coordenadas, barras e contagem de etiquetas manualmente. Repetir com rota??es de 90/180/270 graus, fotos desfocadas, reflexos, v?rios r?tulos e SKUs desconhecidos. Registrar valores esperados e obtidos. N?o usar o prot?tipo para aprova??o autom?tica.

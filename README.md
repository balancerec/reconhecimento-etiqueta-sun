# PRO-ACT Mobile — Reconhecimento de Etiquetas DUN e SUN

Aplicativo mobile para acompanhamento operacional e inspeção de etiquetas industriais de caixa (DUN) e unidade logística/palete (SUN).

## Comparativo visual das etiquetas

![Comparativo visual das etiquetas DUN e SUN, com dimensões físicas e exemplos esquemáticos de códigos de barras](docs/etiquetas-dun-sun.svg)

> Ilustração vetorial baseada no esquema de referência fornecido. Não é uma reprodução fiel das etiquetas impressas nem o arquivo PNG original. Os códigos de barras desenhados são apenas ilustrativos, não devem ser decodificados.

| Característica | DUN | SUN |
| --- | --- | --- |
| Aplicação | Caixa de produto | Palete / unidade logística |
| Dimensões físicas | **8 × 8 cm** (80 × 80 mm) | **10,1 × 15,1 cm** (101 × 151 mm) |
| Identificador | GTIN-14, quando aplicável e confirmado | SSCC-18 |
| Reconhecimento | OCR e leitura óptica do código | OCR, leitura do código e validação logística |

## Aplicativo

**[Abrir PRO-ACT Mobile no GitHub Pages](https://balancerec.github.io/reconhecimento-etiqueta-sun/)**

O reconhecimento por OCR e a decodificação de códigos são processos distintos. Uma leitura textual não deve ser apresentada como validação do código de barras sem decodificação real.

## Referências

- [Diagrama vetorial DUN × SUN](docs/etiquetas-dun-sun.svg)

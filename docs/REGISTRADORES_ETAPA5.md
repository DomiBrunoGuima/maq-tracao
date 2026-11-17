# Registradores — Etapa 5 (CLP DVP-SX2 + IHM DOP-107)

Fonte: planilha "Registradores IMAKE - ETAPA 5.xlsx" (gerada em 16/11/2026 a partir de
`VERSÃO FINAL IMAKE - ETAPA 5.isp` e `VERSÃO FINAL TRAÇÃO - ETAPA 5.dpa`).

O software conversa com a **IHM** por Modbus TCP, e a IHM republica os registradores
do CLP conforme a tabela Modbus do DOPSoft. Endereço no software = endereço da tabela − 1
(0-based). Os D são REAL (float32, 2 words, word order little). O campo `device` dos
registradores fica vazio de propósito: ele calcula o endereço Modbus do próprio CLP
(D→0x1000+n), que só vale numa ligação direta ao CLP, não pela IHM.

## O que mudou no CLP em relação ao mapa anterior

| Item | Antes | Etapa 5 |
|---|---|---|
| Deslocamento atual (tração) | D600 | **D210** (mm). D600 agora é a janela do regime elástico |
| Força atual (tração) | D92 / D650 (kgf) | **D2000** (N). D650 agora é cálculo interno da janela |
| Tensão máxima | D3004 | **D2010** (MPa) |
| Deslocamento máximo | D610 | **D214** (mm) |
| INICIAR flexão | M9 (o mesmo da tração) | **M11** |
| Força atual (flexão) | sem endereço confirmado | **D326** (N) |
| Deflexão atual (flexão) | D600 | **D442** (mm) |
| Planilha H0001 | 7 colunas | **13 colunas** (D2160…D2184) |

Como a força agora vem em N, `forca_clp_kgf` ficou `false` no config.json.
O limite de ruptura D2006 é comparado com D2000 no CLP, então também é em N.

## Tabela Modbus da IHM esperada pelo config.json

Linhas que já existiam e continuam iguais:

| Tabela da IHM | CLP | Tamanho | Usado pelo software (0-based) |
|---|---|---|---|
| Registers 40000 | D407 | 10 | 40000 velocidade D408 · 40004 desl. programado D412 |
| Registers 40010 | D2012 | 10 | 40009 força máxima D2012 (N) |
| Registers 40020 | D2002 | 10 | 40019 área D2002 · 40023 limite de ruptura D2006 · 40027 tensão máxima D2010 |
| Registers 40030 | D2022 | 10 | 40029 L0 D2022 |
| Coils 4000 | M5 | 10 | 3999 SUBIR M5 · 4000 DESCER M6 · 4001 PARAR M7 · 4003 INICIAR tração M9 · 4005 INICIAR flexão M11 |
| Coils 4010 | M30 | 10 | 4009 M30 · 4010 ruptura M31 · 4011 captura tração M32 |
| Coils 4020 | M100 | 10 | 4019 ZERA DESLOCAMENTO M100 · 4020 TARA M101 |

Linhas que precisam mudar ou ser criadas no DOPSoft:

| Tabela da IHM | Antes | Agora | Tamanho | Usado pelo software (0-based) |
|---|---|---|---|---|
| Registers 40040 | D600 | **D210** | 10 | 40039 deslocamento atual D210 · 40043 deslocamento máximo D214 |
| Registers 40050 | D92 | **D2000** | 2 | 40049 força atual da tração (N) |
| Registers 40060 | — | **D326** | 2 | 40059 força atual da flexão (N) |
| Registers 40070 | — | **D442** | 2 | 40069 deflexão atual da flexão (mm) |
| Coils 4030 | — | **X0** | 3 | 4029 emergência X0 · 4030 fim de curso inferior X1 · 4031 superior X2 |

Se as linhas da IHM forem montadas de outro jeito, ajuste o campo `address` de cada
registrador em Configurações → Controle (CLP), ou no config.json.

## Planilha H0001 (tração)

O parser lê os títulos da linha 2 do CSV, então aceita o arquivo antigo (7 colunas)
e o novo (13). As colunas novas Area_mm2, L0_mm, Veloc_mm_min e Desl_Prog_mm viram
os parâmetros do ensaio (área, L0, velocidade, deslocamento programado) e têm
prioridade sobre a leitura Modbus feita na hora da importação.

| Coluna | Título | CLP |
|---|---|---|
| 1 | Tensão_Pa | D2160 |
| 2 | Modulo_Elast | D2162 |
| 3 | Tensão_Max, | D2164 |
| 4 | Deform.Along | D2166 |
| 5 | Alonga_Ruptura | D2168 |
| 6 | Deslocamento | D2170 |
| 7 | Força_N | D2172 |
| 8 | Forca_Max_N | D2174 |
| 9 | Desl_Max_mm | D2176 |
| 10 | Area_mm2 | D2178 |
| 11 | L0_mm | D2180 |
| 12 | Veloc_mm_min | D2182 |
| 13 | Desl_Prog_mm | D2184 |

A planilha de flexão H0002 (23 colunas, D2114…D2158) ainda não é importada pelo
software: os ensaios de flexão são gravados pela leitura em tempo real.

## Pendências

- D408 (velocidade programada): a planilha diz REAL (2 words), mas a descrição diz
  "inteiro" e o D410 guarda a cópia em float (mm/min ×100). O software continua
  escrevendo como antes (inteiro de 16 bits, ×100, na tração).
- Fim do ensaio de flexão: o software usa M31 (ruptura). O fim por alvo de
  deslocamento é M15, que fica fora da linha Coils 4000 → M5 (tamanho 10).

<div class="capa">
<p class="capa-sup">MANUAL DE CÁLCULOS</p>
<h1 class="capa-titulo">SISTEMA DE ENSAIOS DE TRAÇÃO E FLEXÃO</h1>
<div class="capa-barra"></div>
<p class="capa-sup2">CONTEÚDO</p>
<p class="capa-projeto">Todas as contas que o software faz, com fórmula, unidade, origem dos dados e exemplo</p>
<table class="capa-tabela">
<tr><th>Documento nº</th><td>MC 01/26 — Revisão 00</td></tr>
<tr><th>Data de emissão</th><td>20/11/2026</td></tr>
<tr><th>Sistema</th><td>Software de coleta, controle e parametrização da máquina de ensaios (MaqTracao)</td></tr>
<tr><th>Versão do software</th><td>Branch master, commit 2f95527 (19/11/2026)</td></tr>
<tr><th>Público</th><td>Equipe técnica, comercial e laboratório de qualidade do cliente</td></tr>
<tr><th>Documentos relacionados</th><td>Manual completo do sistema e SDD — Sistema de Ensaios</td></tr>
<tr><th>Elaborado por</th><td>AUTOMATIC</td></tr>
</table>
<p class="capa-slogan">Facilitando e evoluindo</p>
<p class="capa-aviso">Este documento contém informações técnicas de propriedade da AUTOMATIC. Sua reprodução ou divulgação a terceiros depende de autorização prévia.</p>
</div>

# RESPOSTAS RÁPIDAS

As perguntas que mais aparecem, com a resposta curta. O detalhe de cada uma
está nas seções seguintes.

| Pergunta | Resposta curta |
|---|---|
| Como vocês calculam a tensão? | σ = F ÷ A. Força em N dividida pela área da seção em mm² dá MPa (1 N/mm² = 1 MPa). Ver item 3.2. |
| De onde vem a área? | É **digitada** pelo operador (na IHM ou na tela de Controle do software). O software não mede a área. Ver item 1.2. |
| Como é o alongamento? | Deslocamento do travessão ÷ comprimento de referência × 100. No relatório de lote a referência é a **distância entre garras**; nas telas é o **L₀**. Não há extensômetro. Ver item 3.4. |
| A força está em kgf ou N? | As contas são **sempre em N**. A tela mostra kgf = N ÷ 9,80665 só para leitura. Ver item 2.1. |
| Como é o módulo de elasticidade? | Reta ajustada (mínimos quadrados) na curva σ × ε, só no trecho elástico que o software detecta. A inclinação é o E. Ver item 3.5. |
| O que é o R²? | Mede o quanto os pontos do trecho elástico estão alinhados na reta. 1 = reta perfeita. Abaixo de 0,98 o software avisa. Ver item 3.6. |
| Como sai APROVADO/REPROVADO? | No relatório de lote, pega o **menor valor** entre os CPs e compara com o requisito digitado pelo laboratório (padrão: alongamento ≥ 350 %). Todos os requisitos atendidos = APROVADO. Ver item 7. |
| E na ISO 13953 (solda de topo)? | O operador marca cada CP como dúctil ou frágil. Todos dúcteis = APROVADO; um frágil = REPROVADO. Ver item 7.4. |
| Como o sistema sabe que rompeu? | A força cai pelo menos 25 % da força máxima em até 2 leituras (tração) ou mais de 50 % numa leitura (flexão). Ver item 3.12. |
| Quem define o requisito normativo? | O laboratório, no formulário do relatório. O software não tem requisito fixo, só o valor sugerido de 350 % para a NBR 15561. |
| Qual a resistência à flexão? | σf = 3·F·L ÷ (2·b·h²) na força máxima (ISO 178 / ASTM D790, 3 pontos). Ver item 4.1. |
| Média e desvio padrão? | Na tela de Comparação: média aritmética, desvio padrão **amostral** (divide por n − 1) e CV = desvio ÷ média × 100. Ver item 6. |

## Convenções usadas no manual

- Números no formato brasileiro: vírgula decimal (25,3 MPa).
- **F** = força (N), **d** = deslocamento do travessão (mm), **A** = área da
  seção (mm²), **L₀** = comprimento inicial de referência (mm), **t** = tempo (s).
- O exemplo-base da tração, usado ao longo do texto, é um corpo de prova de
  PE com **A = 40 mm²**, **L₀ = 50 mm**, distância entre garras **115 mm** e
  **Fmáx = 1.000 N**.
- "No código" aponta o arquivo e a função do repositório onde a conta está,
  para quem precisar conferir.

# 1. DE ONDE VÊM OS DADOS

Todo cálculo parte de dois tipos de informação: o que a máquina **mede** e o
que o operador **digita**. Saber separar os dois resolve a maioria das
dúvidas, porque um resultado estranho quase sempre vem de um valor digitado
errado.

## 1.1 Dados medidos (vêm da máquina)

| Grandeza | Unidade | Origem | Observação |
|---|---|---|---|
| Força F | N | Célula de carga, lida pelo CLP. O software lê da IHM por Modbus (registrador `forca_atual`, D2000 na tração e D326 na flexão). | Se o CLP entregar em kgf, o software converte para N (ver 2.1). |
| Deslocamento d | mm | Posição do travessão, lida pelo CLP (D210 na tração, D442 na flexão). | É o deslocamento **do travessão**, não de um extensômetro no corpo de prova. Zerado pelo botão "Zerar deslocamento". |
| Tempo t | s | Relógio do PC (aquisição direta, a cada 100 ms) ou coluna DATA/HORA da planilha da IHM (resolução de 1 s). | O tempo 0 é a primeira leitura do ensaio. |

Há dois caminhos para o ensaio chegar ao software, e as contas são as mesmas
nos dois:

1. **Aquisição direta** (tela Controle): o software lê força e deslocamento
   ponto a ponto durante o ensaio e calcula tudo.
2. **Planilha da IHM** (H0001.csv, por FTP ou pasta): a IHM grava as colunas
   e o software recalcula os resultados a partir delas. Nesse caminho algumas
   colunas (tensão, módulo local, alongamento) já vêm calculadas pela IHM e o
   software as usa como apoio, mas os resultados principais (σmáx = Fmáx ÷ A,
   alongamento por L₀) são refeitos a partir de F, d, A e L₀.

## 1.2 Dados digitados

| Dado | Unidade | Onde é digitado | Usado em |
|---|---|---|---|
| Área da seção A | mm² | IHM (D2002 / coluna Área da planilha) ou campo "Área" na tela Controle | Tensão σ, módulo E |
| Comprimento inicial L₀ | mm | IHM (D2022 / coluna L0) ou tela Controle | Deformação ε, alongamento nas telas, Rp0,2 |
| Distância entre garras | mm | Formulário do relatório (pré-preenchida pela norma, ex.: 115 mm na ISO 527-2) | Alongamento do relatório de lote |
| Largura b, espessura h, vão L | mm | Tela Flexão | Todas as contas de flexão |
| Velocidade | mm/min | Tela Controle/Flexão (vai para o CLP, D408) | Só controle da máquina; não entra em conta |
| Deslocamento programado | mm | Tela Controle/Flexão (D412) | Só controle da máquina |
| Limite de força | N | Tela Controle/Flexão (D2006) | O CLP usa para armar a detecção de ruptura |
| Requisitos normativos | conforme a propriedade | Formulário do relatório | Conclusão APROVADO/REPROVADO |
| Tipo de falha (dúctil/frágil) | — | Formulário do relatório (ISO 13953) | Conclusão da ISO 13953 |

## 1.3 Ordem de prioridade da área e do L₀

Quando o mesmo dado pode vir de mais de um lugar, o software segue esta ordem:

1. **Colunas da própria planilha do ensaio** (Etapa 5: Área, L0). São as mais
   confiáveis porque foram gravadas junto com o ensaio.
2. **Leitura Modbus da IHM** no momento em que o ensaio foi carregado.
3. **Valor digitado na tela Controle** (aquisição direta).
4. Se nada disso existir, o software **estima** a área e o L₀ pela própria
   planilha da IHM: A = mediana de F ÷ σ e L₀ = mediana de d ÷ ε, usando os
   pontos de carregamento. O painel de Qualidade dos dados avisa quando o L₀ foi
   estimado.

No código: `backend/main.py` (carregamento do CSV), `backend/parser.py`
(`parametros_da_planilha`), `backend/calculator.py` (`calculate_kpis`, bloco
"Área da seção e comprimento inicial").

# 2. UNIDADES E CONVERSÕES

## 2.1 kgf e newton

- **O que é:** a célula de carga pode estar configurada em kgf no CLP. O
  software trabalha sempre em newton.
- **Fórmula:** 1 kgf = **9,80665 N** (gravidade padrão).
  - Leitura do CLP em kgf → N: F(N) = F(kgf) × 9,80665.
  - Escrita do limite de força N → kgf: F(kgf) = F(N) ÷ 9,80665.
  - Mostradores da tela (Força atual, Força máxima): kgf = N ÷ 9,80665, com
    1 casa decimal.
- **De onde vem:** opção "Unidade da força no CLP" em Configurações → Controle
  (`forca_clp_kgf`). Na Etapa 5 o CLP já entrega em N, então a opção fica em N
  e não há conversão na leitura.
- **Exemplo:** 102 kgf × 9,80665 = **1.000,28 N**. E 1.000 N ÷ 9,80665 =
  **101,97 kgf**.
- **No código:** `backend/main.py` (`_forca_em_newton`, `N_POR_KGF`),
  `frontend/src/components/Common/Status.tsx` (`fmtKgf`).

Se a tela mostra valores de força cerca de 9,8 vezes maiores ou menores que o
esperado, a opção de unidade está trocada em relação ao CLP.

## 2.2 Outras unidades

| Conversão | Regra | Exemplo |
|---|---|---|
| Tensão | 1 N/mm² = 1 MPa | 1.000 N ÷ 40 mm² = 25 N/mm² = 25 MPa |
| Módulo | 1 GPa = 1.000 MPa | 996 MPa = 0,996 GPa |
| Força | 1 kN = 1.000 N | 1.000 N = 1 kN |
| Energia | 1 J = 1.000 N·mm | 5.500 N·mm = 5,5 J |
| Deformação | % = ε × 100 | ε = 0,02 → 2 % |

## 2.3 Como os números chegam do CLP

Isto não é cálculo de ensaio, mas explica por que um valor pode chegar
"embaralhado" quando a configuração está errada.

- **float32 (REAL):** cada valor ocupa 2 registradores de 16 bits no padrão
  IEEE 754. A ordem das palavras está como `little` (palavra baixa primeiro).
  Ordem trocada gera números absurdos (ex.: 1,2 × 10⁻³⁸).
- **Velocidade (D408):** na tração está configurada como inteiro com escala:
  o software envia velocidade × 100 (50 mm/min → 5000) e lê dividindo por 100.
- **Escala:** todo registrador tem um fator `scale`. Leitura = valor bruto ×
  scale; escrita = valor × scale.

No código: `backend/modbus_client.py` (`_decode_float32`, `capture_registers`,
`write_register`).

# 3. TRAÇÃO

## 3.1 Força máxima (Fmáx)

- **O que é:** a maior força registrada no ensaio.
- **Fórmula:** Fmáx = maior valor da série de força.
- **Unidade:** N (também mostrada em kN e kgf).
- **De onde vem:** força medida.
- **Exemplo:** se a maior leitura foi 1.000 N → Fmáx = 1.000 N = 1,000 kN =
  101,97 kgf.
- **No código:** `backend/calculator.py`, `calculate_kpis` (`forca_max_N`).

## 3.2 Tensão (σ) e tensão máxima (σmáx)

- **O que é:** força por unidade de área da seção do corpo de prova. A tensão
  máxima é a tensão na força máxima (também chamada de resistência à tração).
- **Fórmula:** σ = F ÷ A e **σmáx = Fmáx ÷ A**.
- **Unidade:** MPa (N/mm²).
- **De onde vem:** F medida; A digitada.
- **Exemplo:** 1.000 N ÷ 40 mm² = **25,0 MPa**.
- **No código:** `backend/calculator.py` (`tensao_max_calc_MPa`);
  `backend/acquisition.py` (coluna `Tensao_Pa` = F ÷ A, ponto a ponto).

Quando não há área informada, o software usa a maior tensão da coluna
calculada pela IHM (`tensao_max_MPa`). Telas, comparação e relatório sempre
preferem Fmáx ÷ A quando A existe.

**Cuidado com a área digitada.** Caso real (relatório 0016/2026): a área foi
digitada como 1,127 mm² em vez de 1.127 mm². Com Fmáx = 28.511 N, deu
28.511 ÷ 1,127 = 25.298 MPa, em vez de 28.511 ÷ 1.127 = **25,3 MPa**, que é o
normal para PE100. Tensão mil vezes maior que o esperado = vírgula na área.

## 3.3 Deformação (ε)

- **O que é:** quanto o corpo de prova esticou em relação ao comprimento
  inicial.
- **Fórmula:** ε = d ÷ L₀ (adimensional). Em %: ε × 100.
- **Unidade:** adimensional ou %.
- **De onde vem:** d medido (travessão); L₀ digitado.
- **Exemplo:** d = 1 mm com L₀ = 50 mm → ε = 0,02 = **2 %**.
- **No código:** `backend/acquisition.py` (coluna `Deform_Along`).

## 3.4 Alongamento

O alongamento é a deformação expressa em %, num instante específico. O
software mostra três versões, e é importante saber qual está em cada lugar.

| Nome | Fórmula | Onde aparece |
|---|---|---|
| Alongamento na força máxima | d(no instante da Fmáx) ÷ L₀ × 100 | Tela de resultado, Comparação, relatório completo |
| Alongamento final | d(última leitura do ensaio) ÷ L₀ × 100 | Tela de resultado, Comparação |
| **Alongamento final do relatório de lote** | d(última leitura) ÷ **distância entre garras** × 100 (se a distância entre garras não for informada, usa L₀) | Relatório resumido (NBR 15561) e conclusão |

- **Unidade:** %.
- **De onde vem:** d medido; L₀ e distância entre garras digitados.
- **Exemplo (tela):** d na Fmáx = 12 mm, L₀ = 50 mm → 12 ÷ 50 × 100 = **24 %**.
- **Exemplo (relatório de lote):** d final = 455,4 mm, garras = 115 mm →
  455,4 ÷ 115 × 100 = **396 %**.
- **No código:** `backend/calculator.py` (`alonga_calc_pct`,
  `alonga_final_pct`); `backend/report.py` (`_linhas_por_cp`).

**Por que o relatório usa a distância entre garras?** Em tubos de PE o
alongamento é medido pelo travessão, sem extensômetro. O travessão mede o
afastamento das garras, então a referência coerente é a distância entre elas.
O L₀ (base de medida marcada no corpo de prova) só seria a referência certa se
houvesse extensômetro.

**Variante (d − L₀) ÷ L₀ × 100.** O software também mostra o alongamento
calculado como (d − L₀) ÷ L₀ × 100, que só faz sentido quando o deslocamento
lido já inclui o comprimento inicial (posição absoluta da garra). Como a
máquina zera o deslocamento antes do ensaio, esse valor normalmente sai
**negativo** e não deve ser usado. Ele existe só para comparação.

## 3.5 Módulo de elasticidade (E)

- **O que é:** a rigidez do material no trecho elástico, a inclinação da reta
  inicial da curva tensão × deformação.
- **Fórmula:** E = inclinação da reta σ = E·ε + b ajustada por mínimos
  quadrados aos pontos do **trecho elástico linear** (ver 3.10).
- **Unidade:** MPa (também em GPa).
- **De onde vem:** σ (de F e A) e ε (de d e L₀).
- **Exemplo:** pontos do trecho elástico (ε; σ em MPa): (0,001; 1,02),
  (0,002; 1,98), (0,003; 3,01), (0,004; 4,00), (0,005; 4,99). A reta ajustada
  tem inclinação **E = 996 MPa** (0,996 GPa).
- **No código:** `backend/calculator.py`, `elastic_fit`
  (`modulo_trecho_elastico_MPa`).

Esse é o E que aparece em destaque na tela ("Módulo de elasticidade" e
"E (reta)") e na Comparação. Existem outras duas estimativas, mostradas só
como apoio na tela de resultado:

| Estimativa | Como é feita |
|---|---|
| Módulo E (média local) | Média do módulo ponto a ponto (dσ/dε) nos primeiros 30 % dos pontos de carregamento. No caminho da planilha, o módulo ponto a ponto vem da IHM. É o valor da tabela detalhada do relatório completo. |
| E regressão | Reta σ × ε nesses mesmos 30 % iniciais, recalculando σ = F ÷ A e ε = d ÷ L₀. |

**Importante:** como a deformação vem do travessão (e não de extensômetro), o E
inclui a folga e a deformação das garras e da máquina. Ele serve para comparar
ensaios entre si, mas costuma ser **menor** que o E de catálogo do material.

## 3.6 R² (coeficiente de determinação)

- **O que é:** nota de 0 a 1 que diz o quanto os pontos do trecho elástico
  estão sobre a reta do módulo. 1 = todos exatamente na reta.
- **Fórmula:** R² = 1 − SQres ÷ SQtot, em que SQres = Σ(σ − σ da reta)² e
  SQtot = Σ(σ − média de σ)².
- **Unidade:** adimensional.
- **Exemplo:** nos 5 pontos do exemplo do item 3.5, R² = **0,9999**.
- **Referências usadas pelo software:** R² ≥ 0,99 é a meta do detector do
  trecho elástico; abaixo de **0,98** o painel de qualidade mostra aviso
  "trecho elástico pouco linear".
- **No código:** `backend/calculator.py` (`elastic_fit`, `r2_elastico`);
  `backend/qualidade.py` (`R2_MIN = 0,98`).

## 3.7 Limite de escoamento convencional (Rp0,2)

- **O que é:** a tensão em que o material deixa de ser elástico, pela regra
  da deformação residual de 0,2 %.
- **Fórmula:** traça-se uma reta paralela à reta do módulo, deslocada 0,2 %
  (0,002) para a direita: σ = E·(ε − 0,002) + b. Rp0,2 é a tensão da curva no
  primeiro ponto, depois do trecho elástico, em que a curva fica igual ou
  abaixo dessa reta.
- **Unidade:** MPa.
- **Exemplo:** com E = 1.000 MPa e b = 0, em ε = 0,020 a reta deslocada vale
  1.000 × (0,020 − 0,002) = 18,0 MPa. Se a curva ali vale 17,9 MPa (abaixo da
  reta) e no ponto anterior estava acima, **Rp0,2 = 17,9 MPa**.
- **Quando não aparece:** sem trecho elástico identificado, ou se a curva
  nunca cruza a reta deslocada.
- **No código:** `backend/calculator.py`, `_rp02`.

## 3.8 Tensão de escoamento estimada

- **O que é:** indicador simples de onde a curva começa a "deitar".
- **Regra:** primeiro ponto do carregamento em que o módulo ponto a ponto cai
  mais de 10 % abaixo do módulo médio (item 3.5, média local). A tensão nesse
  ponto é a tensão de escoamento estimada.
- **Unidade:** MPa.
- **Exemplo:** módulo médio 1.000 MPa → limite 900 MPa. O primeiro ponto com
  módulo local abaixo de 900 MPa tinha σ = 16,5 MPa → **σesc ≈ 16,5 MPa**.
- **No código:** `backend/calculator.py` (`tensao_escoamento_MPa`).

Para relatório e cliente, prefira o Rp0,2, que segue regra de norma. A
tensão de escoamento estimada é só um indicador interno.

## 3.9 Rigidez, taxa de carregamento, energia e tempo

| Resultado | Fórmula | Unidade | Exemplo |
|---|---|---|---|
| Rigidez k | (maior F − menor F) ÷ (maior d − menor d), nos pontos do início até a Fmáx | N/mm | 1.000 N em 8 mm → **125 N/mm** |
| Taxa de carregamento | (maior F − menor F) ÷ (último t − primeiro t), nos pontos do início até a Fmáx | N/s | 1.000 N em 40 s → **25 N/s** |
| Energia absorvida | Área sob a curva força × deslocamento do ensaio inteiro (regra do trapézio) ÷ 1.000 | J | Pontos (0 mm; 0 N), (5; 600), (10; 1.000): ½·(0+600)·5 + ½·(600+1.000)·5 = 5.500 N·mm = **5,5 J** |
| Tempo até a força máxima | t no instante da Fmáx | s | Fmáx aos 40 s → **40 s** |
| Deslocamento máximo | Maior d do ensaio | mm | — |
| Deslocamento final | Último d do ensaio | mm | — |
| CV do módulo | Desvio padrão ÷ média do módulo ponto a ponto nos primeiros 30 % do carregamento | % | Indica a estabilidade do trecho inicial |

Observação: a rigidez k é a rigidez **média até a força máxima**, não só do
trecho elástico. Para a rigidez do trecho elástico, use o módulo E.

No código: `backend/calculator.py`, `calculate_kpis` (`rigidez_N_mm`,
`taxa_carregamento_N_s`, `energia_J`, `tempo_ruptura_s`).

## 3.10 Como o trecho elástico é encontrado

O trecho elástico é a base do E, do R² e do Rp0,2. O software o encontra
sozinho, sem o operador marcar pontos:

1. Considera só os pontos do início até a força máxima.
2. Calcula a **rigidez local** (ΔF ÷ Δd) em janelas de 5 pontos.
3. Marca como "linear" o ponto em que a rigidez local está acima de **50 %**
   da maior rigidez e é estável (variação, CV, abaixo de **20 %** na
   vizinhança).
4. O trecho elástico **começa** na primeira sequência de pontos lineares com
   pelo menos 5 % dos pontos (mínimo 3). Tudo antes disso é **acomodação**
   (folgas, garras se assentando).
5. O trecho **termina** quando a rigidez fica abaixo de **80 %** da máxima por
   mais de alguns pontos seguidos.
6. Por fim, o fim do trecho é encurtado até a reta força × deslocamento ter
   **R² ≥ 0,99**, mantendo no mínimo 5 pontos. Isso evita misturar o começo do
   escoamento no módulo.

No código: `backend/parser.py` (`_find_linear_region`, `_refine_elastic_end`).

## 3.11 Estágios do ensaio

Cada ponto da curva recebe um estágio, mostrado em cores no gráfico e na lista
de estágios com tempo de início e fim:

| Estágio | Regra |
|---|---|
| Acomodação | Antes do trecho elástico (item 3.10). |
| Elástico linear | Trecho do item 3.10. |
| Escoamento superior | Pico local de tensão logo após o trecho elástico, seguido de queda maior que 1,5 % (procurado nos primeiros 65 % do trecho até a Fmáx, com a curva suavizada). Comum em aço; em plásticos geralmente não aparece. |
| Patamar de escoamento | Após o escoamento superior, enquanto a tensão fica até 12 % acima do menor valor do patamar. |
| Encruamento | Do fim do patamar (ou do trecho elástico) até a força máxima. |
| Estricção | Da força máxima até a ruptura (a força cai enquanto o corpo afina). |
| Ruptura | O ponto da quebra (item 3.12). |
| Pós-ruptura | Leituras depois da quebra. |

No código: `backend/parser.py`, `_detect_stages`.

## 3.12 Detecção da ruptura

- **Regra principal:** depois da força máxima, procura uma **queda de pelo
  menos 25 % da Fmáx** de uma leitura para a seguinte. Se não achar, procura a
  mesma queda em duas leituras. O ponto de ruptura é a última leitura antes da
  queda.
- **Regra secundária:** se não houve queda brusca, aceita a queda gradual até
  a força ficar abaixo de **10 % da Fmáx**.
- **Sem nenhuma das duas:** o ensaio foi interrompido antes de romper (por
  exemplo, atingiu o deslocamento programado). O painel de qualidade avisa.
- **Exemplo:** Fmáx = 1.000 N. As leituras vão 980 N → 950 N → 620 N. A queda
  de 950 para 620 N (330 N) é maior que 250 N (25 %), então a ruptura é o ponto
  de **950 N**.
- **No código:** `backend/parser.py`, `_find_break`.

A máquina também tem a sua detecção, no CLP: o bit de ruptura (M31) arma
quando a força passa do "limite de força" e serve para **parar o ensaio**. O
software usa a regra acima para os **cálculos**, independente do CLP.

# 4. FLEXÃO A 3 PONTOS

Geometria digitada: **b** = largura, **h** = espessura, **L** = distância entre
apoios (vão), todos em mm. O exemplo-base é o corpo de prova da ISO 178:
**b = 10 mm, h = 4 mm, L = 64 mm**. As fórmulas são as mesmas na ISO 178 e na
ASTM D790.

A travessa desce durante a flexão e o CLP entrega a deflexão negativa. O
software inverte o sinal sozinho; todas as contas usam valores positivos.

## 4.1 Tensão de flexão (σf) e resistência à flexão (σfM)

- **O que é:** a tensão na face do corpo de prova sob flexão. A resistência à
  flexão σfM é a maior σf do ensaio (na força máxima).
- **Fórmula:** **σf = 3·F·L ÷ (2·b·h²)**.
- **Unidade:** MPa.
- **De onde vem:** F medida; b, h, L digitados.
- **Exemplo:** F = 50 N → σf = 3 × 50 × 64 ÷ (2 × 10 × 4²) = 9.600 ÷ 320 =
  **30,0 MPa**.
- **No código:** `backend/flexao/calculator.py` (`sigma_flexao`);
  `backend/flexao/acquisition.py` (coluna `Tensao_Flexao`).

## 4.2 Deformação de flexão (εf)

- **Fórmula:** **εf = 6·s·h ÷ L²**, em que s = deflexão (mm).
- **Unidade:** adimensional ou %.
- **Exemplo:** s = 2 mm → εf = 6 × 2 × 4 ÷ 64² = 48 ÷ 4.096 = 0,0117 =
  **1,17 %**.
- **No código:** `backend/flexao/calculator.py` (`epsilon_flexao`).

## 4.3 Módulo de flexão (Ef)

O software calcula dois módulos e mostra como principal o **cordal**, que é o
da norma:

| Módulo | Fórmula | Observação |
|---|---|---|
| **Cordal (principal)** | Ef = (σf2 − σf1) ÷ (εf2 − εf1) | ISO 178: εf1 = 0,0005 e εf2 = 0,0025. ASTM D790: εf1 = 0 e εf2 = 0,0025. As tensões σf1 e σf2 são interpoladas na curva. |
| Regressão | Inclinação da reta σf × εf no trecho elástico | Usado se o cordal não puder ser calculado. |

- **Unidade:** MPa (também em GPa).
- **Exemplo (cordal, ISO 178):** σf1 = 0,6 MPa em εf = 0,0005 e σf2 = 3,0 MPa
  em εf = 0,0025 → Ef = (3,0 − 0,6) ÷ 0,002 = **1.200 MPa**.
- **Conferência pela rigidez:** a mesma conta pode ser feita com força e
  deflexão: Ef = L³ ÷ (4·b·h³) × (ΔF ÷ Δs). Na geometria do exemplo,
  L³ ÷ (4·b·h³) = 102,4, então ΔF ÷ Δs = 11,72 N/mm dá 102,4 × 11,72 ≈
  1.200 MPa.
- **No código:** `backend/flexao/calculator.py`, `calculate_kpis`
  (`modulo_cordal_MPa`, `modulo_regressao_MPa`, `modulo_flexao_MPa`).

Na geometria do exemplo, εf = 0,0005 corresponde a s = 0,085 mm e
εf = 0,0025 a s = 0,427 mm. Por isso o zero do deslocamento e a acomodação
inicial pesam muito no módulo de flexão.

## 4.4 Demais resultados da flexão

| Resultado | Regra | Unidade |
|---|---|---|
| Força máxima | Maior F | N |
| Deflexão na força máxima | s no instante da Fmáx | mm |
| Deflexão máxima | Maior s | mm |
| Deformação de flexão máxima | Maior εf × 100 | % |
| Rigidez k | (maior F − menor F) ÷ (maior s − menor s), em todas as leituras menos a última (rigidez média do ensaio) | N/mm |
| Taxa de carregamento | (maior F − menor F) ÷ intervalo de tempo, nos mesmos pontos | N/s |
| Energia | Área sob força × deflexão (regra do trapézio) em todas as leituras menos a última ÷ 1.000 | J |
| Tensão de escoamento de flexão | Primeiro ponto em que o módulo local cai mais de 10 % abaixo do módulo de regressão | MPa |
| R² do trecho elástico | Mesma conta do item 3.6, na reta σf × εf | — |
| Tempo até a força máxima / tempo de ensaio | t na Fmáx / último t | s |

## 4.5 Estágios e ruptura na flexão

| Estágio | Regra |
|---|---|
| Acomodação | Antes do trecho elástico (mesmo detector da tração, item 3.10). |
| Elástico linear | Trecho detectado. |
| Pós-escoamento | Do fim do trecho elástico até o fim do ensaio. |
| Ruptura | Último ponto, se depois da força máxima houve uma queda **maior que 50 % da Fmáx** numa única leitura. |
| Fim do ensaio | Último ponto, se não houve quebra (parou na deflexão-alvo). Na flexão isso é normal. |

No código: `backend/flexao/parser.py` (`detect_stages`).

# 5. QUALIDADE DOS DADOS

O painel "Qualidade dos dados" não muda nenhum resultado; ele só avisa quando
um resultado merece conferência.

| Verificação | Verde (ok) | Aviso | Erro |
|---|---|---|---|
| Dados faltantes | Nenhum valor vazio e nenhuma lacuna de leitura. | Há valores vazios ou intervalos entre leituras **maiores que 5×** o intervalo típico (mediana). | Mais de **10 %** dos valores vazios. |
| Dados completos | **50 amostras** ou mais, cobrindo o carregamento. | Menos de 50 amostras ou carregamento não identificado. | — |
| Curva válida | Trecho elástico com **R² ≥ 0,98**. | R² < 0,98, ou deslocamento voltando em mais de **5 %** das leituras. | Força máxima nula ou trecho elástico não encontrado. |
| Ruptura detectada | Queda brusca encontrada (item 3.12). | Ensaio parece ter parado antes de romper. | — |
| Alongamento estimado (tração) | Informativo: L₀ informado; alongamento pelo travessão. | L₀ não informado; estimado pela planilha. | Sem L₀: não há alongamento. |
| Geometria (flexão) | b, h e L informados. | — | Falta b, h ou L: σf e Ef não podem ser calculados. |

No código: `backend/qualidade.py`.

# 6. COMPARAÇÃO DE ENSAIOS: MÉDIA, DESVIO PADRÃO E CV

Na tela de Comparação (e em "Comparar todos" do cliente), cada coluna da
tabela recebe três estatísticas:

- **Média:** x̄ = Σx ÷ n.
- **Desvio padrão amostral:** s = √[ Σ(x − x̄)² ÷ (n − 1) ]. Divide por
  **n − 1**, como pedem as normas de ensaio para uma amostra de corpos de
  prova. Com 1 ensaio só, não há desvio.
- **Coeficiente de variação:** CV = s ÷ |x̄| × 100 (%).

**Exemplo:** σmáx de 5 CPs = 25,3; 24,8; 25,9; 25,1; 24,6 MPa.
Média = **25,14 MPa**; desvio = **0,50 MPa**; CV = **2,0 %**.

As colunas usam os mesmos valores das telas e do relatório: σmáx = Fmáx ÷ A,
E do trecho elástico, alongamento por L₀.

No código: `frontend/src/components/Comparison/ComparisonView.tsx`
(`estatisticas`).

# 7. RELATÓRIO DE LOTE E CONCLUSÃO APROVADO/REPROVADO

## 7.1 Valores por corpo de prova

No relatório resumido (modelo pedido pela qualidade), cada CP do lote tem uma
linha com:

| Coluna | Cálculo |
|---|---|
| Fmáx (N) | Item 3.1 |
| σmáx (MPa) | Fmáx ÷ A (item 3.2); sem A, a tensão máxima da IHM |
| Alongamento final (%) | d final ÷ distância entre garras × 100 (item 3.4); sem distância entre garras, usa L₀ |

Com mais de um CP, a tabela ganha a linha **Mínimo**, com o menor valor de
cada coluna. A qualidade pediu só o mínimo porque é ele que vai para a
conclusão.

## 7.2 Requisitos

O laboratório digita os requisitos no formulário do relatório. Cada requisito
tem propriedade (tensão máxima, alongamento final ou força máxima), critério
(≥ mínimo exigido ou ≤ máximo permitido), valor e referência (ex.: NBR 15561).
O valor sugerido é **alongamento ≥ 350 % (NBR 15561)**, e o formulário
reaproveita os requisitos do último relatório. O software não tem requisito
normativo fixo: quem define é o laboratório.

## 7.3 Regra da conclusão (NBR 15561 e demais)

1. Para cada propriedade com requisito de **mínimo (≥)**, pega o **menor**
   valor entre os CPs. Para requisito de **máximo (≤)**, pega o **maior**.
2. Compara esse valor com o requisito: atende = **Aprovado** na linha; não
   atende = **Reprovado**.
3. **Conclusão = APROVADO** se todas as linhas com requisito forem aprovadas;
   basta uma reprovada para **REPROVADO**.
4. Sem nenhum requisito preenchido, vale a conclusão escrita à mão pelo
   laboratório (campo "Conclusão manual"); se ficar em branco, o relatório sai
   sem conclusão.

**Exemplo:** alongamento final de 5 CPs = 412; 388; 405; 371; 396 %. Requisito
≥ 350 %. Menor valor = 371 % ≥ 350 % → linha **Aprovado** → conclusão
**APROVADO**. Se um CP tivesse dado 340 %, o menor valor seria 340 % < 350 % →
**REPROVADO**, mesmo com os outros quatro acima.

Usar o **menor valor** (e não a média) é a regra conservadora: o lote só passa
se o pior corpo de prova passar.

No código: `backend/report.py` (`_conclusao_resumida`, `_estatisticas`).

## 7.4 ISO 13953 (solda de topo)

Na ISO 13953 o critério não é numérico: o laboratório classifica o modo de
falha de cada CP.

- A tabela traz a **força máxima** de cada CP e o **tipo de falha** escolhido
  pelo operador (Dúctil ou Frágil).
- **APROVADO** se todos os CPs forem dúcteis.
- **REPROVADO** se **algum** CP for frágil.
- Se faltar classificar algum CP (e nenhum for frágil), não há conclusão
  automática: vale a conclusão manual.

Regra confirmada com a qualidade da IMAKE em 19/11/2026.

No código: `backend/report.py` (`_conclusao_iso13953`, `_falha`).

## 7.5 Gráficos do relatório

| Gráfico | Eixo X | Eixo Y |
|---|---|---|
| Tensão × Alongamento | d ÷ distância entre garras × 100 (%) | F ÷ A (MPa) |
| Tensão × Deformação | d ÷ L₀ × 100 (%) | F ÷ A (MPa) |
| Tensão × Deslocamento | d (mm) | F ÷ A (MPa) |
| Força × Deslocamento | d (mm) | F (N) |

Tensão × Alongamento e Tensão × Deformação têm formatos iguais e escalas
diferentes, porque usam bases diferentes (garras e L₀). O ponto marcado em cada
curva é a força máxima.

# 8. PROTEÇÃO DE SOBRECARGA

- **O que é:** parada automática para proteger a célula de carga.
- **Regra:** a cada leitura de força, |F| ÷ 9,80665 (em kgf) é comparado com o
  limite configurado. Se **|F| ≥ limite**, o software manda o pulso de PARAR e
  mostra o alarme. Enquanto a força continuar acima, o pulso é repetido a cada
  **2 s**. O módulo |F| faz a proteção valer para tração e compressão.
- **Unidade do limite:** kgf (a tela mostra o equivalente em N).
- **Exemplo:** limite = 500 kgf = 4.903 N. Uma leitura de 4.910 N = 500,7 kgf
  ≥ 500 kgf → parada.
- **Limite 0** desliga a proteção.
- **No código:** `backend/sobrecarga.py` (`MonitorSobrecarga.verificar`).

# 9. VALORES SUGERIDOS PELAS NORMAS

Ao escolher a norma, o software pré-preenche velocidade, L₀ (ou vão) e
distância entre garras. São valores de partida, não cálculos: conferir sempre
a edição vigente da norma.

| Norma | Tipo | Corpo de prova | Velocidade (mm/min) | L₀ ou vão (mm) | Garras (mm) |
|---|---|---|---|---|---|
| ISO 527-2 | Tração | Tipo 1A (170 × 10 × 4) | 50 | 75 | 115 |
| ASTM D638 | Tração | Tipo I (165 × 13 × 3,2) | 5 | 50 | 115 |
| ABNT NBR ISO 6892-1 | Tração | Proporcional (L₀ = 5,65·√S₀) | por taxa | depende da seção | — |
| ASTM E8/E8M | Tração | Chapa 12,5 mm | por taxa | 50 | — |
| ASTM D3039 | Tração | 250 × 25 × 2,5 | 2 | — | — |
| ISO 37 | Tração | Gravata tipo 1 | 500 | 25 | — |
| ASTM D412 | Tração | Matriz C | 500 | 25 | — |
| ISO 178 | Flexão | 80 × 10 × 4 | 2 | vão 64 (16·h) | — |
| ASTM D790 | Flexão | 127 × 12,7 × 3,2 | 1,4 | vão 51,2 | — |

Na ASTM D790 a velocidade sai de R = 0,01·L² ÷ (6·d), com d = espessura:
0,01 × 51,2² ÷ (6 × 3,2) = 1,37 ≈ 1,4 mm/min. Na NBR ISO 6892-1, L₀ = 5,65·√S₀,
com S₀ = área da seção: S₀ = 50 mm² → L₀ = 5,65 × 7,07 = 40 mm.

No código: `backend/normas.py`.

# 10. PERGUNTAS DIFÍCEIS E ARMADILHAS

**"O alongamento de vocês é medido com extensômetro?"**
Não. É calculado pelo deslocamento do travessão. Por isso o relatório de lote
usa a distância entre garras como base. É a prática usual para tubos de PE,
em que o alongamento é muito grande (centenas de %).

**"Por que o módulo deu menor que o do catálogo?"**
Porque, sem extensômetro, a deformação inclui a acomodação das garras e a
deformação da própria máquina. O E do software é bom para comparar lotes entre
si, não para substituir um ensaio de módulo com extensômetro.

**"A tensão deu um valor absurdo."**
Quase sempre é a área digitada: vírgula no lugar errado (1,127 em vez de 1.127)
ou unidade errada (cm² em vez de mm²: 1 cm² = 100 mm²).

**"A força está 9,8 vezes maior/menor."**
A opção de unidade da força (kgf/N) em Configurações → Controle não está igual
à do CLP.

**"Por que o alongamento (d − L₀)/L₀ deu negativo?"**
Porque o deslocamento é zerado antes do ensaio, então d já é o alongamento.
Essa variante só serviria se d fosse a posição absoluta da garra. Use d ÷ L₀
(ou d ÷ garras no relatório).

**"Por que a tela e o relatório mostram alongamentos diferentes?"**
A tela usa L₀ e o relatório de lote usa a distância entre garras (item 3.4).
Com L₀ = 50 mm e garras = 115 mm, o mesmo d dá alongamentos que diferem por um
fator de 2,3.

**"O resultado muda se eu abrir o ensaio de novo?"**
Não. Os dados gravados (força, deslocamento, tempo) não são alterados, e as
contas são refeitas sempre do mesmo jeito. Depois do ensaio, só mudam o
resultado do relatório os valores digitados no formulário dele: distância
entre garras, requisitos e tipo de falha.

**"Como vocês arredondam?"**
As contas usam todos os dígitos. O arredondamento é só na exibição: força com
1 casa no relatório, tensão e alongamento com 2 casas, módulo com 1 casa em
MPa ou 3 em GPa, R² com 4 casas.

**"O tempo do ensaio é preciso?"**
Na aquisição direta, as leituras são a cada 100 ms. Na planilha da IHM, a
hora tem resolução de 1 segundo; a taxa de carregamento e o tempo até a Fmáx
herdam essa resolução.

# 11. ONDE CADA CÁLCULO ESTÁ NO CÓDIGO

| Cálculo | Arquivo | Função / chave |
|---|---|---|
| σ, ε, A%, módulo local (aquisição direta) | `backend/acquisition.py` | `build_ensaio_dataframe` |
| Resultados da tração | `backend/calculator.py` | `calculate_kpis` |
| Reta do trecho elástico, E e R² | `backend/calculator.py` | `elastic_fit` |
| Rp0,2 | `backend/calculator.py` | `_rp02` |
| Trecho elástico, estágios e ruptura (tração) | `backend/parser.py` | `_find_linear_region`, `_refine_elastic_end`, `_detect_stages`, `_find_break` |
| Área e L₀ da planilha | `backend/parser.py` | `parametros_da_planilha` |
| σf, εf, módulo local (flexão) | `backend/flexao/acquisition.py` | `build_ensaio_flexao_dataframe`, `sentido_positivo` |
| Resultados da flexão, módulo cordal | `backend/flexao/calculator.py` | `calculate_kpis`, `sigma_flexao`, `epsilon_flexao` |
| Estágios da flexão | `backend/flexao/parser.py` | `detect_stages` |
| Qualidade dos dados | `backend/qualidade.py` | `avaliar_qualidade`, `avaliar_qualidade_flexao` |
| Conversão kgf ↔ N | `backend/main.py` | `_forca_em_newton` |
| Leitura de float32 e escala | `backend/modbus_client.py` | `_decode_float32`, `capture_registers` |
| Sobrecarga | `backend/sobrecarga.py` | `MonitorSobrecarga.verificar` |
| Média, desvio padrão e CV | `frontend/src/components/Comparison/ComparisonView.tsx` | `estatisticas` |
| Valores por CP, mínimo e conclusão | `backend/report.py` | `_linhas_por_cp`, `_estatisticas`, `_conclusao_resumida`, `_conclusao_iso13953` |
| Normas cadastradas | `backend/normas.py` | `NORMAS` |

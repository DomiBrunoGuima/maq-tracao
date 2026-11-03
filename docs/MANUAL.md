# Sistema de Ensaios de Tração e Flexão — Manual completo

Versão do manual: novembro de 2026 · Software 1.0

Este manual cobre o sistema inteiro: instalação, configuração, operação dos
ensaios, resultados, relatórios, clientes, backup, diagnóstico e referência
técnica. As seções 1 a 9 são para quem opera a máquina. As seções 10 a 14 são
para o técnico que instala e configura.

**Sumário**

1. [Visão geral](#1-visão-geral)
2. [Abrindo o sistema e a tela principal](#2-abrindo-o-sistema-e-a-tela-principal)
3. [Ensaio de tração](#3-ensaio-de-tração)
4. [Resultados de tração](#4-resultados-de-tração)
5. [Ensaio de flexão a 3 pontos](#5-ensaio-de-flexão-a-3-pontos)
6. [Alerta de sobrecarga e parada automática](#6-alerta-de-sobrecarga-e-parada-automática)
7. [Comparação de ensaios](#7-comparação-de-ensaios)
8. [Clientes, busca e dados do teste](#8-clientes-busca-e-dados-do-teste)
9. [Relatórios](#9-relatórios)
10. [Instalação](#10-instalação)
11. [Configurações](#11-configurações)
12. [Backup e restauração](#12-backup-e-restauração)
13. [Solução de problemas](#13-solução-de-problemas)
14. [Referência técnica](#14-referência-técnica)

---

## 1. Visão geral

O sistema é um programa que roda no computador ao lado da máquina de ensaios.
Ele:

- **comanda** a máquina: inicia, para, zera deslocamento, faz a tara e envia
  velocidade, curso (deslocamento programado) e limite de força;
- **registra** força e deslocamento várias vezes por segundo e desenha a curva
  durante o ensaio;
- **calcula** os resultados (força e tensão máximas, módulo de elasticidade com
  R², Rp0,2, alongamento, energia, resistência e módulo de flexão);
- **documenta**: guarda o ensaio com cliente, amostra, norma e operador e gera
  o relatório técnico numerado.

Dois tipos de ensaio: **tração** (ISO 527-2, ASTM D638, ABNT NBR ISO 6892-1,
ASTM E8, ASTM D3039, ISO 37, ASTM D412) e **flexão a 3 pontos** (ISO 178,
ASTM D790).

### Como as partes se conectam

```
Máquina (motor, garras, célula de carga)
   │
CLP Delta DVP ── controla o ensaio e lê os sinais
   │  (Link1 da IHM)
IHM Delta DOP ── tela da máquina; ponte para a rede
   │  Ethernet, Modbus TCP, porta 502 (IP padrão 192.168.11.10)
Computador ──── este sistema (servidor local + tela no navegador)
```

O computador **não fala direto com o CLP**: ele lê e escreve na memória
Modbus da IHM, e a IHM repassa para os registradores D/M/X do CLP conforme a
tabela de troca de dados configurada no DOPSoft (ver
[14.4](#144-mapa-de-registradores-ihm--clp)).

Tudo fica no próprio computador: ensaios, clientes e relatórios são gravados num
banco local (`tracao.db`) e não dependem de internet.

---

## 2. Abrindo o sistema e a tela principal

### Abrindo

1. Ligue a máquina e a IHM. A IHM precisa estar na rede para o computador
   enxergar a máquina.
2. Ligue o computador. O sistema inicia sozinho com o Windows, em segundo plano.
3. Dê dois cliques no atalho **Máquina de Tração** da área de trabalho. A tela
   abre numa janela própria.
4. Confira o indicador **CLP CONECTADO** no canto superior esquerdo. Verde: a
   máquina responde. Vermelho: veja [Solução de problemas](#13-solução-de-problemas).

Logo depois de ligar o computador, a tela pode levar alguns segundos para
carregar. Se aparecer em branco, aguarde e aperte **F5**.

Fechar a janela **não** desliga o sistema; ele continua rodando. Basta abrir o
atalho de novo.

### A tela principal

| Área | O que faz |
|---|---|
| Indicador de conexão | Verde quando o computador está lendo a força pela IHM, com o IP dela. Em modo simulador mostra "simulador". |
| Tema | Alterna entre fundo escuro e claro. |
| **TRAÇÃO** / **FLEXÃO** | Abrem a tela de controle de cada ensaio. O botão FLEXÃO some se a máquina não tiver o dispositivo de flexão ([11.2](#112-geral)). |
| Busca | Encontra clientes, testes e relatórios pelo nome, amostra ou número. Ignora acentos. Filtros limitam o tipo. |
| **Comparar (n)** | Abre a comparação dos ensaios marcados com "+ Comparar". |
| Reimportar todos | Reprocessa os ensaios importados de CSV com os cálculos atuais (mantém o cadastro de cada um). |
| Lista de ensaios | Todos os ensaios salvos, do mais novo ao mais antigo. Os de flexão têm a etiqueta FLEXÃO. Clique para abrir o resultado. |
| Clientes, Relatórios, Configurações | Menu inferior esquerdo. |

---

## 3. Ensaio de tração

### 3.1 Preparando

1. Clique em **TRAÇÃO**.
2. Preencha os **Dados do teste**: cliente, amostra (ex.: `Lote 23 · CP 1`),
   norma e operador. Esses dados vão automaticamente para o ensaio gravado e
   para o relatório. O botão **+** cadastra um cliente novo ali mesmo.
3. Ao escolher a **norma**, o sistema sugere velocidade, L₀ e corpo de prova
   (tabela em [14.6](#146-normas-cadastradas)). São valores de partida: confira
   a edição vigente da norma.
4. Confira os parâmetros:

   | Campo | Unidade | Observação |
   |---|---|---|
   | Deslocamento programado | mm | Curso máximo do travessão. |
   | Velocidade | mm/min | |
   | Limite de força (opcional) | N | Digitado em N; se a força do CLP estiver em kgf, o sistema converte antes de enviar. Precisa ser maior que zero. |
   | Área da seção | mm² | Entra direto no cálculo da tensão σ = F/A. |
   | Comprimento inicial L₀ | mm | Entra direto no alongamento e na deformação. |

5. Escolha o **sentido**: *Cima* para tração.

Meça o corpo de prova antes de cada ensaio. Área e L₀ errados dão tensão e
alongamento errados.

### 3.2 Executando

1. **Zerar deslocamento** — limpa o deslocamento que sobrou do ensaio anterior.
2. **Tara** — zera a célula de carga com o corpo de prova preso e sem carga.
   Atenção: a Tara também **para um ensaio em andamento**.
3. **Iniciar ensaio** — o sistema escreve os parâmetros na máquina, dá um pulso
   no sentido escolhido e depois o pulso de início.
4. Acompanhe pela barra de status: **Parado → Preparando → Executando →
   Ruptura detectada → Finalizado**. Força atual, deslocamento atual e força
   máxima aparecem em números grandes (força em kgf) e nos gráficos Força ×
   Tempo e Deslocamento × Tempo.
5. Também aparecem, quando mapeados: estado do material (Íntegro/Ruptura),
   tensão máxima e deslocamento máximo calculados pelo CLP, e os sinais de
   Emergência, Limite superior e Limite inferior.

Para interromper a qualquer momento, use **Parar** na tela ou a emergência da
máquina. Parar dá um pulso no comando de parada e desliga os dois sentidos.

### 3.3 Gravação

O ensaio é gravado sozinho:

- quando o CLP sinaliza a ruptura (bit de ruptura), ou
- quando o ensaio é parado pela tela, ou a tela é fechada, com dados já
  coletados.

Ensaios com menos de 10 leituras de força não são gravados. Ao gravar aparece a
mensagem **Ensaio gravado** com o link para abrir o resultado. O nome do ensaio
segue o padrão `CLP_AAAAMMDD_HHMMSS`.

Ensaios já gravados nunca são apagados nem sobrescritos por atualizações do
programa.

---

## 4. Resultados de tração

Clique no ensaio na lista. A tela mostra:

1. **Resultados principais**: força máxima, tensão máxima, módulo de
   elasticidade, alongamento e os demais indicadores.
2. **Curva tensão × deformação**. A faixa verde é o trecho elástico e a linha
   vermelha tracejada é a reta ajustada. Clique num ponto para abrir a
   **Inspeção do ponto**, que mostra força (e a conversão kgf × 9,80665),
   deslocamento, área, L₀ e a conta de σ = F ÷ A naquele ponto.
3. **Qualidade dos dados**: selo verde "Dados confiáveis" quando está tudo
   certo; aviso amarelo ou vermelho com a explicação do que conferir.
4. **Trecho elástico**: E, R² e Rp0,2.
5. **Estágios**: acomodação, elástico linear, escoamento, encruamento,
   estricção, ruptura e pós-ruptura, com o tempo de cada um.
6. **Outros gráficos**: força × deslocamento, força × tempo, módulo × tempo,
   tensão × tempo. Clique para trocar a curva principal.
7. Botões **Dados do teste**, **+ Comparar** e **Gerar Relatório**.

### O que significa cada resultado

| Sigla | Significado |
|---|---|
| Fmáx | Maior força do ensaio (N ou kN). |
| σmáx | Tensão máxima = Fmáx ÷ área da seção (MPa = N/mm²). |
| E | Módulo de elasticidade: inclinação da reta σ × ε no trecho elástico. |
| R² | Qualidade do ajuste da reta. Acima de 0,99 indica trecho elástico bem definido; abaixo de 0,98 gera aviso. |
| Rp0,2 | Tensão de escoamento convencional: onde a curva cruza a reta elástica deslocada de 0,2 % de deformação. |
| Alongamento A% | (Lf − L₀) ÷ L₀ × 100, pelo deslocamento do travessão (sem extensômetro). |
| Ruptura | Queda brusca de força: a força cai ao menos 25 % de Fmáx em até 2 leituras. Sem isso, aceita queda gradual abaixo de 10 % de Fmáx. Sem nenhuma das duas, o ensaio foi interrompido antes de romper. |
| Energia | Área sob a curva força × deslocamento até a ruptura, em joules. |
| Rigidez k | Força por milímetro no trecho elástico (N/mm). |
| L₀ | Comprimento inicial de referência do corpo de prova. |

### Qualidade dos dados

| Verificação | Verde | Aviso / erro |
|---|---|---|
| Dados faltantes | Nenhum valor vazio nem lacuna de leitura. | Valores vazios ou intervalos entre leituras maiores que 5× o normal. Erro acima de 10 % vazio. |
| Dados completos | 50 amostras ou mais cobrindo o carregamento. | Menos de 50 amostras ou carregamento não identificado. |
| Curva válida | Trecho elástico com R² ≥ 0,98. | Força máxima nula, trecho elástico não encontrado, R² baixo, ou deslocamento voltando em mais de 5 % das leituras. |
| Ruptura detectada | Queda brusca encontrada. | Ensaio parece ter parado antes de romper. |
| Alongamento estimado | L₀ informado (informativo). | L₀ não informado (estimado) ou ausente (sem alongamento). |

---

## 5. Ensaio de flexão a 3 pontos

### 5.1 Executando

1. Clique em **FLEXÃO** (aba **Controle & Aquisição**).
2. Preencha os **Dados do teste**, como na tração. A norma sugerida é a ISO 178.
3. Informe a geometria em mm: **largura b**, **espessura h** e **distância
   entre apoios L**.
4. Informe **velocidade** e **deflexão-alvo**. O limite de força é opcional. O
   sentido normal é **Baixo**.
5. **Zerar deslocamento**, **Zerar célula** e **Iniciar ensaio**. O resultado é
   gravado ao final (bit de fim de ensaio, Parar ou fechamento da tela).

A deflexão vem negativa do CLP porque a travessa desce. O sistema inverte o
sinal sozinho, e os cálculos e gráficos usam deflexão positiva.

### 5.2 Resultados de flexão

Na aba **Resultados**, ou clicando no ensaio com a etiqueta FLEXÃO:

| Sigla | Significado |
|---|---|
| Fmáx | Força máxima. |
| σfM | Resistência à flexão: σf = 3·F·L ÷ (2·b·h²) na força máxima. |
| Ef | Módulo de flexão pela regressão no trecho elástico, e o módulo cordal da norma: Ef = (σf2 − σf1) ÷ (εf2 − εf1), com εf1 = 0,0005 e εf2 = 0,0025 na ISO 178, ou 0 e 0,0025 na ASTM D790. |
| εf | Deformação de flexão: εf = 6·s·h ÷ L², com s = deflexão. |
| δ | Deflexão máxima. |
| k | Rigidez (N/mm). |
| Energia | Área sob força × deflexão até o pico. |

Qualidade dos dados, trecho elástico com R², estágios, Inspeção do ponto,
Dados do teste, Comparar e Gerar Relatório funcionam como na tração. O seletor
no topo troca entre os ensaios de flexão salvos.

Se a máquina não tiver dispositivo de flexão, o técnico desliga a opção
**Máquina com flexão** ([11.2](#112-geral)): o botão FLEXÃO e os ensaios de
flexão somem e o programa recusa iniciar esse ensaio.

---

## 6. Alerta de sobrecarga e parada automática

<!-- SOBRECARGA: seção completada quando o recurso entrar na master. -->

O sistema vigia a força durante o ensaio e, se ela atingir o limite da célula
de carga definido nas Configurações, mostra um alerta de sobrecarga e envia
sozinho o pulso de parada para a máquina. Detalhes da configuração e do
funcionamento serão acrescentados aqui assim que o recurso for liberado.

O limite de força da tela do ensaio ([3.1](#31-preparando)) é diferente: ele é
enviado ao CLP como parâmetro do ensaio. O limite de sobrecarga protege a
célula de carga e vale para todos os ensaios.

---

## 7. Comparação de ensaios

1. Abra cada ensaio na lista e clique em **+ Comparar**. Ele passa a mostrar
   **✓ Comparar**.
2. Clique em **Comparar (n)** no topo da lista.
3. As curvas aparecem sobrepostas, cada uma com uma cor (σ × ε e força ×
   deslocamento na tração; σf × εf e força × deflexão na flexão), com a
   **tabela comparativa**, a **média**, o **desvio padrão** e o **CV (%)** de
   cada indicador.

Tração e flexão ficam em abas separadas. Para tirar um ensaio, clique no × da
etiqueta dele no topo. Também dá para comparar a partir da busca (botão que
compara todos os testes encontrados) ou da página do cliente (**Comparar
todos**).

Excluir um ensaio pede confirmação e não tem volta (a não ser por um backup).

---

## 8. Clientes, busca e dados do teste

### Clientes

Menu **Clientes**: cadastre nome/razão social (obrigatório), CNPJ/CPF,
contato, endereço, cidade/UF e observações. Ao abrir um cliente aparecem os
testes de tração, os testes de flexão e os relatórios dele, com o botão
**Comparar todos**.

Para um ensaio aparecer no cliente, escolha o cliente nos Dados do teste antes
de iniciar, ou corrija depois em **Dados do teste**.

### Busca

A caixa no topo da lista procura em clientes, amostras, nomes de ensaio e
números de relatório, sem diferenciar acentos. Se nada aparecer, tente menos
palavras.

### Corrigindo os dados de um ensaio

Abra o ensaio, clique em **Dados do teste** e ajuste nome, cliente, amostra,
norma, operador e observações. Os parâmetros da máquina usados no ensaio e os
dados medidos ficam registrados e **não mudam**.

---

## 9. Relatórios

1. Abra o ensaio e clique em **Gerar Relatório**. Os campos já vêm
   preenchidos com os dados do ensaio e do cliente.
2. Complete as seções:
   - **Cabeçalho / Empresa**: nome, endereço, contato e logo. O número do
     relatório é sequencial por ano (0001/2026, 0002/2026…).
   - **Dados do cliente / OS**: cliente cadastrado ou digitado, OS, data de
     recebimento, período de realização.
   - **Identificação da amostra**: ID interno, ID do cliente, foto.
   - **Objetivos**.
   - **Condições do ensaio**: temperatura e umidade, número de corpos de
     prova, célula de carga, L₀, velocidade, tipo de corpo de prova, distância
     entre garras (ou entre apoios, na flexão), extensômetro, largura e
     espessura, preparação, equipamentos e norma.
   - **Resultados**: gráfico tensão × deformação, gráfico força ×
     deslocamento (ou deflexão), tabela de dados brutos e gráficos
     comparativos com outros ensaios.
   - **Conclusão / Assinaturas**: local e data, nomes de quem assina e
     observações finais (uma por linha).
3. Desmarque o que não quiser incluir e clique em **Gerar Relatório**.

O relatório é baixado como arquivo HTML. Abra e use **Imprimir → Salvar como
PDF** para enviar ao cliente. Uma cópia fica em **Relatórios** (menu inferior),
com número, cliente e data, e pode ser aberta, baixada ou apagada pelos ícones à
direita. A assinatura é feita no papel ou no PDF; o sistema ainda não tem
assinatura eletrônica.

---

## 10. Instalação

### 10.1 No PC do cliente (versão compilada)

O cliente recebe só o programa compilado (`MaqTracao.exe`), sem código-fonte,
Python ou Node. O passo a passo completo, com geração do pacote, está em
[`instalacao/README.md`](../instalacao/README.md). Resumo:

1. **Gerar o pacote** (no PC de desenvolvimento): `git pull` na master,
   conferir `backend\config.json` (vira o padrão da primeira instalação) e
   rodar `instalacao\build_cliente_nuitka.bat` (recomendado; compila em código
   de máquina, 20 a 60 minutos na primeira vez) ou
   `instalacao\build_cliente.bat` (PyInstaller, mais rápido). Sai
   `build-cliente\MaqTracao-instalador.zip`.
2. **Instalar**: copiar o zip para o PC do cliente, extrair, clicar com o
   botão direito em `instalar.bat` → **Executar como administrador**.
3. Conferir em **Configurações** o IP da IHM e trocar a senha do técnico.
4. Apagar o zip e a pasta extraída. Reiniciar o PC uma vez e confirmar que a
   tela abre pelo atalho.

O que fica instalado:

```
C:\MaqTracao\
  MaqTracao.exe      programa (servidor + tela), sem janela
  config.json        configurações (editável)
  tracao.db          banco de ensaios, clientes e relatórios
  data\              pasta monitorada de CSVs (liberada a usuários comuns)
  logs\servidor.log  log do servidor
```

- Inicia com o Windows pela tarefa agendada **MaqTracao** (conta SYSTEM, antes
  do login) e é reiniciado se cair.
- O atalho **Máquina de Tração** abre `http://localhost:8000` no Edge em modo
  aplicativo.
- A pasta `C:\MaqTracao` só abre para administradores. A proteção só vale se o
  operador usar uma conta **padrão** do Windows.
- Atende só no próprio PC (`127.0.0.1`). Para abrir de outro PC da rede, use
  `"server_host": "0.0.0.0"` no `config.json` e libere a porta no firewall.
  `"server_port"` muda a porta (padrão 8000).

**Atualizar**: faça um backup ([12](#12-backup-e-restauração)), gere um zip novo
e rode `instalar.bat` de novo. Ele troca só o programa e mantém `config.json`,
`tracao.db`, `data\` e `logs\`.

**Desinstalar**: `desinstalar.bat` como administrador. Remove programa, tarefa e
atalho e mantém os dados.

### 10.2 Ambiente de desenvolvimento

Requisitos: Python 3.11+, Node.js 20+ e npm 9+.

```bat
setup.bat    :: cria o venv, instala dependências, gera data\H0001.csv de exemplo
start.bat    :: sobe o backend (porta 8000) e o frontend (porta 5173)
```

Manual:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
cd frontend && npm run dev
```

Testes: `pytest backend/tests/ -v`. A documentação interativa da API fica em
`http://localhost:8000/docs` (desligada na versão do cliente).

---

## 11. Configurações

### 11.1 Acesso

A tela **Configurações** pede a **senha do técnico** (padrão `tracao2026`).
Sem ela não dá para salvar configurações nem testar registradores, nem pela
tela nem pela API. Troque a senha em **Configurações → Sobre** logo depois de
instalar. Uma alteração errada aqui faz o sistema perder contato com a máquina;
no dia a dia, o operador não precisa mexer em nada.

Depois de alterar, clique em **Salvar e Aplicar**. As mudanças valem na hora,
sem reiniciar.

### 11.2 Geral

| Campo | Para que serve |
|---|---|
| Diretório monitorado | Pasta onde o sistema procura arquivos `.csv` no formato HISTORY V1.0 exportados pela IHM. |
| Monitoramento automático | Importa novos CSVs em segundo plano. |
| Intervalo de verificação | De 1 a 60 segundos. |
| Máquina com flexão | Desligue em máquinas sem o dispositivo de flexão. |
| Modo simulador | Gera força, deslocamento e ruptura plausíveis sem máquina, para treinar ou testar o software. Não conecta no CLP. **Desligue antes de ensaiar de verdade.** |

### 11.3 Controle (CLP)

| Campo | Para que serve |
|---|---|
| IP de conexão | IP da IHM (ou do CLP) consultado via Modbus TCP. Padrão 192.168.11.10. |
| Porta Modbus | Normalmente 502. |
| Timeout (s) | Tempo de espera por resposta. |
| Família do CLP | Converte D/M/X em endereço Modbus: **Delta DVP** (D600 → 4696), **Sem offset** (D600 → 600; use quando os endereços já são os da tabela da IHM) ou **Delta AS**. |
| Pulso comando (ms) | Duração dos pulsos de iniciar, parar, sentido, zerar e tara (padrão 300 ms). |
| Unidade da força no CLP | **kgf**: a força lida é multiplicada por 9,80665 para virar N e o limite de força é enviado em kgf. **N**: sem conversão. Os cálculos usam sempre N. |
| Área da seção padrão / L₀ padrão | Valores usados quando o ensaio não informa outros. |

**Registradores de controle**: tabela com uma linha por sinal. Colunas:

| Coluna | Conteúdo |
|---|---|
| Disp./End. | Endereço Modbus numérico (0-based) ou dispositivo Delta (`D412`, `M5`, `X0`), convertido pela família. |
| CLP | Só referência: registrador de origem no CLP. |
| Role | Papel do sinal para o programa (lista em [14.3](#143-roles)). |
| Nome | Chave interna. |
| Tipo | `coil`, `input`, `uint16`, `decimal`, `int32`, `decimal32`, `float32`. |
| Escala | Fator multiplicado na leitura (e dividido na escrita). |
| Ordem | Ordem das palavras em tipos de 32 bits: `big` ou `little`. Os D float32 do DVP via IHM usam `little`. |

**Flexão**: usa os mesmos registradores da tração. Marque **Separar** só nos
sinais que são diferentes na flexão e informe o endereço próprio.

**Diagnóstico de registrador**: lê ou escreve um único endereço e mostra o
valor cru e o interpretado (inclusive como float). Use para confirmar um
endereço antes de salvá-lo. Cuidado ao **escrever** em sinais de comando com a
máquina ligada.

### 11.4 Backup

Ver [12](#12-backup-e-restauração).

### 11.5 Sobre

Versão do software e troca da senha das Configurações.

---

## 12. Backup e restauração

O sistema grava um `.zip` com o banco (`tracao.db`) e o `config.json` numa
pasta que o Google Drive, OneDrive ou Dropbox já sincroniza. Ele não guarda
senha de nuvem e faz a cópia mesmo sem internet; o app da nuvem sobe quando a
conexão voltar.

Em **Configurações → Backup**:

1. Ligue **Fazer backup automaticamente**.
2. Informe a **Pasta do backup** (ex.: `C:\Users\<usuário>\OneDrive\Backup Tração`).
3. Escolha o **Intervalo (horas)** (padrão 24) e quantos manter (**Manter os
   últimos**, padrão 30; os mais antigos são apagados).
4. Clique em **Salvar e Aplicar** e depois em **Fazer backup agora** para
   testar. A tela mostra o último e o próximo backup e a lista de arquivos na
   pasta.

Os arquivos se chamam `MaqTracao-backup-AAAAMMDD-HHMMSS.zip`. A cópia do banco
é consistente mesmo com o programa gravando.

**Restaurar**: feche o programa (Agendador de Tarefas → MaqTracao → Finalizar),
descompacte o `.zip` e troque o `tracao.db` da instalação (`C:\MaqTracao`) pelo
do backup. Se quiser, troque também o `config.json`. Inicie de novo a tarefa ou
reinicie o PC.

Faça sempre um backup antes de atualizar o programa.

---

## 13. Solução de problemas

| Sintoma | O que fazer |
|---|---|
| Tela abre em branco | O sistema ainda está iniciando. Aguarde e aperte F5. Se persistir, veja `C:\MaqTracao\logs\servidor.log` (como administrador) ou Agendador de Tarefas → MaqTracao → Executar. |
| Indicador vermelho (CLP desconectado) | IHM ligada? Cabo de rede conectado nas duas pontas, com luz na porta? O PC está na mesma faixa de rede da IHM (ex.: 192.168.11.x)? O motivo aparece no indicador: "IP não configurado", "sem resposta Modbus" ou "registrador de força sem leitura" (endereço da força errado). |
| "IP do CLP não configurado" / "Registrador 'iniciar' não configurado" | Preencha em Configurações → Controle (CLP). |
| "CLP inacessível em IP:porta" | Mesma checagem do indicador vermelho. Teste com `ping 192.168.11.10`. |
| Força sempre zero | Confira a célula de carga e o cabo. Faça a Tara sem carga. Técnico: confira o endereço e o tipo de `forca_atual` com o Diagnóstico de registrador. |
| Força 9,8 vezes maior ou menor | Unidade da força no CLP trocada (kgf × N). |
| Valor absurdo (ex.: 1e+38) | Ordem das palavras (`big`/`little`) ou tipo errado no registrador. |
| Deslocamento não começa em zero | Clique em Zerar deslocamento antes de iniciar. |
| Ensaio não aparece na lista | Só é gravado com 10 leituras de força ou mais, ao romper, ao Parar ou ao fechar a tela. Se o programa foi desligado no meio, repita o ensaio. |
| Ensaio sem ruptura | A força não caiu de forma brusca: o ensaio foi parado antes de romper ou atingiu o curso programado. |
| Valores estranhos no resultado | Confira área da seção e L₀ (ou b, h e L na flexão) em Dados do teste. |
| R² baixo ou "trecho elástico não identificado" | Folga nas garras ou acomodação longa. Aperte bem o corpo de prova e faça a Tara. |
| Simulador ligado sem querer | O indicador mostra "simulador". Desligue em Configurações → Geral. |
| Porta 8000 ocupada | Mude `"server_port"` no `config.json` e o endereço do atalho. |
| Backup falha | A pasta existe e é gravável? Salve a pasta nova antes de testar. |

Ferramentas de diagnóstico (no ambiente de desenvolvimento, com o venv ativo):

- `python varredura_ihm.py [--ip IP] [--hr 40000-40200] [--coils 3900-4200] [--csv arq.csv]`:
  varre a memória Modbus da IHM **só lendo** e lista o que tem valor. Anote o
  valor da tela da IHM, rode, mexa na máquina e rode de novo: o endereço que
  mudou junto é o certo.
- `python modbus_test.py 40000 40099 --32`: lê endereços e faixas, com
  decodificação de 32 bits e float.
- `python test_bit.py --scan`: mostra quais coils e registradores mudam
  (útil para achar bits de início, parada e ruptura).

---

## 14. Referência técnica

### 14.1 Arquivos e pastas

| Caminho | Conteúdo |
|---|---|
| `backend/main.py` | Servidor FastAPI e todos os endpoints. |
| `backend/modbus_client.py` | Comunicação Modbus TCP e conversão de dispositivos Delta. |
| `backend/acquisition.py`, `backend/flexao/` | Montagem e gravação dos ensaios. |
| `backend/parser.py` | Leitura dos CSV da IHM e detecção dos estágios. |
| `backend/calculator.py`, `backend/flexao/calculator.py` | Cálculos de tração e flexão. |
| `backend/qualidade.py` | Verificações de qualidade dos dados. |
| `backend/normas.py` | Normas e parâmetros sugeridos. |
| `backend/report.py` | Relatório HTML. |
| `backend/backup.py` | Backup em pasta sincronizada. |
| `backend/acesso.py` | Senha das Configurações. |
| `backend/simulator.py` | Modo simulador. |
| `backend/config.json` | Configuração (na instalação: `C:\MaqTracao\config.json`). |
| `tracao.db` | Banco SQLite: ensaios, ensaios de flexão, clientes, relatórios, parâmetros da IHM. |
| `frontend/` | Tela (React + TypeScript + Vite + Tailwind). |
| `instalacao/` | Scripts de build e instalação do cliente. |

### 14.2 Chaves do config.json

| Chave | Padrão | Descrição |
|---|---|---|
| `ihm_ip`, `ihm_port`, `ihm_timeout` | — , 502, 3 | IHM para leitura de parâmetros e CSV/FTP. |
| `clp_ip`, `clp_port`, `clp_timeout` | vazio, 502, 3 | Conexão de controle. Vazio usa os da IHM. |
| `plc_family` | `dvp` | `dvp`, `direto` ou `as`. |
| `forca_clp_kgf` | `true` | Força do CLP em kgf. |
| `control_registers` | | Registradores de controle da tração. |
| `flexao_registers`, `flexao_separados` | | Registradores próprios da flexão e quais roles usam o endereço próprio. |
| `flexao_habilitada` | `true` | Máquina com flexão. |
| `control_pulse_ms` | 300 | Duração dos pulsos. |
| `realtime_interval_ms` | 100 | Intervalo entre leituras durante o ensaio (mínimo 50). |
| `area_seccao_mm2`, `comprimento_inicial_mm` | | Últimos valores de área e L₀. |
| `flexao_largura_mm`, `flexao_espessura_mm`, `flexao_span_mm`, `flexao_norma` | | Últimos valores da flexão. |
| `watch_directory`, `auto_load`, `refresh_interval_s` | | Pasta monitorada de CSV. |
| `ihm_registers`, `realtime_*_name` | | Leitura de parâmetros da IHM e modo de aquisição antigo por CSV. |
| `ftp_port`, `ftp_user`, `ftp_password`, `ftp_remote_dir`, `ftp_remote_filename` | | Baixar o CSV do histórico pela FTP da IHM. |
| `backup_ativo`, `backup_dir`, `backup_intervalo_h`, `backup_manter` | false, vazio, 24, 30 | Backup. |
| `simulator_enabled` | `false` | Modo simulador. |
| `server_host`, `server_port` | 127.0.0.1, 8000 | Só na versão do cliente. |
| `proximo_ensaio`, `proximo_ensaio_flexao` | | Cadastro do próximo ensaio (preenchido pela tela). |
| `senha_config` | | Hash da senha das Configurações (gravado pela tela; apagar a chave volta à senha padrão). |

### 14.3 Roles

| Role | Tipo | Uso |
|---|---|---|
| `iniciar`, `parar` | coil, escrita | Pulso de início e de parada. |
| `sentido_cima`, `sentido_baixo` | coil, escrita | Pulso de sentido antes do início. |
| `zerar_deslocamento` | coil, escrita | Zera o deslocamento. |
| `zerar_celula` | coil, escrita | Tara (também para o ensaio). |
| `velocidade`, `deslocamento_programado`, `limite_forca` | registrador, escrita | Parâmetros do ensaio. |
| `forca_atual`, `deslocamento_atual` | registrador, leitura | Aquisição. `forca_atual` também prova a conexão. |
| `forca_maxima`, `tensao_maxima`, `deslocamento_maximo` | registrador, leitura | Valores calculados pelo CLP, mostrados na tela. |
| `material_integro_bit`, `ruptura_bit` | coil, leitura | Estado do material; a borda de subida da ruptura grava o ensaio. |
| `fim_ensaio_bit` | coil, leitura | Fim do ensaio de flexão. |
| `emergencia`, `limite_superior`, `limite_inferior` | coil/input, leitura | Indicadores na tela. |

### 14.4 Mapa de registradores IHM → CLP

A tabela de troca da IHM (DOPSoft, numeração 1-based; no software use o
número da tabela − 1):

| IHM | CLP |
|---|---|
| Registers 40000 (10) | D407… (velocidade D408, deslocamento programado D412) |
| Registers 40010 (10) | D2012… (força máxima) |
| Registers 40020 (10) | D2002… (limite de força D2006) |
| Registers 40030 (10) | D2022… |
| Registers 40040 (10) | D600… (deslocamento atual) |
| Registers 40050 (10) | D92… |
| Coils 4000 (10) | M5… (sentido cima M5, baixo M6, parar M7, iniciar M9) |
| Coils 4010 (10) | M30… (material íntegro M30, ruptura M31) |
| Coils 4020 (10) | M100… (zerar deslocamento M100, tara M101) |

Linhas sugeridas que ainda precisam ser criadas na IHM para os sinais opcionais:
Registers 40060 → D3004 (tensão máxima), Registers 40070 → D610 (deslocamento
máximo), Coils 4030 → X0 tamanho 3 (emergência, limite inferior e superior).
Sem elas esses indicadores ficam vazios, e o ensaio funciona normalmente.

Conferir sempre com o projeto do DOPSoft da máquina: o mapa pode mudar de uma
máquina para outra.

Conversão da família **Delta DVP** (quando o endereço é digitado como
dispositivo): D0–D4095 → 0x1000 + n; D4096+ → 0x9000 + (n − 4096); M0–M1535 →
0x0800 + n; M1536+ → 0xB000 + (n − 1536); X → 0x0400 + octal; Y → 0x0500 +
octal. D é holding register, M e Y são coils, X é entrada discreta.

### 14.5 Cálculos

Tração:

- σ = F ÷ A (MPa); ε = ΔL ÷ L₀; A% = (Lf − L₀) ÷ L₀ × 100.
- Trecho elástico: maior trecho em que a rigidez fica acima de 80 % da máxima,
  encurtado até a reta F × d ter R² ≥ 0,99 (mínimo 5 pontos). E é a inclinação
  da regressão σ × ε nesse trecho.
- Rp0,2: cruzamento da curva com a reta elástica deslocada de 0,002.
- Energia: ∫ F dd até a ruptura (J).
- Ruptura: queda ≥ 25 % de Fmáx em até 2 amostras; ou queda gradual abaixo de
  10 % de Fmáx.

Flexão (3 pontos):

- σf = 3·F·L ÷ (2·b·h²); εf = 6·s·h ÷ L².
- Módulo pela regressão no trecho elástico e módulo cordal entre εf1 e εf2 da
  norma.
- Tensão de escoamento de flexão: queda do módulo local maior que 10 %.

### 14.6 Normas cadastradas

| Norma | Tipo | Material | Corpo de prova | Velocidade (mm/min) | L₀ / vão (mm) |
|---|---|---|---|---|---|
| ISO 527-2 | Tração | Plásticos | Tipo 1A (170 × 10 × 4) | 50 | 75 |
| ASTM D638 | Tração | Plásticos | Tipo I (165 × 13 × 3,2) | 5 | 50 |
| ABNT NBR ISO 6892-1 | Tração | Metais | Proporcional (L₀ = 5,65·√S₀) | por taxa | — |
| ASTM E8/E8M | Tração | Metais | Chapa 12,5 mm | por taxa | 50 |
| ASTM D3039 | Tração | Compósitos | 250 × 25 × 2,5 | 2 | — |
| ISO 37 | Tração | Borrachas | Gravata tipo 1 | 500 | 25 |
| ASTM D412 | Tração | Borrachas | Matriz C | 500 | 25 |
| ISO 178 | Flexão | Plásticos | 80 × 10 × 4 | 2 | 64 |
| ASTM D790 | Flexão | Plásticos | 127 × 12,7 × 3,2 | 1,4 | 51,2 |

### 14.7 Importação por CSV

Além da aquisição direta, o sistema importa os arquivos de histórico da IHM
(`HISTORY V1.0`, UTF-16 com BOM, separado por TAB, 1 amostra por segundo, com as
colunas TIME, DATA, Tensao_Pa, Modulo_Elast, Tensao_Max, Deform_Along,
Alonga_Ruptura, Deslocamento, Forca_N, Checksum). Formas de importar:

- colocar o arquivo no **diretório monitorado** (importa sozinho);
- baixar pela **FTP da IHM** (`POST /api/ftp/fetch_csv`, usando as chaves
  `ftp_*`);
- forçar nova varredura (`POST /api/scan`).

### 14.8 API

O servidor responde em `http://localhost:8000`. Principais rotas:

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | Servidor no ar. |
| GET | `/api/clp/conexao` | Estado da conexão com a IHM/CLP. |
| GET | `/api/ensaios` · `/api/ensaios/{id}` | Lista e detalhe de ensaios de tração (`?cliente_id=`). |
| PATCH | `/api/ensaios/{id}` | Altera só o cadastro (cliente, amostra…). |
| GET | `/api/ensaios/{id}/kpis` · `/curvas` · `/qualidade` · `/parametros_ihm` | Resultados. |
| DELETE | `/api/ensaios/{id}` | Exclui o ensaio. |
| POST | `/api/ensaios/{id}/reimport` · `/api/reimport-all` | Reprocessa a partir do CSV. |
| GET | `/api/flexao/ensaios` e rotas equivalentes | Ensaios de flexão. |
| POST | `/api/control/start` · `/stop` · `/zerar-deslocamento` · `/zerar-celula` · `/setpoints` | Comandos de tração. |
| GET | `/api/control/status` · `/api/control/stream` | Leitura instantânea e fluxo ao vivo (SSE) que grava o ensaio. |
| POST/GET | `/api/flexao/control/...` | Comandos e fluxo da flexão. |
| POST | `/api/relatorio` | Gera e salva o relatório (`tipo`: tração ou flexão). |
| GET | `/api/ensaios/{id}/campos-relatorio` | Campos pré-preenchidos. |
| GET/DELETE | `/api/relatorios` · `/api/relatorios/{id}/html` | Relatórios salvos. |
| GET/POST/PUT/DELETE | `/api/clientes` | Clientes. |
| GET | `/api/busca?q=` | Busca. |
| GET | `/api/normas?tipo=` | Normas. |
| GET/POST | `/api/backup` · `/api/backup/agora` | Estado do backup e backup imediato. |
| POST | `/api/config/login` · `/logout` · `/senha` | Senha das Configurações (devolve o token do cabeçalho `X-Config-Token`). |
| GET/PUT | `/api/config` | Ler e salvar configurações (PUT exige token). |
| POST | `/api/control/probe` | Diagnóstico de registrador (exige token). |
| POST | `/api/scan` · `/api/ftp/fetch_csv` | Importação de CSV. |

A API não tem autenticação além da senha das Configurações e só atende no
próprio PC por padrão. Não exponha a porta para fora da rede local.

---

Dúvidas ou suporte: equipe da Automatic · Automação Industrial.

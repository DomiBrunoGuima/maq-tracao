<div class="capa">
<p class="capa-sup">DOCUMENTO DE DESIGN DE SOFTWARE (SDD)</p>
<h1 class="capa-titulo">SISTEMA DE ENSAIOS DE TRAÇÃO E FLEXÃO</h1>
<div class="capa-barra"></div>
<p class="capa-sup2">VERSÃO</p>
<p class="capa-projeto">Como entregue (as-built)</p>
<table class="capa-tabela">
<tr><th>Documento nº</th><td>SDD 01/26 — Revisão 00</td></tr>
<tr><th>Data de emissão</th><td>09/11/2026</td></tr>
<tr><th>Sistema</th><td>Software de coleta, controle e parametrização da máquina de ensaios (MaqTracao)</td></tr>
<tr><th>Equipamento</th><td>Máquina de tração com CLP Delta DVP-20SX2 e IHM Delta DOP</td></tr>
<tr><th>Cliente</th><td>[Razão social do cliente]</td></tr>
<tr><th>Versão do software</th><td>Branch master, commit fc6ba53 (06/11/2026)</td></tr>
<tr><th>Repositório</th><td>github.com/DomiBrunoGuima/maq-tracao</td></tr>
<tr><th>Documentos relacionados</th><td>Manual completo do sistema (docs/MANUAL.md e PDF)</td></tr>
<tr><th>Elaborado por</th><td>AUTOMATIC</td></tr>
</table>
<p class="capa-slogan">Facilitando e evoluindo</p>
<p class="capa-aviso">Este documento contém informações técnicas de propriedade da AUTOMATIC, destinadas exclusivamente ao cliente indicado. Sua reprodução ou divulgação a terceiros depende de autorização prévia.</p>
</div>

# CONTROLE DE REVISÕES

| Rev. | Data | Descrição | Elaborado |
|---|---|---|---|
| 00 | 09/11/2026 | Emissão inicial, descrevendo o sistema como entregue (instalação de 21/10/2026 e atualizações até o commit fc6ba53). | AUTOMATIC |

## Convenção de status das informações

Este documento descreve o sistema **como foi construído e entregue**. Quando
uma informação depende da máquina física (endereços, tipos de dado, unidades),
ela vem marcada com um dos selos abaixo, para deixar claro o que foi visto
funcionando e o que ainda precisa de conferência.

| Selo | Significado |
|---|---|
| <span class="selo ok">AJUSTADO EM CAMPO</span> | Valor alterado no `config.json` durante a instalação na máquina (21/10/2026). É a melhor evidência disponível de que foi testado no equipamento. |
| <span class="selo proj">DO PROJETO</span> | Valor tirado do projeto DOPSoft (tabela de troca da IHM) e mantido sem alteração na instalação. Funciona como projetado, mas não há registro formal de teste sinal a sinal. |
| <span class="selo nc">NÃO CONFIRMADO</span> | Depende de linha que não existia na tabela da IHM, ou há divergência entre o projeto e o `config.json`. Precisa ser conferido na máquina antes de ser usado como referência. |

Não existe, no repositório, uma folha de comissionamento assinada sinal a
sinal. O [Anexo A](#anexo-a-roteiro-de-verificação-em-campo) traz o roteiro para
fazer essa conferência e fechar as pendências.

# 1. INTRODUÇÃO

## 1.1 Finalidade

Registrar a arquitetura, as interfaces, o modelo de dados e as decisões de
projeto do software que comanda a máquina de ensaios, coleta força e
deslocamento, calcula os resultados e emite os relatórios. O documento serve
de base para manutenção, auditoria técnica, treinamento da equipe de suporte e
futuras evoluções.

## 1.2 Escopo

Cobre o software instalado no computador ao lado da máquina (servidor local e
tela no navegador), a comunicação com a IHM Delta, o banco de dados local, o
controle de acesso, o backup, os relatórios e o processo de implantação.

Não cobre o programa do CLP (ladder no ISPSoft) nem o projeto de telas da IHM
(DOPSoft), exceto no que eles expõem para o software pela rede.

## 1.3 Público

Equipe técnica da AUTOMATIC, técnico de manutenção do cliente e quem for dar
continuidade ao desenvolvimento. O operador da máquina deve usar o Manual.

## 1.4 Termos e siglas

| Termo | Significado |
|---|---|
| CLP | Controlador lógico programável (Delta DVP-20SX2). |
| IHM | Interface homem-máquina (Delta DOP), tela da máquina e ponte de rede. |
| Modbus TCP | Protocolo usado entre o computador e a IHM (porta 502). |
| Coil | Bit Modbus de leitura e escrita (ex.: comando de iniciar). |
| Holding register | Palavra Modbus de 16 bits; valores float32 ocupam duas. |
| Role | Papel de um registrador para o software (ex.: `forca_atual`, `iniciar`). |
| SSE | Server-Sent Events: fluxo contínuo de dados do servidor para a tela. |
| L₀ | Comprimento inicial de referência do corpo de prova (mm). |
| Fmáx | Força máxima registrada no ensaio. |
| Mestre | Acesso administrador fixo do sistema. |

# 2. VISÃO GERAL DO SISTEMA

## 2.1 Funções

- **Comandar** a máquina: iniciar, parar, sentido (subir/descer), zerar
  deslocamento, tara e envio de velocidade, curso e limite de força.
- **Coletar** força e deslocamento a cada 100 ms durante o ensaio e desenhar
  as curvas ao vivo.
- **Calcular** os resultados de tração (tensão máxima, módulo com R², Rp0,2,
  alongamentos, energia) e de flexão a 3 pontos (resistência, módulo, deflexão).
- **Documentar**: gravar cada ensaio com cliente, amostra, norma e operador,
  avaliar a qualidade dos dados e gerar o relatório técnico numerado.
- **Proteger**: alerta de sobrecarga da célula de carga com pulso de parada.
- **Administrar**: login por usuário, gestão de usuários, registro de
  atividades e backup automático.

## 2.2 Contexto

<figure class="diagrama">
<svg viewBox="0 0 640 250" xmlns="http://www.w3.org/2000/svg" font-family="Arial, Liberation Sans, sans-serif" font-size="11">
  <defs><marker id="seta" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>
  <rect x="10" y="20" width="150" height="80" rx="4" fill="#f2f2f2" stroke="#999"/>
  <text x="85" y="45" text-anchor="middle" font-weight="bold">Máquina</text>
  <text x="85" y="63" text-anchor="middle">motor, garras,</text>
  <text x="85" y="78" text-anchor="middle">célula de carga, encoder</text>
  <rect x="10" y="150" width="150" height="80" rx="4" fill="#f2f2f2" stroke="#999"/>
  <text x="85" y="178" text-anchor="middle" font-weight="bold">CLP Delta DVP-20SX2</text>
  <text x="85" y="196" text-anchor="middle">lógica do ensaio</text>
  <text x="85" y="211" text-anchor="middle">registradores D / M / X</text>
  <rect x="245" y="150" width="150" height="80" rx="4" fill="#fff8e0" stroke="#f9bd00" stroke-width="2"/>
  <text x="320" y="178" text-anchor="middle" font-weight="bold">IHM Delta DOP</text>
  <text x="320" y="196" text-anchor="middle">tela da máquina</text>
  <text x="320" y="211" text-anchor="middle">escravo Modbus TCP</text>
  <rect x="470" y="20" width="160" height="210" rx="4" fill="#1d2021" stroke="#1d2021"/>
  <text x="550" y="45" text-anchor="middle" font-weight="bold" fill="#fff">Computador</text>
  <rect x="485" y="60" width="130" height="50" rx="3" fill="#fff"/>
  <text x="550" y="80" text-anchor="middle" font-weight="bold">Tela (navegador)</text>
  <text x="550" y="96" text-anchor="middle">React, Edge modo app</text>
  <rect x="485" y="125" width="130" height="50" rx="3" fill="#fff"/>
  <text x="550" y="145" text-anchor="middle" font-weight="bold">MaqTracao.exe</text>
  <text x="550" y="161" text-anchor="middle">FastAPI, porta 8000</text>
  <rect x="485" y="190" width="130" height="30" rx="3" fill="#f9bd00"/>
  <text x="550" y="209" text-anchor="middle" font-weight="bold">tracao.db (SQLite)</text>
  <line x1="85" y1="100" x2="85" y2="148" stroke="#333" marker-end="url(#seta)"/>
  <line x1="160" y1="190" x2="243" y2="190" stroke="#333" marker-end="url(#seta)"/>
  <text x="200" y="182" text-anchor="middle">Link1</text>
  <line x1="395" y1="165" x2="483" y2="165" stroke="#333" marker-end="url(#seta)"/>
  <text x="438" y="157" text-anchor="middle" font-size="9">Ethernet</text>
  <text x="438" y="180" text-anchor="middle" font-size="9">Modbus TCP</text>
  <text x="438" y="191" text-anchor="middle" font-size="9">porta 502</text>
  <line x1="550" y1="110" x2="550" y2="123" stroke="#f9bd00" stroke-width="1.5"/>
  <line x1="550" y1="175" x2="550" y2="188" stroke="#f9bd00" stroke-width="1.5"/>
  <rect x="470" y="235" width="0" height="0"/>
  <text x="558" y="120" text-anchor="start" fill="#fff" font-size="8">HTTP</text>
</svg>
<figcaption>Figura 1. O computador não fala direto com o CLP: lê e escreve na memória Modbus da IHM, que repassa para o CLP.</figcaption>
</figure>

O computador conversa só com a **IHM**. A IHM republica, na sua memória
Modbus, os registradores do CLP listados na tabela de troca do projeto DOPSoft.
Um sinal do CLP que não estiver nessa tabela não é visível para o software.

Tudo roda e fica gravado no próprio computador. O sistema não depende de
internet; a única saída externa é a pasta de backup, que um aplicativo de nuvem
(OneDrive, Google Drive ou Dropbox) sincroniza por conta própria.

## 2.3 Tecnologias

| Camada | Tecnologia |
|---|---|
| Servidor | Python 3.11+, FastAPI, Uvicorn |
| Comunicação | pymodbus 3.6+ (cliente Modbus TCP) |
| Cálculo | pandas, numpy, scipy |
| Banco | SQLite via SQLAlchemy 2 |
| Gráficos do relatório | matplotlib (PNG embutido no HTML) |
| Monitoramento de pasta | watchdog |
| Tela | React 18, TypeScript, Vite 5, Tailwind CSS 3, Recharts, TanStack Query |
| Empacotamento | Nuitka (recomendado) ou PyInstaller, gerando `MaqTracao.exe` |

# 3. ARQUITETURA

## 3.1 Visão em camadas

O sistema é um único processo servidor (`MaqTracao.exe`) que atende a API e
entrega a tela já compilada (`frontend/dist`) na mesma porta. A tela roda no
navegador do próprio PC e fala com o servidor só por HTTP.

| Camada | Responsabilidade | Onde está |
|---|---|---|
| Apresentação | Telas de Controle, Flexão, Resultados, Comparação, Clientes, Relatórios, Configurações e Usuários | `frontend/src/components/` |
| API | Rotas REST e fluxos SSE, autenticação, auditoria | `backend/main.py` |
| Domínio | Aquisição, cálculos, qualidade, normas, relatórios, sobrecarga | `backend/*.py`, `backend/flexao/` |
| Integração | Modbus TCP, conversão de dispositivos Delta, FTP da IHM, pasta de CSV | `modbus_client.py`, `ftp_client.py`, `watcher.py` |
| Persistência | SQLite, migração de colunas, `config.json` | `database.py`, `main.py` |

## 3.2 Módulos do servidor

| Módulo | Função |
|---|---|
| `main.py` | Aplicação FastAPI, estado de configuração, todas as rotas, fluxos de aquisição de tração e flexão. |
| `modbus_client.py` | Leitura e escrita Modbus (coil, uint16, int32, float32, decimal), ordem das palavras, conversão D/M/X → endereço, diagnóstico de registrador. |
| `acquisition.py` | Monta o DataFrame do ensaio de tração a partir das amostras e grava no banco. |
| `flexao/` | Equivalente para flexão a 3 pontos: aquisição, cálculos e leitura de CSV. |
| `parser.py` | Leitura do CSV `HISTORY V1.0` da IHM e detecção dos estágios da curva. |
| `calculator.py` | Resultados de tração (KPIs) e dados das curvas. |
| `qualidade.py` | Verificações de qualidade dos dados do ensaio. |
| `normas.py` | Normas cadastradas e parâmetros sugeridos. |
| `report.py` | Relatório técnico em HTML com gráficos. |
| `sobrecarga.py` | Monitor de sobrecarga da célula de carga. |
| `usuarios.py` | Usuários, mestre, sessões, senhas e auditoria. |
| `acesso.py` | Senha do técnico para as Configurações. |
| `backup.py` | Backup periódico em pasta sincronizada. |
| `simulator.py` | Simula IHM e CLP para treino e testes sem máquina. |
| `watcher.py`, `ftp_client.py` | Importação de CSV pela pasta monitorada e pela FTP da IHM. |

## 3.3 Execução concorrente

| Atividade | Como roda |
|---|---|
| Requisições da tela | Uvicorn (assíncrono); chamadas Modbus bloqueantes vão para o executor de threads. |
| Aquisição ao vivo | Um fluxo SSE por tela aberta (`/api/control/stream` ou o de flexão), com leitura a cada `realtime_interval_ms` (padrão 100 ms, mínimo 50 ms). |
| Pasta monitorada | Thread do watchdog, iniciada na subida do servidor. |
| Backup | Thread própria que confere a cada 60 s se o intervalo venceu. |
| Sobrecarga | Sem thread própria: cada leitura de força (status e fluxos) passa pelo monitor. |

## 3.4 Fluxo de um ensaio de tração

1. O operador preenche o cadastro (cliente, amostra, norma, operador) e o
   setup (sentido, velocidade, curso, limite de força, área e L₀) na tela de
   Controle.
2. **Iniciar** (`POST /api/control/start`): o servidor recusa se houver
   alarme de sobrecarga ativo, escreve velocidade, curso e limite de força,
   guarda o cadastro em `proximo_ensaio` no `config.json`, dá o pulso de
   sentido e o pulso de **iniciar** (300 ms) e registra `ensaio_iniciado` na
   auditoria.
3. A tela abre o fluxo `/api/control/stream`. A cada leitura o servidor
   acumula força e deslocamento, envia o ponto para a tela e passa a força
   pelo monitor de sobrecarga.
4. O ensaio é gravado quando acontece o primeiro destes eventos: borda de
   subida do bit de **ruptura**; **sobrecarga** (com pulso de parada);
   operador clica **Parar** ou fecha a tela.
5. Só é gravado com 10 leituras de força ou mais. A gravação calcula
   tensão, deformação, estágios e KPIs, salva tudo em `ensaios` e aplica o
   cadastro de `proximo_ensaio`.
6. A tela recebe o número do ensaio gravado e abre os resultados.

A flexão segue o mesmo fluxo com os registradores da flexão
(`/api/flexao/control/...`), o bit `fim_ensaio_bit` no lugar da ruptura e a
geometria b, h e L no lugar de área e L₀. A deflexão vem negativa do CLP (a
travessa desce) e o software inverte o sinal da série predominantemente
negativa.

## 3.5 Caminho alternativo por CSV

Antes da aquisição direta, a IHM gravava um histórico em CSV (`HISTORY V1.0`,
UTF-16, TAB, 1 amostra por segundo). Esse caminho continua disponível: o
arquivo pode ser colocado na pasta monitorada, baixado pela FTP da IHM
(`/HMI/HMI-000/History/CSV/H0001.csv`) ou reprocessado. Na operação normal da
máquina entregue, o caminho usado é a aquisição direta da seção 3.4.

# 4. COMUNICAÇÃO COM A IHM DELTA

## 4.1 Parâmetros de rede

| Item | Valor | Status |
|---|---|---|
| Protocolo | Modbus TCP, o computador é mestre e a IHM é escrava | <span class="selo ok">AJUSTADO EM CAMPO</span> |
| Porta | 502 | <span class="selo ok">AJUSTADO EM CAMPO</span> |
| Timeout | 3 s (2 s no teste de conexão) | <span class="selo proj">DO PROJETO</span> |
| `ihm_ip` | 192.168.11.10 (IP padrão de fábrica da IHM) | <span class="selo proj">DO PROJETO</span> |
| `clp_ip` | 192.168.15.50 | <span class="selo ok">AJUSTADO EM CAMPO</span> |
| Família de endereços | `dvp` | <span class="selo proj">DO PROJETO</span> |
| Pulso de comando | 300 ms | <span class="selo proj">DO PROJETO</span> |
| Unidade da força no CLP | kgf (`forca_clp_kgf` = true, padrão) | <span class="selo nc">NÃO CONFIRMADO</span> |

**Qual IP vale.** O software usa `clp_ip` para controle e aquisição; só quando
ele está vazio usa `ihm_ip`. O `config.json` gravado no dia da instalação tem
`clp_ip` = 192.168.15.50, portanto é nesse endereço que o software procura a
IHM. O 192.168.11.10 continua sendo usado para a leitura de parâmetros e a FTP
do caminho por CSV. O arquivo que vale é o da máquina
(`C:\MaqTracao\config.json`), que pode ter sido alterado depois pela tela de
Configurações.

**Unidade da força.** O software assume força em kgf vinda do CLP, multiplica
por 9,80665 para trabalhar em N e envia o limite de força em kgf. Se a força
aparecer 9,8 vezes maior ou menor que a da tela da IHM, a unidade está trocada.

## 4.2 Endereçamento

- A tabela de troca no DOPSoft é numerada a partir de 1 (ex.: Registers 40050).
  O software usa endereço a partir de 0: **endereço no software = número da
  tabela − 1**.
- Cada linha da tabela liga um bloco da memória da IHM a um bloco do CLP
  (ex.: Registers 40040, tamanho 10 → D600 a D609).
- Os valores D do CLP são float32 e ocupam dois registradores. Pela IHM, a
  ordem das palavras é `little` (palavra baixa primeiro).
- Um registrador também pode ser digitado como dispositivo Delta (`D412`,
  `M5`, `X0`). Com a família **DVP**, o software converte: D0–D4095 → 0x1000 + n;
  M0–M1535 → 0x0800 + n; X → 0x0400 + octal; Y → 0x0500 + octal. Essa conversão
  vale para falar **direto** com o CLP; para falar com a IHM, os endereços são
  os da tabela de troca (como estão no `config.json` entregue).

## 4.3 Tabela de troca da IHM (projeto DOPSoft)

| Linha da IHM (1-based) | Tamanho | Bloco do CLP | Status |
|---|---|---|---|
| Registers 40000 | 10 | D407… (velocidade D408, curso D412) | <span class="selo proj">DO PROJETO</span> |
| Registers 40010 | 10 | D2012… (força máxima) | <span class="selo proj">DO PROJETO</span> |
| Registers 40020 | 10 | D2002… (limite de força D2006) | <span class="selo proj">DO PROJETO</span> |
| Registers 40030 | 10 | D2022… | <span class="selo proj">DO PROJETO</span> |
| Registers 40040 | 10 | D600… (deslocamento atual) | <span class="selo proj">DO PROJETO</span> |
| Registers 40050 | 10 | D92… | <span class="selo proj">DO PROJETO</span> |
| Coils 4000 | 10 | M5… (cima M5, baixo M6, parar M7, iniciar M9) | <span class="selo proj">DO PROJETO</span> |
| Coils 4010 | 10 | M30… (íntegro M30, ruptura M31) | <span class="selo proj">DO PROJETO</span> |
| Coils 4020 | 10 | M100… (zerar desloc. M100, tara M101) | <span class="selo proj">DO PROJETO</span> |
| Registers 40080 | 2 | D650 (força atual em kgf, a da tela) | <span class="selo nc">NÃO CONFIRMADO</span> |
| Registers 40060 | 2 | D3004 (tensão máxima) | <span class="selo nc">NÃO CONFIRMADO</span> |
| Registers 40070 | 2 | D610 (deslocamento máximo) | <span class="selo nc">NÃO CONFIRMADO</span> |
| Coils 4030 | 3 | X0, X1, X2 (emergência, limites) | <span class="selo nc">NÃO CONFIRMADO</span> |

As quatro últimas linhas foram propostas pela AUTOMATIC para o projeto da IHM.
Não há registro de que tenham sido criadas, exceto o indício da linha 40080
(o endereço da força foi mudado para 40079 na instalação, ver 4.4).

## 4.4 Mapa de registradores da tração (config.json entregue)

| Role | Endereço | Tipo / ordem | CLP | Status |
|---|---|---|---|---|
| `iniciar` (escrita) | coil 4003 | coil | M9 | <span class="selo proj">DO PROJETO</span> |
| `parar` (escrita) | coil 4001 | coil | M7 | <span class="selo proj">DO PROJETO</span> |
| `sentido_cima` (escrita) | coil 3999 | coil | M5 | <span class="selo proj">DO PROJETO</span> |
| `sentido_baixo` (escrita) | coil 4000 | coil | M6 | <span class="selo proj">DO PROJETO</span> |
| `zerar_deslocamento` (escrita) | coil 4019 | coil | M100 | <span class="selo ok">AJUSTADO EM CAMPO</span> |
| `zerar_celula` / tara (escrita) | coil 4020 | coil | M101 | <span class="selo proj">DO PROJETO</span> |
| `material_integro_bit` | coil 4009 | coil | M30 | <span class="selo proj">DO PROJETO</span> |
| `ruptura_bit` | coil 4010 | coil | M31 | <span class="selo proj">DO PROJETO</span> |
| `velocidade` (escrita) | 40000 | decimal ×100 / little | D408 | <span class="selo nc">NÃO CONFIRMADO</span> |
| `deslocamento_programado` (escrita) | 40004 | float32 / little | D412 | <span class="selo proj">DO PROJETO</span> |
| `limite_forca` (escrita) | 40023 | float32 / little | D2006 | <span class="selo proj">DO PROJETO</span> |
| `forca_maxima` | 40009 | float32 / little | D2012 | <span class="selo proj">DO PROJETO</span> |
| `deslocamento_atual` | 40039 | float32 / little | D600 | <span class="selo proj">DO PROJETO</span> |
| `forca_atual` | 40079 | float32 / little | D650 | <span class="selo ok">AJUSTADO EM CAMPO</span> |
| `tensao_maxima` | 40060 | float32 / little | D3004 | <span class="selo nc">NÃO CONFIRMADO</span> |
| `deslocamento_maximo` | 40070 | float32 / little | D610 | <span class="selo nc">NÃO CONFIRMADO</span> |
| `emergencia` | coil 4029 | coil | X0 | <span class="selo nc">NÃO CONFIRMADO</span> |
| `limite_inferior` | coil 4030 | coil | X1 | <span class="selo nc">NÃO CONFIRMADO</span> |
| `limite_superior` | coil 4031 | coil | X2 | <span class="selo nc">NÃO CONFIRMADO</span> |

Mudanças feitas na instalação (comparando o `config.json` antes e depois de
21/10/2026): `zerar_deslocamento` 4004 → 4019, `forca_atual` 40049 (D92) →
40079 (D650), `tensao_maxima` 40059 → 40060, `deslocamento_maximo` 40069 →
40070 e `clp_ip` vazio → 192.168.15.50.

## 4.5 Flexão

A flexão usa a mesma máquina e, por padrão, os mesmos registradores da tração.
Só os roles marcados em `flexao_separados` usam endereço próprio. No
`config.json` entregue, apenas `forca_atual` é separado, no endereço 40089
(float32, little), e o fim de ensaio usa o mesmo bit da ruptura (coil 4010).
O endereço 40089 não aparece em nenhuma linha conhecida da tabela da IHM:
<span class="selo nc">NÃO CONFIRMADO</span>.

## 4.6 Divergências e pendências

| # | Ponto | Risco | Ação sugerida |
|---|---|---|---|
| P1 | `tensao_maxima` e `deslocamento_maximo` foram para 40060 e 40070. Pela regra "tabela − 1", linhas criadas em 40060 e 40070 seriam lidas em 40059 e 40069. | Indicador com valor errado ou vazio (não afeta o ensaio). | Conferir no DOPSoft o número exato das linhas criadas e ajustar o endereço. |
| P2 | Velocidade na tração como `decimal` × 100 e na flexão como `decimal32` × 1, enquanto o projeto diz que os D são float32. | Velocidade enviada diferente da programada. | Escrever um valor conhecido e conferir na tela da IHM com o Diagnóstico de registrador. |
| P3 | Força da flexão separada em 40089 sem linha conhecida na IHM. | Flexão sem leitura de força. | Confirmar a linha ou desmarcar "Separar" para usar 40079. |
| P4 | Unidade da força (kgf) assumida. | Resultados 9,8× fora. | Pendurar massa conhecida e comparar. |
| P5 | Emergência e limites dependem da linha Coils 4030 → X0. | Indicadores vazios (o ensaio funciona). | Criar a linha ou retirar os roles. |
| P6 | IP: `clp_ip` 192.168.15.50 × `ihm_ip` 192.168.11.10. | Documentação divergente do campo. | Registrar o IP real da IHM na rede do cliente. |
| P7 | Significado do bit M8 e comportamento exato de M30/M31 no programa do CLP. | Gravação do ensaio fora de hora. | Conferir no ladder. Sem bit de ruptura, o ensaio é gravado ao Parar. |

## 4.7 Ferramentas de verificação

- **Diagnóstico de registrador** (Configurações → Controle): lê ou escreve um
  endereço e mostra o valor cru e interpretado.
- `varredura_ihm.py`: varre a memória da IHM **só lendo**. Anotar o valor da
  tela, rodar, mexer na máquina e rodar de novo: o endereço que mudou junto é
  o certo.
- `modbus_test.py` e `test_bit.py --scan`: leitura de faixas e busca de bits que
  mudam.
- Indicador de conexão (`/api/clp/conexao`): considera a máquina conectada só
  se a **força atual** for lida, o que também valida o endereço da força.

# 5. AQUISIÇÃO E PROCESSAMENTO

## 5.1 Regras de gravação

- Amostragem: `realtime_interval_ms` (100 ms). Cada amostra guarda tempo
  decorrido, força (N) e deslocamento (mm).
- Mínimo de 10 leituras de força para gravar.
- Se a conexão cai, o fluxo avisa a tela ("reconectando"), espera 1 s e tenta
  de novo, sem perder as amostras já coletadas.
- Gravação no fechamento do fluxo é síncrona, para não ser interrompida quando
  a tela fecha.
- Ensaios gravados **nunca são alterados nem apagados** por atualização ou
  migração. A edição pela tela muda só o cadastro (cliente, amostra, norma,
  operador, observações), nunca a série medida.

## 5.2 Cálculos de tração

| Grandeza | Definição |
|---|---|
| Tensão | σ = F ÷ A (MPa) |
| Deformação | ε = ΔL ÷ L₀ |
| Trecho elástico | Maior trecho com rigidez acima de 80 % da máxima, encurtado até a reta F × d ter R² ≥ 0,99 (mínimo 5 pontos) |
| Módulo de elasticidade | Inclinação da regressão σ × ε no trecho elástico, com R² |
| Rp0,2 | Cruzamento da curva com a reta elástica deslocada de 0,002 |
| Ruptura | Queda ≥ 25 % de Fmáx em até 2 amostras, ou queda gradual abaixo de 10 % de Fmáx |
| Alongamento na Fmáx | d/L₀ e (d − L₀)/L₀, em % |
| Alongamento final | Último deslocamento do ensaio, nas mesmas duas formas |
| Energia | ∫ F dd até a ruptura (J) |

As duas formas de alongamento existem porque o deslocamento da máquina pode
já incluir L₀, conforme a referência de zero usada no ensaio.

Estágios identificados na curva: acomodação, elástico linear, escoamento
superior, patamar de escoamento, encruamento, estricção, ruptura e
pós-ruptura.

## 5.3 Cálculos de flexão (3 pontos)

σf = 3·F·L ÷ (2·b·h²) e εf = 6·s·h ÷ L². Módulo por regressão no trecho
elástico e módulo cordal entre εf1 e εf2 da norma. Escoamento de flexão quando o
módulo local cai mais de 10 %.

## 5.4 Qualidade dos dados

Cada ensaio recebe uma avaliação com os itens: dados completos, dados
faltantes (lacunas de tempo), geometria do corpo de prova, curva válida,
ruptura detectada e alongamento estimado. Cada item fica OK, alerta ou erro e
aparece em Resultados.

## 5.5 Normas

ISO 527-2, ASTM D638, ABNT NBR ISO 6892-1, ASTM E8/E8M, ASTM D3039, ISO 37 e
ASTM D412 (tração); ISO 178 e ASTM D790 (flexão). Cada norma traz corpo de
prova, velocidade e L₀ ou vão sugeridos (`backend/normas.py`).

# 6. MODELO DE DADOS

## 6.1 Visão geral

Um único arquivo SQLite, `tracao.db`, na pasta da instalação. As tabelas são
criadas na primeira execução. Colunas novas de versões futuras são
acrescentadas automaticamente por `database.migrate()` sem tocar nos dados
existentes.

<figure class="diagrama">
<svg viewBox="0 0 640 210" xmlns="http://www.w3.org/2000/svg" font-family="Arial, Liberation Sans, sans-serif" font-size="11">
  <defs><marker id="s2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>
  <g>
    <rect x="250" y="10" width="140" height="34" rx="3" fill="#f9bd00"/><text x="320" y="32" text-anchor="middle" font-weight="bold">clientes</text>
    <rect x="20" y="90" width="150" height="34" rx="3" fill="#1d2021"/><text x="95" y="112" text-anchor="middle" font-weight="bold" fill="#fff">ensaios</text>
    <rect x="245" y="90" width="150" height="34" rx="3" fill="#1d2021"/><text x="320" y="112" text-anchor="middle" font-weight="bold" fill="#fff">ensaios_flexao</text>
    <rect x="470" y="90" width="150" height="34" rx="3" fill="#1d2021"/><text x="545" y="112" text-anchor="middle" font-weight="bold" fill="#fff">relatorios</text>
    <rect x="20" y="165" width="150" height="34" rx="3" fill="#f2f2f2" stroke="#999"/><text x="95" y="187" text-anchor="middle">parametros_ihm</text>
    <rect x="245" y="165" width="110" height="34" rx="3" fill="#f2f2f2" stroke="#999"/><text x="300" y="187" text-anchor="middle">usuarios</text>
    <rect x="375" y="165" width="110" height="34" rx="3" fill="#f2f2f2" stroke="#999"/><text x="430" y="187" text-anchor="middle">sessoes</text>
    <rect x="505" y="165" width="115" height="34" rx="3" fill="#f2f2f2" stroke="#999"/><text x="562" y="187" text-anchor="middle">auditoria</text>
  </g>
  <line x1="290" y1="44" x2="110" y2="88" stroke="#333" marker-end="url(#s2)"/>
  <line x1="320" y1="44" x2="320" y2="88" stroke="#333" marker-end="url(#s2)"/>
  <line x1="350" y1="44" x2="530" y2="88" stroke="#333" marker-end="url(#s2)"/>
  <line x1="95" y1="124" x2="95" y2="163" stroke="#333" marker-end="url(#s2)" stroke-dasharray="4 3"/>
  <text x="102" y="148">filename</text>
  <line x1="470" y1="107" x2="397" y2="107" stroke="#333" stroke-dasharray="4 3"/>
  <text x="400" y="80">ensaio_id + tipo</text>
  <line x1="300" y1="199" x2="300" y2="205" stroke="#fff"/>
  <line x1="355" y1="182" x2="373" y2="182" stroke="#333" marker-end="url(#s2)"/>
</svg>
<figcaption>Figura 2. Tabelas principais. Setas cheias: chave estrangeira cliente_id. Tracejadas: ligação lógica (sem chave estrangeira).</figcaption>
</figure>

## 6.2 Tabelas

**ensaios** (tração): `id`, `nome`, `filename` (único; `CLP_AAAAMMDD_HHMMSS.csv`
na aquisição direta), `data_ensaio`, `num_amostras`, `forca_max_N`,
`tensao_max_MPa`, `alonga_ruptura_pct`, `tempo_ruptura_s`, metadados do
equipamento, `created_at`, **`data_json`** (série completa do ensaio, com as
colunas derivadas e o estágio de cada ponto), `cliente_id`, `amostra`,
`norma`, `operador`, `observacoes`, `setup_json` (sentido, velocidade, curso,
limite, área, L₀), `usuario_id`, `usuario_nome`.

**ensaios_flexao**: mesma ideia, com `tensao_flexao_max_MPa`,
`modulo_flexao_MPa`, `deflexao_max_mm`, `tempo_ensaio_s`, `largura_mm`,
`espessura_mm`, `span_mm` e `norma`.

**parametros_ihm**: parâmetros lidos no momento do ensaio (`ensaio_filename`,
`captured_at`, `ihm_ip`, `params_json`), como área e L₀ usados.

**clientes**: `nome`, `documento` (CNPJ/CPF), `contato`, `email`, `telefone`,
`endereco`, `bairro`, `cidade_uf`, `cep`, `observacoes`.

**relatorios**: `ensaio_id` e `tipo` (`tracao` ou `flexao`, indica a tabela do
ensaio), `cliente_id`, `numero` (ex.: 0007/2026), `titulo`, `cliente_nome`,
`request_json` (campos usados), **`html`** (relatório completo, como emitido),
`usuario_id`, `usuario_nome`.

**usuarios**: `login` (único), `nome`, `cargo`, `registro`, `email`,
`senha_hash`, `ativo`, `trocar_senha`, datas de criação, alteração e último
login.

**sessoes**: `token_hash` (SHA-256 do token, nunca o token), `usuario_id`
(0 = mestre), `criada_em`, `ultimo_uso`, `ip`.

**auditoria**: `data`, `usuario_id`, `usuario` (login no momento), `acao`,
`detalhe`, `ip`.

## 6.3 Decisões

- O ensaio guarda o **nome** do usuário e do cliente além do id. Assim, excluir
  um usuário não apaga a autoria dos ensaios e relatórios.
- O relatório guarda o **HTML emitido**. Mudar o cadastro ou o cálculo depois
  não altera um relatório já entregue.
- A série medida fica em `data_json` dentro do banco, não em arquivos soltos:
  um único arquivo para copiar no backup.

# 7. LOGIN, USUÁRIOS E AUDITORIA

## 7.1 Perfis

| Perfil | Pode |
|---|---|
| Usuário | Operar a máquina, ver e editar cadastros, gerar relatórios, trocar a própria senha. |
| Técnico | Usuário que também sabe a senha das Configurações (padrão `tracao2026`, trocável em Configurações → Sobre). |
| Mestre | Login `mestre`, fixo no programa. Gerencia usuários, vê a auditoria e entra nas Configurações sem a senha do técnico. |

O mestre não pode ser alterado, desativado nem excluído pela tela e funciona
mesmo com o banco vazio. No código fica só o salt e o hash da senha; a senha é
entregue em separado pela AUTOMATIC e não consta deste documento. Trocá-la exige
gerar novo hash e novo executável.

## 7.2 Autenticação e sessão

- Senhas: PBKDF2-HMAC-SHA256, 200.000 iterações, salt individual de 16 bytes.
- Senha gerada pelo mestre: 10 caracteres de um alfabeto sem caracteres
  ambíguos, mostrada uma única vez. Opção de senha provisória, que obriga a
  troca no próximo login (até lá, só as rotas de sessão e troca de senha
  respondem).
- Cookie de sessão `maq_sessao`, HttpOnly. No banco fica só o hash do token.
- Expira após **8 h sem uso** ou **24 h** desde o login; também ao gerar nova
  senha ou desativar o usuário.
- **5 tentativas erradas** bloqueiam o login por **5 minutos**.
- Toda rota `/api` exige sessão, menos login, logout e `/api/health`.
- A senha do técnico das Configurações gera um token de 8 h enviado no
  cabeçalho `X-Config-Token`.

## 7.3 Auditoria

Ações registradas: `login`, `login_falhou`, `logout`, `usuario_criado`,
`usuario_editado`, `usuario_excluido`, `senha_trocada`, `senha_redefinida`,
`ensaio_iniciado`, `ensaio_editado`, `ensaio_excluido`, `relatorio_gerado`,
`relatorio_excluido`, `cliente_excluido`, `config_aberta`, `config_alterada`,
`config_senha_errada`, `config_senha_trocada`. Cada registro guarda data,
usuário, detalhe e IP. Só o mestre consulta (tela Usuários e acessos →
Registro de atividades).

# 8. PROTEÇÃO DE SOBRECARGA

- Ligada por `sobrecarga_ativa`, com limite em kgf (`sobrecarga_limite_kgf`).
- Cada leitura de força, em módulo e convertida para kgf, é comparada com o
  limite. Ao atingir, o monitor trava o alarme, envia o pulso de parada (role
  `parada_sobrecarga` se existir, senão `parar`) e o repete a cada 2 s
  enquanto a força continuar acima.
- O ensaio em andamento é gravado com o que foi coletado.
- Novo ensaio é recusado até o operador clicar **Reconhecer**.
- **Limitação:** a verificação depende das leituras feitas pelo software, ou
  seja, só funciona com a tela de Controle ou Flexão aberta. Não substitui a
  proteção do CLP nem a parada de emergência física.

# 9. RELATÓRIOS

- Gerados pelo servidor em HTML (`report.py`), com gráficos tensão ×
  deformação e força × deslocamento em PNG embutidos. A tela imprime ou salva
  em PDF pelo navegador.
- Seções: identificação da empresa e do cliente, identificação da(s)
  amostra(s), objetivos, condições do ensaio, resultados e conclusão.
- Numeração sugerida sequencial por ano (`NNNN/AAAA`), editável antes de
  emitir. Campos vêm pré-preenchidos com o último relatório e com o cadastro do
  ensaio (`/campos-relatorio`).
- Responsabilidade: "Emitido por" (usuário logado) e executor do ensaio, com
  nome, cargo e registro do cadastro do usuário. O mestre não assina.
- O relatório emitido fica salvo na tabela `relatorios` e pode ser reaberto
  igual ao original. Modos tração e flexão.
- Comparação de vários ensaios (sobreposição de curvas, média e desvio padrão)
  em abas separadas para tração e flexão.

# 10. BACKUP E RESTAURAÇÃO

- Destino: uma pasta local que o OneDrive, Google Drive ou Dropbox sincroniza.
  O sistema não guarda senha de nuvem.
- Conteúdo: `MaqTracao-backup-AAAAMMDD-HHMMSS.zip` com cópia consistente do
  `tracao.db` (API de backup do SQLite, segura com o programa gravando) e o
  `config.json`.
- Agenda: intervalo em horas (padrão 24), conferido a cada minuto; retenção dos
  últimos N arquivos (padrão 30). Botão "Fazer backup agora".
- Restauração: parar a tarefa MaqTracao, trocar o `tracao.db` (e, se quiser, o
  `config.json`) pelo do zip e iniciar de novo.

# 11. CONFIGURAÇÃO

Toda a configuração fica em `config.json`, editado pela tela (Configurações,
com senha do técnico ou mestre) e aplicado na hora, sem reiniciar. As chaves
principais:

| Grupo | Chaves |
|---|---|
| Conexão | `clp_ip`, `clp_port`, `clp_timeout`, `ihm_ip`, `ihm_port`, `ihm_timeout`, `plc_family` |
| Registradores | `control_registers`, `flexao_registers`, `flexao_separados` |
| Ensaio | `control_pulse_ms`, `realtime_interval_ms`, `forca_clp_kgf`, `area_seccao_mm2`, `comprimento_inicial_mm`, `flexao_*` |
| Proteção | `sobrecarga_ativa`, `sobrecarga_limite_kgf` |
| Backup | `backup_ativo`, `backup_dir`, `backup_intervalo_h`, `backup_manter` |
| CSV / FTP | `watch_directory`, `auto_load`, `refresh_interval_s`, `ftp_*`, `ihm_registers` |
| Servidor | `server_host` (127.0.0.1), `server_port` (8000) |
| Outros | `simulator_enabled` (false na entrega), `senha_config`, `proximo_ensaio*` |

A descrição completa de cada chave e de cada role está no Manual, seções 11 e 14.

# 12. IMPLANTAÇÃO

## 12.1 Geração do pacote

No PC de desenvolvimento, a partir da master: conferir `backend/config.json`
(vira o padrão da primeira instalação) e rodar
`instalacao\build_cliente_nuitka.bat` (recomendado, compila para código de
máquina) ou `build_cliente.bat` (PyInstaller). Sai
`build-cliente\MaqTracao-instalador.zip`. A instalação de 21/10/2026 foi feita
com o build Nuitka.

## 12.2 Instalação no cliente

`instalar.bat` como administrador:

| Item | Valor |
|---|---|
| Pasta | `C:\MaqTracao\` (só Administradores e SYSTEM; `data\` liberada a usuários) |
| Arquivos | `MaqTracao.exe`, `config.json`, `tracao.db`, `data\`, `logs\servidor.log` |
| Início | Tarefa agendada **MaqTracao**, conta SYSTEM, na inicialização do Windows, reinicia se cair |
| Acesso | Atalho "Máquina de Tração" abre `http://localhost:8000` no Edge em modo aplicativo |
| Rede | Atende só em 127.0.0.1. Para outro PC, `server_host` = 0.0.0.0 e liberar a porta no firewall |
| API | Documentação interativa (`/docs`) desligada na versão do cliente |

O PC precisa de uma placa de rede na mesma faixa da IHM. A proteção da pasta só
é efetiva se o operador usar conta padrão do Windows.

## 12.3 Atualização e desinstalação

Atualizar: backup, novo zip, `instalar.bat` de novo. Troca só o programa e
mantém `config.json`, `tracao.db`, `data\` e `logs\`. O banco é migrado na
subida sem perder ensaios. Desinstalar: `desinstalar.bat` remove programa,
tarefa e atalho e mantém os dados.

**Situação atual:** login, usuários e auditoria (05/11/2026) e o alongamento
final (06/11/2026) estão na master, mas só chegam à máquina com um novo build e
reinstalação.

# 13. INTERFACE DE PROGRAMAÇÃO (API)

O servidor expõe uma API REST em `http://localhost:8000/api`, usada pela tela.
Grupos de rotas:

| Grupo | Rotas |
|---|---|
| Sessão | `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/senha` |
| Usuários (mestre) | `/usuarios`, `/usuarios/{id}/senha`, `/auditoria` |
| Máquina | `/clp/conexao`, `/control/start`, `/stop`, `/setpoints`, `/zerar-deslocamento`, `/zerar-celula`, `/status`, `/stream`, `/probe` e equivalentes em `/flexao/control/` |
| Ensaios | `/ensaios`, `/ensaios/{id}` e `/kpis`, `/curvas`, `/qualidade`, `/parametros_ihm`, `/reimport`; equivalentes em `/flexao/ensaios` |
| Cadastro | `/clientes`, `/busca`, `/normas` |
| Relatórios | `/relatorio`, `/relatorios`, `/relatorios/{id}/html`, `/ensaios/{id}/campos-relatorio` |
| Sistema | `/config`, `/config/login`, `/config/senha`, `/backup`, `/backup/agora`, `/sobrecarga`, `/sobrecarga/reconhecer`, `/scan`, `/ftp/fetch_csv`, `/health` |

A API não foi publicada para terceiros: não tem autenticação por chave nem
documentação externa. Não deve ser exposta fora da rede local.

# 14. TESTES

Testes automatizados em `backend/tests/` (pytest), rodados no ambiente de
desenvolvimento antes de cada entrega. O repositório não tem integração
contínua.

| Arquivo | Cobre |
|---|---|
| `test_parser.py` | Leitura do CSV da IHM, detecção de ruptura, KPIs e energia |
| `test_control.py` | Codificação float32/int32, conversão de dispositivos Delta, montagem do ensaio, escala, força kgf → N, alongamento final, senha das Configurações |
| `test_flexao.py` | Cálculos e aquisição de flexão, deflexão negativa |
| `test_cadastro.py` | Ajuste elástico e R², qualidade, clientes, busca, normas, migração de banco antigo, relatório de flexão |
| `test_report.py` | Numeração de figuras e tabelas, KPI ausente, energia em joules |
| `test_sobrecarga.py` | Disparo, trava até reconhecer, módulo da força, falha do pulso, registrador próprio |
| `test_backup.py` | Geração do zip, retenção, intervalo, pasta inválida |
| `test_auth.py` | Login obrigatório, mestre fixo, gestão de usuários, bloqueio, logout, dados do usuário no relatório |

Os testes usam o simulador e dados sintéticos; não substituem a verificação na
máquina do Anexo A.

# 15. LIMITAÇÕES CONHECIDAS E EVOLUÇÕES

- Itens não confirmados do mapa de registradores (seção 4.6).
- Proteção de sobrecarga depende da tela aberta (seção 8).
- Sem bit de ruptura mapeado, o ensaio só é gravado ao Parar ou fechar a tela.
- Se o programa for desligado no meio do ensaio, as amostras se perdem.
- A proteção de arquivos depende de o operador usar conta padrão do Windows.
- Evoluções previstas, ainda não feitas: assinatura eletrônica de relatórios,
  API para sistemas externos com autenticação própria e detecção de falha do
  corpo de prova por IA.

<div class="quebra"></div>

# ANEXO A. ROTEIRO DE VERIFICAÇÃO EM CAMPO

Fazer com a máquina sem corpo de prova, salvo indicação. Usar o Diagnóstico de
registrador (só leitura, salvo os itens de escrita) e comparar com a tela da
IHM. Anotar o resultado e, ao final, salvar uma cópia do `config.json` da
máquina junto com esta folha.

| # | Sinal | Como verificar | Resultado |
|---|---|---|---|
| 1 | IP da IHM | Anotar o IP configurado na IHM e conferir `clp_ip` | |
| 2 | Força atual (40079) | Tara; pendurar massa conhecida; comparar com a IHM e com a massa (kgf × N) | |
| 3 | Deslocamento atual (40039) | Mover a travessa; comparar com a IHM | |
| 4 | Zerar deslocamento (4019) | Botão na tela; IHM deve ir a zero | |
| 5 | Tara (4020) | Botão na tela; força deve ir a zero | |
| 6 | Velocidade (40000) | Enviar 10 mm/min; conferir na IHM | |
| 7 | Curso (40004) | Enviar 5 mm; conferir na IHM | |
| 8 | Limite de força (40023) | Enviar valor; conferir na IHM | |
| 9 | Sentido cima/baixo (3999/4000) | Iniciar ensaio curto em cada sentido | |
| 10 | Iniciar / Parar (4003/4001) | Iniciar e parar pela tela | |
| 11 | Ruptura (4010) | Ensaio com corpo de prova até romper; o ensaio deve gravar sozinho | |
| 12 | Força máxima (40009) | Comparar com a IHM após o ensaio | |
| 13 | Tensão máx. / desl. máx. (40060/40070) | Conferir com a IHM; ver P1 | |
| 14 | Emergência / limites (4029–4031) | Acionar emergência e fins de curso | |
| 15 | Força na flexão (40089) | Ensaio de flexão curto; ver P3 | |
| 16 | Sobrecarga | Limite baixo de teste; aplicar carga; máquina deve parar | |
| 17 | Backup | "Fazer backup agora"; conferir o zip na pasta da nuvem | |

<table class="assinatura">
<tr><td>Responsável pela verificação</td><td>Data</td><td>Assinatura</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
</table>

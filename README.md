# Analisador de Ensaios de Tração

Software desktop para análise automática de arquivos CSV gerados pela IHM da máquina de tração (formato `HISTORY V1.0`).

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + Python 3.11+ |
| Dados | pandas, numpy, scipy |
| Banco | SQLite (via SQLAlchemy) |
| Monitoramento | watchdog |
| Frontend | React 18 + TypeScript + Vite |
| Gráficos | Recharts |
| Estilo | Tailwind CSS |

## Pré-requisitos

- Python 3.11 ou superior
- Node.js 20 ou superior
- npm 9+

## Instalação

```bat
setup.bat
```

O script de setup:
1. Cria o ambiente virtual Python (`venv/`)
2. Instala todas as dependências Python
3. Gera o arquivo de exemplo `data/H0001.csv`
4. Instala as dependências do frontend

## Execução

```bat
start.bat
```

Abre dois terminais: backend na porta **8000** e frontend na **5173**.  
O browser abre automaticamente em `http://localhost:5173`.

### Execução manual (alternativa)

```bash
# Terminal 1 — Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

## Formato do Arquivo CSV

O software lê arquivos `.csv` com as seguintes características:

- **Encoding:** UTF-16 com BOM (`\xff\xfe`)
- **Separador:** TAB
- **Linha 1:** `HISTORY V1.0\t<ID_equipamento>\t<codigo>`
- **Linha 2:** vazia
- **Linha 3:** nomes das colunas
- **Linha 4:** marcadores de canal
- **Linhas 5+:** dados numéricos (1 amostra/segundo)

### Colunas

| # | Nome | Unidade |
|---|------|---------|
| 1 | TIME | HH:MM:SS |
| 2 | DATA | DD/MM/AAAA |
| 3 | Tensao_Pa | MPa |
| 4 | Modulo_Elast | MPa |
| 5 | Tensao_Max | MPa |
| 6 | Deform_Along | adimensional |
| 7 | Alonga_Ruptura | % |
| 8 | Deslocamento | mm |
| 9 | Forca_N | N |
| 10 | Checksum | string |

## Funcionalidades

### Dashboard
- **7 KPI cards** no topo (Fmax, σmax, E, δ, deslocamento, tempo, energia)
- **5 gráficos** interativos com marcador de ruptura em laranja tracejado:
  - Tensão × Deformação (σ-ε) — gráfico principal
  - Força × Deslocamento (F-d)
  - Força × Tempo
  - Módulo de Elasticidade × Tempo
  - Tensão × Tempo (σ e envelope σmax)

### Indicadores calculados
| Indicador | Método |
|-----------|--------|
| Rigidez k | ΔF/Δd na fase de carregamento |
| Energia absorvida | ∫F·dd (numpy.trapz) |
| Tensão de escoamento (est.) | Primeiro ponto onde E cai >10% do valor inicial |
| Taxa de carregamento | dF/dt médio na fase de carregamento |
| CV do módulo | std(E)/mean(E) na região elástica (primeiros 30%) |

### Comparação
Selecione múltiplos ensaios na barra lateral (botão "+ Comparar") para ver:
- Curvas σ-ε sobrepostas com cores distintas
- Tabela comparativa com todos os KPIs

### Relatório
Botão "Gerar Relatório" abre um modal com opções de conteúdo.  
O relatório HTML abre em nova aba — use Ctrl+P no browser para salvar como PDF.

### Monitoramento automático
Configure o diretório de exportação da IHM em **Configurações**.  
Novos arquivos `.csv` são detectados e carregados automaticamente via `watchdog`.

## Estrutura do Projeto

```
maq-tracao/
├── backend/
│   ├── main.py          # FastAPI + endpoints
│   ├── parser.py        # Parser UTF-16 do CSV
│   ├── calculator.py    # KPIs e dados para gráficos
│   ├── database.py      # SQLite (SQLAlchemy)
│   ├── watcher.py       # Monitoramento de diretório
│   ├── report.py        # Gerador de relatório HTML
│   └── tests/
│       └── test_parser.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Sidebar/
│       │   ├── Dashboard/
│       │   ├── Charts/      # 5 componentes Recharts
│       │   ├── Comparison/
│       │   ├── Reports/
│       │   └── Config/
│       ├── api/client.ts
│       ├── hooks/
│       └── types/
├── data/
│   └── H0001.csv        # Gerado pelo setup
├── generate_sample.py
├── requirements.txt
├── setup.bat
└── start.bat
```

## Testes

```bash
# Ativar venv primeiro
venv\Scripts\activate

# Executar testes
pytest backend/tests/ -v
```

Os testes cobrem: parsing básico, detecção de ruptura, tempo decorrido, energia absorvida, campos de KPI e estrutura dos dados para gráficos.

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/ensaios` | Lista todos os ensaios |
| GET | `/api/ensaios/{id}` | Detalhe de um ensaio |
| GET | `/api/ensaios/{id}/kpis` | KPIs calculados |
| GET | `/api/ensaios/{id}/curvas` | Dados formatados para os 5 gráficos |
| DELETE | `/api/ensaios/{id}` | Remove um ensaio do banco |
| POST | `/api/relatorio` | Gera relatório HTML |
| GET | `/api/config` | Configurações atuais |
| PUT | `/api/config` | Atualiza configurações |
| POST | `/api/scan` | Força rescan do diretório |

Documentação interativa disponível em `http://localhost:8000/docs`.

## Arquivos de Dados

O banco SQLite (`tracao.db`) é criado automaticamente na raiz do projeto.  
Os ensaios carregados persistem entre sessões — ao reabrir o software os dados anteriores aparecem na barra lateral.

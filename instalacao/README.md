# Instalação no PC do cliente

O cliente recebe só o programa compilado: um `MaqTracao.exe` que sobe o backend
e serve a tela (frontend já buildado) em `http://localhost:8000`. Não vão para o
PC do cliente o código-fonte, o Python, o Node, o `venv` nem o `git`.

## O que fica no PC do cliente

```
C:\MaqTracao\
  MaqTracao.exe      programa (backend + tela), sem janela
  _internal\         bibliotecas e o código em bytecode, empacotados
  config.json        configurações: IP da IHM, registradores... (editável)
  tracao.db          banco dos ensaios
  data\              pasta monitorada de CSVs
  logs\servidor.log  log do servidor
```

- Inicia sozinho com o Windows (tarefa agendada `MaqTracao`, como SYSTEM, antes
  do login) e é reiniciado se cair.
- Atalho **Maquina de Tracao** na área de trabalho abre a tela no navegador.
- A pasta `C:\MaqTracao` só abre para Administradores. A subpasta `data\` fica
  liberada para usuários comuns (digite `C:\MaqTracao\data` no Explorer) caso
  precisem colocar CSVs à mão.
- A documentação da API (`/docs`) fica desligada nessa versão.
- Só atende no próprio PC (`127.0.0.1`). Para abrir de outro PC da rede, coloque
  `"server_host": "0.0.0.0"` no `config.json` e reinicie (talvez precise liberar
  a porta 8000 no firewall). `"server_port"` muda a porta.

## Passo a passo

### 1. Gerar o pacote (no seu PC, não no do cliente)

Precisa de Python 3.11+ e Node 20+, os mesmos do `setup.bat`.

1. `git pull` na master.
2. Confira `backend\config.json`: ele vira o padrão da primeira instalação
   (IP da IHM, registradores). Depois de instalado, o cliente edita pela tela
   **Configurações** ou no `C:\MaqTracao\config.json`.
3. Rode `instalacao\build_cliente.bat` (duplo clique). Leva alguns minutos.
4. Sai `build-cliente\MaqTracao-instalador.zip`.

### 2. Instalar no PC do cliente

1. Copie o zip para o PC do cliente (pen drive) e extraia.
2. Clique com o botão direito em `instalar.bat` > **Executar como administrador**.
3. O navegador abre em `http://localhost:8000`. Confira em **Configurações** o
   IP da IHM (`192.168.11.10`) e a pasta monitorada.
4. Apague a pasta extraída e o zip.
5. Reinicie o PC uma vez e confirme que a tela abre pelo atalho sem fazer nada.

### 3. Conta do operador (importante)

A proteção da pasta só vale se o operador **não for administrador** do PC.
Se o cliente usa uma conta administradora, crie uma conta padrão para quem opera
a máquina (Configurações do Windows > Contas > Outros usuários) e guarde a senha
de administrador com vocês.

### Atualizar

Gere um zip novo e rode `instalar.bat` de novo. Ele para o programa, troca só o
executável e mantém `config.json`, `tracao.db`, `data\` e `logs\`.

### Desinstalar

`desinstalar.bat` como administrador. Remove o programa, a tarefa e o atalho e
mantém os dados.

### Se a tela não abrir

- Veja `C:\MaqTracao\logs\servidor.log` (como administrador).
- Agendador de Tarefas > `MaqTracao` > Executar, ou reinicie o PC.
- Porta 8000 ocupada por outro programa: mude `"server_port"` no `config.json`
  e o atalho da área de trabalho.

## Até onde vai a proteção

Nenhuma proteção é absoluta. O que esse pacote garante:

- Não há arquivo `.py` legível no PC do cliente; o código vai como bytecode
  compactado dentro do executável.
- Um operador sem conta de administrador não abre a pasta do programa.

O que ele **não** impede:

- Um administrador do PC com conhecimento técnico consegue extrair o bytecode do
  executável e reconstruir boa parte do código Python com ferramentas públicas.
- O JavaScript da tela chega ao navegador (é assim que qualquer site funciona).
  Ele vai minificado e sem source map, mas pode ser lido.

Para dificultar mais, o próximo passo seria compilar o backend com **Nuitka**
(vira código C compilado, bem mais difícil de reverter) no lugar do PyInstaller.
Na prática, a proteção mais forte é contratual: licença ou contrato com cláusula
de não engenharia reversa.

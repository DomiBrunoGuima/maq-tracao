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
- Atalho **Maquina de Tracao** na área de trabalho abre a tela no Edge em modo
  aplicativo (janela própria, sem barra de endereço). O ícone é o
  `instalacao\icone.ico`; para trocar, substitua esse arquivo antes do build
  (ou o `icone.ico` dentro do zip, antes de rodar o `instalar.bat`).
- A pasta `C:\MaqTracao` só abre para Administradores. A subpasta `data\` fica
  liberada para usuários comuns (digite `C:\MaqTracao\data` no Explorer) caso
  precisem colocar CSVs à mão.
- A tela **Configurações** só aparece para o login `desenvolvedor` (AUTOMATIC).
  Antes do build, defina a senha com `python instalacao\definir_senha_desenvolvedor.py`
  (grava só o hash em `backend/credencial_desenvolvedor.py`). Sem isso o login
  fica desativado e ninguém abre as Configurações. O `mestre` do cliente só
  gerencia usuários.
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

#### Versão compilada com Nuitka (recomendada para o cliente)

`instalacao\build_cliente_nuitka.bat` gera o mesmo zip, mas com o backend
compilado em código de máquina pelo Nuitka, bem mais difícil de reverter do que
o PyInstaller. Na primeira vez ele baixa sozinho um compilador C (gcc ou zig);
o build leva de 20 a 40 minutos. Instalação e uso são iguais.

### 2. Instalar no PC do cliente

1. Copie o zip para o PC do cliente (pen drive) e extraia.
2. Clique com o botão direito em `instalar.bat` > **Executar como administrador**.
3. O navegador abre em `http://localhost:8000`. Confira em **Configurações** o
   IP da IHM (`192.168.15.50`) e a pasta monitorada.
4. Apague a pasta extraída e o zip.
5. Reinicie o PC uma vez e confirme que a tela abre pelo atalho sem fazer nada.

### 3. Conta do operador (importante)

A proteção da pasta só vale se o operador **não for administrador** do PC.
Se o cliente usa uma conta administradora, crie uma conta padrão para quem opera
a máquina (Configurações do Windows > Contas > Outros usuários) e guarde a senha
de administrador com vocês.

### Atualizar (sem mexer nos registradores do cliente)

Os registradores, o IP da IHM e as demais configurações ficam só no
`C:\MaqTracao\config.json` do cliente; ensaios, clientes, usuários e auditoria
ficam no `tracao.db`. O `instalar.bat` troca só o programa e mantém esses dois
arquivos, `data\` e `logs\`. O `backend\config.json` do repositório só vale na
primeira instalação (quando ainda não existe `C:\MaqTracao\config.json`).

1. **No seu PC:** `git pull`, defina a senha do desenvolvedor
   (`python instalacao\definir_senha_desenvolvedor.py`; sem ela ninguém abre as
   Configurações) e gere o zip (`build_cliente_nuitka.bat`).
2. **No PC do cliente, antes de instalar:** como administrador, copie
   `C:\MaqTracao\config.json` e `C:\MaqTracao\tracao.db` para um pen drive ou
   para a área de trabalho. Tire um print da tela **Configurações** (IP e
   registradores), se tiver acesso a ela.
3. Extraia o zip novo e rode `instalar.bat` como administrador. Ele:
   - para o programa;
   - guarda outra cópia de `config.json` e `tracao.db` em
     `C:\MaqTracao\backups-atualizacao\<data-hora>` (nunca apagada pelo instalador);
   - troca o programa e confere com `fc` que o `config.json` ficou idêntico
     (se não ficou, restaura a cópia e avisa).
4. **Conferir depois:**
   - O instalador não pode mostrar `[AVISO] config.json tinha mudado`. Para
     conferir à mão: `fc C:\MaqTracao\config.json <cópia>\config.json` deve
     dizer "nenhuma diferença encontrada".
   - Entre com o login `desenvolvedor` e confira em **Configurações** o IP e os
     registradores contra o print. Campos novos aparecem com o valor padrão, sem
     tocar nos endereços. Não clique em Salvar se não for mudar nada.
   - Na tela de controle, o indicador do CLP fica **conectado** e a força mostrada
     bate com a da IHM. Se a força vier ~9,8 vezes maior ou menor, ajuste só
     **Configurações → Controle → Unidade da força no CLP** (kgf/N): instalações
     de antes de 29/10/2026 não têm essa opção gravada e assumem kgf.
   - Os ensaios antigos continuam na lista.
5. **Se algo der errado:** pare a tarefa (`schtasks /end /tn MaqTracao`), copie de
   volta o `config.json` e o `tracao.db` da cópia e inicie de novo
   (`schtasks /run /tn MaqTracao`).

Novidades que dependem de configuração ficam desligadas ou com padrão neutro em
`config.json` antigos: flexão usa os registradores da tração enquanto
`flexao_registers` estiver vazio; sobrecarga e backup automático ficam
desligados. O login `mestre` e os usuários entram no `tracao.db` sem apagar nada.

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

Com o build do **Nuitka** o primeiro ponto fica bem mais difícil: não há
bytecode Python para extrair, só código de máquina.
Na prática, a proteção mais forte é contratual: licença ou contrato com cláusula
de não engenharia reversa.

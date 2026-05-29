-- =============================================
-- Configurações — ajuste conforme seu projeto
-- =============================================
local LINK        = "Link1"       -- nome do link do seu CLP
local ESTACAO     = 1             -- número da estação
local END_INICIO  = 0x6001        -- bit que indica "teste em andamento" ($6001)
local REGISTRADORES = {
    0xD3000, 0xD3001, 0xD3002     -- endereços que você quer gravar
}
local INTERVALO_MS = 1000         -- coleta a cada 1 segundo

-- =============================================
-- Variáveis internas
-- =============================================
local coletando    = false
local linhas       = {}
local nome_arquivo = ""

-- =============================================
-- Loop principal
-- =============================================
while true do

    -- Lê o bit de controle do CLP (1 = teste ativo)
    local status = mem.inter.Read(END_INICIO)

    -- ---- INÍCIO DO TESTE ----
    if status == 1 and not coletando then
        coletando    = true
        linhas       = {}   -- limpa dados anteriores
        nome_arquivo = "/usb/teste_" .. os.date("%Y%m%d_%H%M%S") .. ".csv"

        -- Cabeçalho do CSV
        local cabecalho = "Timestamp"
        for i, _ in ipairs(REGISTRADORES) do
            cabecalho = cabecalho .. ",Reg" .. i
        end
        table.insert(linhas, cabecalho)
    end

    -- ---- COLETA DE DADOS ----
    if coletando then
        local linha = os.date("%H:%M:%S")
        for _, addr in ipairs(REGISTRADORES) do
            local val = plc.Read(LINK, ESTACAO, addr)
            linha = linha .. "," .. tostring(val)
        end
        table.insert(linhas, linha)
    end

    -- ---- FIM DO TESTE ----
    if status == 0 and coletando then
        coletando = false

        -- Grava tudo de uma vez no arquivo
        local f = io.open(nome_arquivo, "w")
        if f then
            for _, l in ipairs(linhas) do
                f:write(l .. "\n")
            end
            f:close()
        end

        linhas = {}  -- libera memória
    end

    sys.Sleep(INTERVALO_MS)
end

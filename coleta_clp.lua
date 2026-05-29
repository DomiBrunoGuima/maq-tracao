-- =============================================
-- Configurações
-- =============================================
local LINK     = "Link1"
local ESTACAO  = 1
local BIT_CTRL = 6001  -- $6001: 1 = teste ativo, 0 = encerrado

local INTERVALO_MS = 1000  -- coleta a cada 1 segundo

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

    local status = mem.inter.Read(BIT_CTRL)

    -- ---- INÍCIO DO TESTE ----
    if status == 1 and not coletando then
        coletando    = true
        linhas       = {}
        nome_arquivo = "/usb/teste_" .. os.date("%Y%m%d_%H%M%S") .. ".csv"

        -- Cabeçalho
        table.insert(linhas, "Timestamp,D412,D408,D92,D600")
    end

    -- ---- COLETA ----
    if coletando then
        local d412 = plc.Read(LINK, ESTACAO, "D412")
        local d408 = plc.Read(LINK, ESTACAO, "D408")
        local d92  = plc.Read(LINK, ESTACAO, "D92")
        local d600 = plc.Read(LINK, ESTACAO, "D600")

        local linha = os.date("%H:%M:%S")
            .. "," .. tostring(d412)
            .. "," .. tostring(d408)
            .. "," .. tostring(d92)
            .. "," .. tostring(d600)

        table.insert(linhas, linha)
    end

    -- ---- FIM DO TESTE ----
    if status == 0 and coletando then
        coletando = false

        local f = io.open(nome_arquivo, "w")
        if f then
            for _, l in ipairs(linhas) do
                f:write(l .. "\n")
            end
            f:close()
        end

        linhas = {}
    end

    sys.Sleep(INTERVALO_MS)
end
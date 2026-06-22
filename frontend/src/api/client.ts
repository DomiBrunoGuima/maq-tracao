import axios from "axios";
import type {
  AppConfig,
  ChartData,
  ControlSetpointsRequest,
  ControlStartRequest,
  ControlStatus,
  EnsaioDetail,
  EnsaioFlexaoDetail,
  EnsaioFlexaoSummary,
  EnsaioSummary,
  FlexaoChartData,
  FlexaoControlStartRequest,
  KPIs,
  KPIsFlexao,
  ModbusFetchResult,
  ParametrosIHM,
  RegisterProbeRequest,
  RegisterProbeResult,
  ReportRequest,
} from "../types";

const api = axios.create({ baseURL: "/api" });

export const getEnsaios = (): Promise<EnsaioSummary[]> =>
  api.get("/ensaios").then((r) => r.data);

export const getEnsaio = (id: number): Promise<EnsaioDetail> =>
  api.get(`/ensaios/${id}`).then((r) => r.data);

export const getKPIs = (id: number): Promise<KPIs> =>
  api.get(`/ensaios/${id}/kpis`).then((r) => r.data);

export const getCurvas = (id: number): Promise<ChartData> =>
  api.get(`/ensaios/${id}/curvas`).then((r) => r.data);

export const deleteEnsaio = (id: number): Promise<void> =>
  api.delete(`/ensaios/${id}`).then(() => undefined);

export const getConfig = (): Promise<AppConfig> =>
  api.get("/config").then((r) => r.data);

export const updateConfig = (config: AppConfig): Promise<AppConfig> =>
  api.put("/config", config).then((r) => r.data);

export const scanDirectory = (): Promise<{ scanned: string[] }> =>
  api.post("/scan").then((r) => r.data);

export const getParametrosIHM = (id: number): Promise<ParametrosIHM | null> =>
  api.get(`/ensaios/${id}/parametros_ihm`).then((r) => r.data);

export const fetchFtpCsv = (): Promise<ModbusFetchResult> =>
  api.post("/ftp/fetch_csv").then((r) => r.data);

export const reimportAll = (): Promise<{ reimported: number; details: { file: string; ok: boolean }[] }> =>
  api.post("/reimport-all").then((r) => r.data);

// ── Controle da máquina (CLP) ──────────────────────────────────────────────

export const startTest = (req: ControlStartRequest): Promise<{ status: string; sentido: string; setpoints: Record<string, number> }> =>
  api.post("/control/start", req).then((r) => r.data);

export const stopTest = (): Promise<{ status: string }> =>
  api.post("/control/stop").then((r) => r.data);

export const setSetpoints = (req: ControlSetpointsRequest): Promise<{ status: string; setpoints: Record<string, number> }> =>
  api.post("/control/setpoints", req).then((r) => r.data);

export const getControlStatus = (): Promise<ControlStatus> =>
  api.get("/control/status").then((r) => r.data);

export const probeRegister = (req: RegisterProbeRequest): Promise<RegisterProbeResult> =>
  api.post("/control/probe", req).then((r) => r.data);

export const zerarDeslocamento = (): Promise<{ status: string }> =>
  api.post("/control/zerar-deslocamento").then((r) => r.data);

export const zerarCelula = (): Promise<{ status: string }> =>
  api.post("/control/zerar-celula").then((r) => r.data);

// ── Flexão (módulo separado) ───────────────────────────────────────────────

export const getEnsaiosFlexao = (): Promise<EnsaioFlexaoSummary[]> =>
  api.get("/flexao/ensaios").then((r) => r.data);

export const getEnsaioFlexao = (id: number): Promise<EnsaioFlexaoDetail> =>
  api.get(`/flexao/ensaios/${id}`).then((r) => r.data);

export const getKPIsFlexao = (id: number): Promise<KPIsFlexao> =>
  api.get(`/flexao/ensaios/${id}/kpis`).then((r) => r.data);

export const getCurvasFlexao = (id: number): Promise<FlexaoChartData> =>
  api.get(`/flexao/ensaios/${id}/curvas`).then((r) => r.data);

export const deleteEnsaioFlexao = (id: number): Promise<void> =>
  api.delete(`/flexao/ensaios/${id}`).then(() => undefined);

export const startFlexaoTest = (req: FlexaoControlStartRequest): Promise<{ status: string; sentido: string; setpoints: Record<string, number> }> =>
  api.post("/flexao/control/start", req).then((r) => r.data);

export const stopFlexaoTest = (): Promise<{ status: string }> =>
  api.post("/flexao/control/stop").then((r) => r.data);

export const getFlexaoStatus = (): Promise<ControlStatus> =>
  api.get("/flexao/control/status").then((r) => r.data);

export const zerarDeslocamentoFlexao = (): Promise<{ status: string }> =>
  api.post("/flexao/control/zerar-deslocamento").then((r) => r.data);

export const zerarCelulaFlexao = (): Promise<{ status: string }> =>
  api.post("/flexao/control/zerar-celula").then((r) => r.data);

export const generateReport = async (req: ReportRequest): Promise<void> => {
  const response = await api.post("/relatorio", req, { responseType: "blob" });
  const url = URL.createObjectURL(
    new Blob([response.data], { type: "text/html" })
  );
  window.open(url, "_blank");
};

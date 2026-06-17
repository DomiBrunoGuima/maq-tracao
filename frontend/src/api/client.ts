import axios from "axios";
import type {
  AppConfig,
  ChartData,
  ControlSetpointsRequest,
  ControlStartRequest,
  ControlStatus,
  EnsaioDetail,
  EnsaioSummary,
  KPIs,
  ModbusFetchResult,
  ParametrosIHM,
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

export const generateReport = async (req: ReportRequest): Promise<void> => {
  const response = await api.post("/relatorio", req, { responseType: "blob" });
  const url = URL.createObjectURL(
    new Blob([response.data], { type: "text/html" })
  );
  window.open(url, "_blank");
};

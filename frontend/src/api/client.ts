import axios from "axios";
import type {
  AppConfig,
  ChartData,
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

export const generateReport = async (req: ReportRequest): Promise<void> => {
  const response = await api.post("/relatorio", req, { responseType: "blob" });
  const url = URL.createObjectURL(
    new Blob([response.data], { type: "text/html" })
  );
  window.open(url, "_blank");
};

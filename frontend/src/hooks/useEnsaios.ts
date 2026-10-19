import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/client";

export function useEnsaios() {
  return useQuery({
    queryKey: ["ensaios"],
    queryFn: api.getEnsaios,
    refetchInterval: 8000,
  });
}

export function useEnsaio(id: number | null) {
  return useQuery({
    queryKey: ["ensaio", id],
    queryFn: () => api.getEnsaio(id!),
    enabled: id !== null,
  });
}

export function useKPIs(id: number | null) {
  return useQuery({
    queryKey: ["kpis", id],
    queryFn: () => api.getKPIs(id!),
    enabled: id !== null,
  });
}

export function useCurvas(id: number | null) {
  return useQuery({
    queryKey: ["curvas", id],
    queryFn: () => api.getCurvas(id!),
    enabled: id !== null,
  });
}

export function useDeleteEnsaio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteEnsaio,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ensaios"] }),
  });
}

export function useScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.scanDirectory,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ensaios"] }),
  });
}

export function useReimportAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.reimportAll,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ensaios"] }),
  });
}

export function useParametrosIHM(id: number | null) {
  return useQuery({
    queryKey: ["parametros_ihm", id],
    queryFn: () => api.getParametrosIHM(id!),
    enabled: id !== null,
  });
}

export function useQualidade(id: number | null) {
  return useQuery({
    queryKey: ["qualidade", id],
    queryFn: () => api.getQualidade(id!),
    enabled: id !== null,
  });
}

export function useClientes() {
  return useQuery({ queryKey: ["clientes"], queryFn: api.getClientes });
}

export function useNormas(tipo?: "tracao" | "flexao") {
  return useQuery({ queryKey: ["normas", tipo], queryFn: () => api.getNormas(tipo), staleTime: Infinity });
}

export function useRelatorios(params: { cliente_id?: number; ensaio_id?: number } = {}) {
  return useQuery({ queryKey: ["relatorios", params], queryFn: () => api.getRelatorios(params) });
}

export function useUpdateEnsaio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof api.updateEnsaio>[1] }) =>
      api.updateEnsaio(id, body),
    onSuccess: (_d, { id }) => {
      qc.invalidateQueries({ queryKey: ["ensaios"] });
      qc.invalidateQueries({ queryKey: ["ensaio", id] });
      qc.invalidateQueries({ queryKey: ["busca"] });
    },
  });
}

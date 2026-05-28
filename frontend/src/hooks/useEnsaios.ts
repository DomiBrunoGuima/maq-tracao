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

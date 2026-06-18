import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/client";

export function useEnsaiosFlexao() {
  return useQuery({
    queryKey: ["flexao", "ensaios"],
    queryFn: api.getEnsaiosFlexao,
    refetchInterval: 8000,
  });
}

export function useKPIsFlexao(id: number | null) {
  return useQuery({
    queryKey: ["flexao", "kpis", id],
    queryFn: () => api.getKPIsFlexao(id!),
    enabled: id !== null,
  });
}

export function useCurvasFlexao(id: number | null) {
  return useQuery({
    queryKey: ["flexao", "curvas", id],
    queryFn: () => api.getCurvasFlexao(id!),
    enabled: id !== null,
  });
}

export function useDeleteEnsaioFlexao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteEnsaioFlexao,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["flexao", "ensaios"] }),
  });
}

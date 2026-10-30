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

export function useQualidadeFlexao(id: number | null) {
  return useQuery({
    queryKey: ["flexao", "qualidade", id],
    queryFn: () => api.getQualidadeFlexao(id!),
    enabled: id !== null,
  });
}

export function useEnsaioFlexao(id: number | null) {
  return useQuery({
    queryKey: ["flexao", "ensaio", id],
    queryFn: () => api.getEnsaioFlexao(id!),
    enabled: id !== null,
  });
}

export function useUpdateEnsaioFlexao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof api.updateEnsaioFlexao>[1] }) =>
      api.updateEnsaioFlexao(id, body),
    onSuccess: (_d, { id }) => {
      qc.invalidateQueries({ queryKey: ["flexao", "ensaios"] });
      qc.invalidateQueries({ queryKey: ["flexao", "ensaio", id] });
      qc.invalidateQueries({ queryKey: ["flexao", "kpis", id] });
      qc.invalidateQueries({ queryKey: ["busca"] });
      qc.invalidateQueries({ queryKey: ["clientes"] });
    },
  });
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/client";
import type { AppConfig } from "../types";

export function useConfig() {
  return useQuery({ queryKey: ["config"], queryFn: api.getConfig });
}

export function useUpdateConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: AppConfig) => api.updateConfig(config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });
}

export function useFetchFtpCsv() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.fetchFtpCsv,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ensaios"] }),
  });
}

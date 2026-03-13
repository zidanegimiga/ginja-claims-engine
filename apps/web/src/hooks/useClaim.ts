import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchClaim, adjudicateClaim } from "@/lib/queries";
import { ClaimRequest } from "@/types";

export function useClaim(claimId: string) {
  return useQuery({
    queryKey: ["claims", claimId],
    queryFn: () => fetchClaim(claimId),
    enabled: Boolean(claimId),
  });
}

export function useAdjudicate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (claim: ClaimRequest) => adjudicateClaim(claim),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["claims"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

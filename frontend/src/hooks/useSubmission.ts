import { useQuery } from '@tanstack/react-query'
import { getCertificate, getStatus } from '@/api/client'
import type { SubmissionStatus } from '@/types/certificate'

const POLL_INTERVAL_MS = 3_000
const TERMINAL_STATUSES: SubmissionStatus[] = ['COMPLETE', 'FAILED']

export function useSubmissionStatus(submissionId: string | undefined) {
  return useQuery({
    queryKey: ['submission-status', submissionId],
    queryFn: () => getStatus(submissionId!),
    enabled: Boolean(submissionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || TERMINAL_STATUSES.includes(status)) return false
      return POLL_INTERVAL_MS
    },
  })
}

export function useCertificate(submissionId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['certificate', submissionId],
    queryFn: () => getCertificate(submissionId!),
    enabled: Boolean(submissionId) && enabled,
    staleTime: Infinity, // certificate is immutable once issued
  })
}

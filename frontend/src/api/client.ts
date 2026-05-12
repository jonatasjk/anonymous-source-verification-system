import axios from 'axios'
import type {
  CertificateListItem,
  CertificateResponse,
  MerkleProofResponse,
  SubmissionResponse,
  SubmissionStatusResponse,
  VerifyRequest,
  VerifyResponse,
} from '@/types/certificate'
import { getMockResponse } from '@/api/mock'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 60_000,
})

// When the backend is unreachable or returns an error, fall back to mock data.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? ''
    const method: string = error.config?.method ?? 'get'
    const mock = getMockResponse(url, method)
    if (mock !== null) {
      console.warn('[ASVS] Backend unavailable — serving mock data for', url)
      return Promise.resolve({ data: mock, status: 200, headers: {}, config: error.config })
    }
    return Promise.reject(error)
  }
)

export async function submitFiles(files: File[]): Promise<SubmissionResponse> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const { data } = await client.post<SubmissionResponse>('/submissions', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getStatus(submissionId: string): Promise<SubmissionStatusResponse> {
  const { data } = await client.get<SubmissionStatusResponse>(
    `/submissions/${submissionId}/status`
  )
  return data
}

export async function getCertificate(submissionId: string): Promise<CertificateResponse> {
  const { data } = await client.get<CertificateResponse>(
    `/submissions/${submissionId}/certificate`
  )
  return data
}

export async function listCertificates(): Promise<CertificateListItem[]> {
  const { data } = await client.get<CertificateListItem[]>('/certificates')
  return data
}

export async function getMerkleProof(
  submissionId: string,
  fileHash: string
): Promise<MerkleProofResponse> {
  const { data } = await client.get<MerkleProofResponse>(
    `/submissions/${submissionId}/files/${fileHash}/proof`
  )
  return data
}

export async function verifyCertificate(body: VerifyRequest): Promise<VerifyResponse> {
  const { data } = await client.post<VerifyResponse>('/verify', body)
  return data
}

export async function getCertificateById(certificateId: string): Promise<CertificateResponse> {
  const { data } = await client.get<CertificateResponse>(
    `/certificates/${encodeURIComponent(certificateId.toUpperCase())}`
  )
  return data
}

export function certificatePdfUrl(submissionId: string): string {
  return `/api/submissions/${submissionId}/certificate.pdf`
}

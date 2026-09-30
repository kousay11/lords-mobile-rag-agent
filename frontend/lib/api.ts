import axios from 'axios'
import { getToken, removeToken } from './auth'

// Keep browser requests on the frontend origin. Next.js proxies this path to
// Spring Boot through Docker's internal network, avoiding host-port/CORS issues.
const BASE_URL = '/backend-api'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      removeToken()
      if (typeof window !== 'undefined') window.location.replace('/login')
    }
    return Promise.reject(error)
  },
)

export interface AuthResponse { token: string; username: string; role: string; profileRole: string }
export interface LoginRequest { username: string; password: string }
export interface RegisterRequest { username: string; email: string; password: string; profileRole?: string }

export const loginApi = async (data: LoginRequest) =>
  (await apiClient.post<AuthResponse>('/api/auth/login', data)).data
export const registerApi = async (data: RegisterRequest) =>
  (await apiClient.post<AuthResponse>('/api/auth/register', data)).data

export interface BackendHealth {
  status: string
  service: string
  agent: 'online' | 'offline'
  rag: 'online' | 'offline'
  read_only: boolean
}
export const getBackendHealth = async () =>
  (await apiClient.get<BackendHealth>('/api/health')).data

export interface SourceCitation {
  title?: string
  source?: string
  url?: string
  game_version?: string
  version?: string
  score?: number
  content?: string
  [key: string]: unknown
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  confidence?: number | null
  sources?: SourceCitation[]
  intent?: string | null
  gameVersion?: string | null
  generationMode?: string | null
  createdAt: string
}

export interface ChatThread {
  id: string
  title: string
  language?: string | null
  gameVersion?: string | null
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
}

export interface ChatRequest {
  message: string
  threadId?: string
  language?: string
  gameVersion?: string
  playerContext?: Record<string, unknown>
  searchType?: 'hybrid' | 'semantic' | 'keyword'
  topK?: number
}

export interface ChatResponse {
  threadId: string
  messageId: string
  response: string
  intent: string
  language: string
  gameVersion?: string | null
  sources: SourceCitation[]
  confidence: number
  needsClarification: boolean
  searchType: string
  rewrittenQueries: string[]
  generationMode: string
  readOnly: boolean
}

export const sendChatMessage = async (data: ChatRequest) =>
  (await apiClient.post<ChatResponse>('/api/lords-mobile/chat', data)).data
export const listThreads = async () =>
  (await apiClient.get<ChatThread[]>('/api/lords-mobile/threads')).data
export const getThread = async (id: string) =>
  (await apiClient.get<ChatThread>(`/api/lords-mobile/threads/${id}`)).data
export const deleteThread = async (id: string) => {
  await apiClient.delete(`/api/lords-mobile/threads/${id}`)
}
export const saveFeedback = async (
  messageId: string,
  rating: 'HELPFUL' | 'NOT_HELPFUL',
  comment?: string,
) => {
  await apiClient.post(`/api/lords-mobile/messages/${messageId}/feedback`, { rating, comment })
}

export interface PlayerProfile {
  responseLength?: 'short' | 'standard' | 'detailed' | null
  versionMode?: 'unknown' | 'specific' | null
  setupCompleted?: boolean
  language?: string | null
  gameVersion?: string | null
  playerLevel?: string | null
  playStyle?: string | null
  kingdom?: string | null
  additionalContext?: Record<string, unknown> | null
}
export interface ProfileVersionOption {
  value: string
  label: string
  kind: 'review' | 'release' | 'guide' | 'corpus'
  documentCount: number
  needsReviewCount: number
  archivedCount: number
}
export const getProfileVersionOptions = async () =>
  (await apiClient.get<ProfileVersionOption[]>('/api/lords-mobile/profile/version-options')).data
export const getProfileVersions = async () =>
  (await apiClient.get<string[]>('/api/lords-mobile/profile/versions')).data
export const getPlayerProfile = async () =>
  (await apiClient.get<PlayerProfile>('/api/lords-mobile/profile')).data
export const updatePlayerProfile = async (data: PlayerProfile) =>
  (await apiClient.put<PlayerProfile>('/api/lords-mobile/profile', data)).data

export interface UserDto { id: string; username: string; email: string; role: string; createdAt: string }
export const getAdminUsers = async () =>
  (await apiClient.get<UserDto[]>('/api/admin/users')).data
export const updateUserRole = async (id: string, role: string) =>
  (await apiClient.put<UserDto>(`/api/admin/users/${id}/role`, { role })).data
export const deleteUser = async (id: string) => {
  await apiClient.delete(`/api/admin/users/${id}`)
}

export interface KnowledgeDocument {
  id: string
  title: string
  source: string
  url?: string | null
  sourceType: 'official' | 'verified_community' | 'community' | 'reference'
  language: string
  gameVersion: string
  reliability: number
  status: string
  contentHash: string
  topics: string[]
  publishedAt?: string | null
  collectedAt: string
  qdrantChunks: number
  lastError?: string | null
  createdAt: string
  updatedAt: string
}

export interface KnowledgeDocumentRequest {
  title: string
  source: string
  url?: string
  sourceType: KnowledgeDocument['sourceType']
  language: string
  gameVersion: string
  reliability: number
  topics: string[]
  content: string
  publishedAt?: string
}

export const listKnowledgeDocuments = async () =>
  (await apiClient.get<KnowledgeDocument[]>('/api/admin/knowledge/documents')).data
export const createKnowledgeDocument = async (data: KnowledgeDocumentRequest) =>
  (await apiClient.post<KnowledgeDocument>('/api/admin/knowledge/documents', data)).data
export const uploadKnowledgeDocument = async (form: FormData) =>
  (await apiClient.post<KnowledgeDocument>('/api/admin/knowledge/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })).data
export const indexKnowledgeDocument = async (id: string) =>
  (await apiClient.post<KnowledgeDocument>(`/api/admin/knowledge/documents/${id}/index`)).data
export const deleteKnowledgeDocument = async (id: string) => {
  await apiClient.delete(`/api/admin/knowledge/documents/${id}`)
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as Record<string, unknown> | string | undefined
    if (typeof data === 'string' && data.trim()) return data
    if (data && typeof data === 'object') {
      const message = data.message || data.error || data.detail
      if (typeof message === 'string' && message.trim()) return message
    }
    if (!error.response) return 'Impossible de joindre le backend.'
    return `Erreur HTTP ${error.response.status}`
  }
  return error instanceof Error ? error.message : 'Erreur inattendue'
}

import { QueryClient, useQuery } from '@tanstack/react-query'
import { endpoints } from './endpoints'

export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export const useCatalog = () => useQuery({ queryKey: ['catalog'], queryFn: endpoints.catalog, staleTime: Infinity })

export const useParameterSchema = () =>
  useQuery({ queryKey: ['parameter-schema'], queryFn: endpoints.parameterSchema, staleTime: Infinity })

export const useScenarios = () =>
  useQuery({ queryKey: ['scenarios'], queryFn: endpoints.scenarios, staleTime: Infinity })

import { createContext, ReactNode, useContext, useEffect, useState } from 'react'
import { ChatFilters, FilterOptions, getFilterOptions } from '../api/client'

interface FiltersContextValue {
  options: FilterOptions
  selected: ChatFilters
  toggleValue: (field: keyof ChatFilters, value: string) => void
  clearFilters: () => void
}

const EMPTY_OPTIONS: FilterOptions = { cuisine: [], budget: [], location: [], dietary_tags: [] }

const FiltersContext = createContext<FiltersContextValue | null>(null)

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<FilterOptions>(EMPTY_OPTIONS)
  const [selected, setSelected] = useState<ChatFilters>({})

  useEffect(() => {
    getFilterOptions()
      .then(setOptions)
      .catch(() => setOptions(EMPTY_OPTIONS))
  }, [])

  function toggleValue(field: keyof ChatFilters, value: string) {
    setSelected((prev) => {
      const current = prev[field] ?? []
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
      return { ...prev, [field]: next.length > 0 ? next : undefined }
    })
  }

  function clearFilters() {
    setSelected({})
  }

  return (
    <FiltersContext.Provider value={{ options, selected, toggleValue, clearFilters }}>
      {children}
    </FiltersContext.Provider>
  )
}

export function useFilters(): FiltersContextValue {
  const ctx = useContext(FiltersContext)
  if (!ctx) throw new Error('useFilters must be used within a FiltersProvider')
  return ctx
}

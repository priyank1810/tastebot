import { ChatFilters } from '../../api/client'
import { useFilters } from '../../state/FiltersContext'

const FIELDS: { key: keyof ChatFilters; label: string }[] = [
  { key: 'cuisine', label: 'Cuisine' },
  { key: 'budget', label: 'Budget' },
  { key: 'location', label: 'Location' },
  { key: 'dietary_tags', label: 'Dietary' },
]

export function FilterPanel() {
  const { options, selected, toggleValue, clearFilters } = useFilters()

  return (
    <div className="flex flex-col gap-4 p-4 border-t border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between">
        <span className="font-semibold">Filters</span>
        <button onClick={clearFilters} className="text-sm underline">
          Clear
        </button>
      </div>
      {FIELDS.map(({ key, label }) => (
        <div key={key}>
          <div className="text-sm font-medium mb-1">{label}</div>
          <div className="flex flex-wrap gap-1">
            {options[key].map((value) => (
              <button
                key={value}
                onClick={() => toggleValue(key, value)}
                className={`text-xs rounded-full px-2 py-1 border ${
                  (selected[key] ?? []).includes(value)
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'border-slate-300 dark:border-slate-600'
                }`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

import { RestaurantCandidate } from '../../api/client'

export function RestaurantCard({ restaurant }: { restaurant: RestaurantCandidate }) {
  const stars = restaurant.rating ? '★'.repeat(Math.round(restaurant.rating)) : ''
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-800">
      <div className="font-semibold">{restaurant.name}</div>
      <div className="text-sm text-slate-500 dark:text-slate-400">
        {restaurant.cuisine} · {restaurant.budget} · {restaurant.location}
      </div>
      {stars && (
        <div className="text-amber-500 text-sm">
          {stars} {restaurant.rating}
        </div>
      )}
    </div>
  )
}

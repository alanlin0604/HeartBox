/**
 * Activity Icons — switched 2026-05-23 from inline stroke-currentColor
 * SVGs to <img> references at the new act-*.svg artwork set. The new
 * icons are multi-color, so they no longer follow button text color via
 * currentColor — the selected/unselected button state is now communicated
 * through the surrounding pill's background + border, not the icon itself.
 *
 * Keeping the original `{name}Icon` component named exports + the
 * ACTIVITY_ICONS map so callers (NoteForm) don't have to change shape.
 */

const make = (src) => {
  const Cmp = ({ className = 'w-5 h-5' }) => (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      className={`${className} object-contain`}
    />
  )
  Cmp.displayName = src.split('/').pop().replace(/\.svg$/, '')
  return Cmp
}

export const ExerciseIcon = make('/icons/act-exercise.svg')
export const SocialIcon = make('/icons/act-social.svg')
export const WorkIcon = make('/icons/act-work.svg')
export const ReadingIcon = make('/icons/act-reading.svg')
export const TravelIcon = make('/icons/act-travel.svg')
export const MusicIcon = make('/icons/act-music.svg')
export const CookingIcon = make('/icons/act-cooking.svg')
export const MeditationIcon = make('/icons/act-meditation.svg')
export const GamingIcon = make('/icons/act-gaming.svg')
export const ShoppingIcon = make('/icons/act-shopping.svg')
export const MovieIcon = make('/icons/act-movie.svg')
export const NatureIcon = make('/icons/act-nature.svg')

// eslint-disable-next-line react-refresh/only-export-components
export const ACTIVITY_ICONS = {
  exercise: ExerciseIcon,
  social: SocialIcon,
  work: WorkIcon,
  reading: ReadingIcon,
  travel: TravelIcon,
  music: MusicIcon,
  cooking: CookingIcon,
  meditation: MeditationIcon,
  gaming: GamingIcon,
  shopping: ShoppingIcon,
  movie: MovieIcon,
  nature: NatureIcon,
}

export const ActivityIcon = ({ id, className = 'w-5 h-5' }) => {
  const Icon = ACTIVITY_ICONS[id]
  if (!Icon) return null
  return <Icon className={className} />
}

import { useQuery } from '@tanstack/react-query'
import { fetchCompetitions } from '../api/competitions'
import styles from './CompetitionSelector.module.css'

export default function CompetitionSelector({ value, onChange }) {
  const { data: competitions = [], isLoading, isError } = useQuery({
    queryKey: ['competitions'],
    queryFn: fetchCompetitions,
    staleTime: 86400 * 1000,
  })

  const fdComps  = competitions.filter(c => c.source === 'football-data')
  const afComps  = competitions.filter(c => c.source === 'api-football')

  return (
    <div className={styles.wrapper}>
      <label className={styles.label}>Liga</label>
      <select
        className={styles.select}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={isLoading}
      >
        <option value="">— Wybierz ligę —</option>

        {fdComps.length > 0 && (
          <optgroup label="football-data.org">
            {fdComps.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </optgroup>
        )}

        {afComps.length > 0 && (
          <optgroup label="API-Football">
            {afComps.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </optgroup>
        )}
      </select>
      {isError && <span className={styles.error}>Błąd ładowania lig</span>}
    </div>
  )
}

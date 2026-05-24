import styles from './TennisTourSelector.module.css'

const TOURS = [
  { value: '', label: 'Wszystkie' },
  { value: 'atp', label: 'ATP' },
  { value: 'wta', label: 'WTA' },
  { value: 'challenger', label: 'Challenger' },
]

const SURFACES = [
  { value: '', label: 'Każda' },
  { value: 'clay', label: 'Mączka', color: '#c2603a' },
  { value: 'hard', label: 'Hard', color: '#3a7fc2' },
  { value: 'grass', label: 'Trawa', color: '#3ac264' },
]

export default function TennisTourSelector({ tour, surface, onTourChange, onSurfaceChange }) {
  return (
    <div className={styles.wrap}>
      <div className={styles.group}>
        <span className={styles.label}>Tura</span>
        <div className={styles.pills}>
          {TOURS.map((t) => (
            <button
              key={t.value}
              className={`${styles.pill} ${tour === t.value ? styles.active : ''}`}
              onClick={() => onTourChange(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.group}>
        <span className={styles.label}>Nawierzchnia</span>
        <div className={styles.pills}>
          {SURFACES.map((s) => (
            <button
              key={s.value}
              className={`${styles.pill} ${surface === s.value ? styles.active : ''}`}
              style={surface === s.value && s.color ? { background: s.color, borderColor: s.color } : {}}
              onClick={() => onSurfaceChange(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

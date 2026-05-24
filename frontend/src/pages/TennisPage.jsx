import { useState } from 'react'
import TennisTourSelector from '../components/tennis/TennisTourSelector'
import TennisModelBanner from '../components/tennis/TennisModelBanner'
import TennisMatchList from '../components/tennis/TennisMatchList'
import TennisPredictionPanel from '../components/tennis/TennisPredictionPanel'
import styles from './TennisPage.module.css'

export default function TennisPage() {
  const [tour, setTour] = useState('')
  const [surface, setSurface] = useState('')
  const [selectedMatch, setSelectedMatch] = useState(null)

  function handleTourChange(t) {
    setTour(t)
    setSelectedMatch(null)
  }

  function handleSurfaceChange(s) {
    setSurface(s)
    setSelectedMatch(null)
  }

  return (
    <div className={styles.page}>
      <div className={styles.filters}>
        <TennisTourSelector
          tour={tour}
          surface={surface}
          onTourChange={handleTourChange}
          onSurfaceChange={handleSurfaceChange}
        />
      </div>

      <TennisModelBanner />

      <div className={styles.content}>
        <div className={`${styles.panel} ${styles.left}`}>
          <div className={styles.panelTitle}>Nadchodzące mecze</div>
          <TennisMatchList
            tour={tour || undefined}
            surface={surface || undefined}
            selectedMatchId={selectedMatch?.match_id}
            onMatchSelect={setSelectedMatch}
          />
        </div>

        <div className={`${styles.panel} ${styles.right}`}>
          {selectedMatch ? (
            <TennisPredictionPanel
              match={selectedMatch}
              onClose={() => setSelectedMatch(null)}
            />
          ) : (
            <div className={styles.placeholder}>
              <span className={styles.placeholderIcon}>🎾</span>
              <p>Kliknij mecz, aby zobaczyć predykcję</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import CompetitionSelector from './components/CompetitionSelector'
import ModelStatusBanner from './components/ModelStatusBanner'
import MatchList from './components/MatchList'
import PredictionPanel from './components/PredictionPanel'
import styles from './App.module.css'

export default function App() {
  const [competition, setCompetition] = useState('')
  const [selectedMatch, setSelectedMatch] = useState(null)

  function handleCompetitionChange(code) {
    setCompetition(code)
    setSelectedMatch(null)
  }

  function handleMatchSelect(match) {
    setSelectedMatch(match)
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>⚽</span>
          <div>
            <div className={styles.logoTitle}>Winner Predictor</div>
            <div className={styles.logoSub}>AI · Piłka nożna · 1/X/2</div>
          </div>
        </div>
        <CompetitionSelector value={competition} onChange={handleCompetitionChange} />
      </header>

      <ModelStatusBanner competition={competition} />

      <div className={styles.content}>
        <div className={`${styles.panel} ${styles.left}`}>
          <div className={styles.panelTitle}>Nadchodzące mecze</div>
          <MatchList
            competition={competition}
            selectedMatchId={selectedMatch?.id}
            onMatchSelect={handleMatchSelect}
          />
        </div>

        <div className={`${styles.panel} ${styles.right} ${selectedMatch ? styles.visible : ''}`}>
          {selectedMatch ? (
            <PredictionPanel
              match={selectedMatch}
              competition={competition}
              onClose={() => setSelectedMatch(null)}
            />
          ) : (
            <div className={styles.placeholder}>
              <span className={styles.placeholderIcon}>🎯</span>
              <p>Kliknij mecz, aby zobaczyć predykcję</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

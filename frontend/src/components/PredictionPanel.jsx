import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPrediction } from '../api/matches'
import styles from './PredictionPanel.module.css'

function ProbabilityBar({ label, value, color, isPredicted }) {
  const barRef = useRef(null)

  useEffect(() => {
    if (barRef.current) {
      setTimeout(() => {
        barRef.current.style.width = `${value}%`
      }, 50)
    }
  }, [value])

  return (
    <div className={`${styles.barRow} ${isPredicted ? styles.predicted : ''}`}>
      <div className={styles.barLabel}>
        <span className={styles.outcome}>{label}</span>
        {isPredicted && <span className={styles.badge}>Typ</span>}
        <span className={styles.pct}>{value}%</span>
      </div>
      <div className={styles.barTrack}>
        <div
          ref={barRef}
          className={styles.barFill}
          style={{ width: '0%', background: color }}
        />
      </div>
    </div>
  )
}

function FormDots({ points, max = 15 }) {
  const pct = Math.round((points / max) * 100)
  return (
    <span className={styles.formPct} style={{ color: pct > 60 ? '#86efac' : pct > 35 ? '#fde047' : '#fca5a5' }}>
      {points}/{max} pkt
    </span>
  )
}

export default function PredictionPanel({ match, competition, onClose }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['prediction', match.id, competition],
    queryFn: () => fetchPrediction(match.id, competition),
    staleTime: 30 * 60 * 1000,
    enabled: !!match && !!competition,
  })

  const outcomeLabels = { '1': 'Wygrana gospodarzy', X: 'Remis', '2': 'Wygrana gości' }
  const outcomeColors = {
    home: 'var(--accent-green)',
    draw: 'var(--accent-yellow)',
    away: 'var(--accent-red)',
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.matchTitle}>
          <div className={styles.teamBlock}>
            {match.homeTeam.crest && (
              <img src={match.homeTeam.crest} alt="" className={styles.crest}
                onError={(e) => { e.target.style.display = 'none' }} />
            )}
            <span>{match.homeTeam.name}</span>
          </div>
          <span className={styles.vsLabel}>VS</span>
          <div className={`${styles.teamBlock} ${styles.teamRight}`}>
            <span>{match.awayTeam.name}</span>
            {match.awayTeam.crest && (
              <img src={match.awayTeam.crest} alt="" className={styles.crest}
                onError={(e) => { e.target.style.display = 'none' }} />
            )}
          </div>
        </div>
        <button className={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      <div className={styles.body}>
        {isLoading && (
          <div className={styles.loadingWrap}>
            <div className={styles.spinner} />
            <p>Analizuję dane…</p>
          </div>
        )}

        {isError && (
          <div className={styles.errorWrap}>
            <span>⚠</span>
            <p>{error.message}</p>
          </div>
        )}

        {data && (
          <>
            <div className={styles.predictionBox}>
              <div className={styles.predLabel}>Predykcja</div>
              <div className={styles.predValue}>
                {outcomeLabels[data.prediction] || data.prediction}
              </div>
              <div className={styles.confidence}>
                Pewność: <strong>{data.confidence}%</strong>
              </div>
            </div>

            <div className={styles.probSection}>
              <h3 className={styles.sectionTitle}>Prawdopodobieństwa</h3>
              <ProbabilityBar
                label="1 — Gospodarz"
                value={data.probabilities.home}
                color={outcomeColors.home}
                isPredicted={data.prediction === '1'}
              />
              <ProbabilityBar
                label="X — Remis"
                value={data.probabilities.draw}
                color={outcomeColors.draw}
                isPredicted={data.prediction === 'X'}
              />
              <ProbabilityBar
                label="2 — Gość"
                value={data.probabilities.away}
                color={outcomeColors.away}
                isPredicted={data.prediction === '2'}
              />
            </div>

            {data.insights && (
              <div className={styles.insights}>
                <h3 className={styles.sectionTitle}>Statystyki</h3>

                <div className={styles.statsGrid}>
                  <div className={styles.statsCard}>
                    <div className={styles.statsTeam}>Gospodarz</div>
                    <div className={styles.statsRow}>
                      <span>Forma (ost. 5)</span>
                      <FormDots points={data.insights.homeForm.points} />
                    </div>
                    <div className={styles.statsRow}>
                      <span>Bramki</span>
                      <span className={styles.statVal}>
                        {data.insights.homeForm.goalsScored} – {data.insights.homeForm.goalsConceded}
                      </span>
                    </div>
                    <div className={styles.statsRow}>
                      <span>Pozycja</span>
                      <span className={styles.statVal}>{data.insights.homePosition}</span>
                    </div>
                  </div>

                  <div className={styles.statsCard}>
                    <div className={styles.statsTeam}>Gość</div>
                    <div className={styles.statsRow}>
                      <span>Forma (ost. 5)</span>
                      <FormDots points={data.insights.awayForm.points} />
                    </div>
                    <div className={styles.statsRow}>
                      <span>Bramki</span>
                      <span className={styles.statVal}>
                        {data.insights.awayForm.goalsScored} – {data.insights.awayForm.goalsConceded}
                      </span>
                    </div>
                    <div className={styles.statsRow}>
                      <span>Pozycja</span>
                      <span className={styles.statVal}>{data.insights.awayPosition}</span>
                    </div>
                  </div>
                </div>

                <div className={styles.h2h}>
                  <span className={styles.h2hLabel}>H2H</span>
                  <span className={styles.h2hStat} style={{ color: 'var(--accent-green)' }}>
                    {data.insights.h2h.homeWins} W
                  </span>
                  <span className={styles.h2hStat} style={{ color: 'var(--accent-yellow)' }}>
                    {data.insights.h2h.draws} R
                  </span>
                  <span className={styles.h2hStat} style={{ color: 'var(--accent-red)' }}>
                    {data.insights.h2h.awayWins} W
                  </span>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchTennisPrediction } from '../../api/tennis'
import styles from './TennisPredictionPanel.module.css'

function ProbBar({ label, value, color, isHigher }) {
  const barRef = useRef(null)

  useEffect(() => {
    if (barRef.current) {
      setTimeout(() => {
        barRef.current.style.width = `${value}%`
      }, 50)
    }
  }, [value])

  return (
    <div className={`${styles.barRow} ${isHigher ? styles.predicted : ''}`}>
      <div className={styles.barLabel}>
        <span>{label}</span>
        {isHigher && <span className={styles.badge}>Faworyt</span>}
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

function ValueSignal({ signal, match }) {
  if (!signal) return null
  const { recommendation, reason, p1_edge, p2_edge } = signal
  const isBet = recommendation.startsWith('BET')
  const betPlayer = recommendation === 'BET_P1'
    ? match.player_1?.name
    : recommendation === 'BET_P2'
    ? match.player_2?.name
    : null

  return (
    <div className={`${styles.signalBox} ${isBet ? styles.signalBet : styles.signalSkip}`}>
      <div className={styles.signalHeader}>
        <span className={styles.signalIcon}>{isBet ? '✓' : '–'}</span>
        <span className={styles.signalLabel}>
          {isBet ? `BET: ${betPlayer}` : 'SKIP'}
        </span>
        {isBet && <span className={styles.signalEdge}>{reason}</span>}
      </div>

      {(p1_edge !== null || p2_edge !== null) && (
        <div className={styles.edgeGrid}>
          {p1_edge !== null && (
            <div className={styles.edgeItem}>
              <span className={styles.edgeName}>{match.player_1?.name}</span>
              <span className={`${styles.edgeVal} ${p1_edge > 0 ? styles.edgePos : styles.edgeNeg}`}>
                edge: {(p1_edge * 100).toFixed(1)}%
              </span>
            </div>
          )}
          {p2_edge !== null && (
            <div className={styles.edgeItem}>
              <span className={styles.edgeName}>{match.player_2?.name}</span>
              <span className={`${styles.edgeVal} ${p2_edge > 0 ? styles.edgePos : styles.edgeNeg}`}>
                edge: {(p2_edge * 100).toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      )}

      {!match.odds_1 && !match.odds_2 && (
        <p className={styles.noOdds}>Brak kursów — podaj kursy aby zobaczyć sygnał value</p>
      )}
    </div>
  )
}

function FatigueIcon({ backToBack }) {
  return backToBack
    ? <span className={styles.fatigueWarn} title="Grał wczoraj">⚡ back-to-back</span>
    : null
}

export default function TennisPredictionPanel({ match, onClose }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['tennisPrediction', match.match_id],
    queryFn: () => fetchTennisPrediction(match.match_id, match),
    staleTime: 30 * 60 * 1000,
    enabled: !!match,
  })

  const p1Name = match.player_1?.name || 'Zawodnik 1'
  const p2Name = match.player_2?.name || 'Zawodnik 2'

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.matchTitle}>
          <div className={styles.playerBlock}>
            {match.player_1?.rank && <span className={styles.rankTag}>#{match.player_1.rank}</span>}
            <span>{p1Name}</span>
          </div>
          <span className={styles.vsLabel}>VS</span>
          <div className={`${styles.playerBlock} ${styles.playerRight}`}>
            <span>{p2Name}</span>
            {match.player_2?.rank && <span className={styles.rankTag}>#{match.player_2.rank}</span>}
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
            <div className={styles.probSection}>
              <h3 className={styles.sectionTitle}>Prawdopodobieństwo wygranej</h3>
              <ProbBar
                label={p1Name}
                value={data.player_1_win_prob}
                color="var(--accent-green)"
                isHigher={data.player_1_win_prob >= data.player_2_win_prob}
              />
              <ProbBar
                label={p2Name}
                value={data.player_2_win_prob}
                color="var(--accent-red)"
                isHigher={data.player_2_win_prob > data.player_1_win_prob}
              />
            </div>

            <ValueSignal signal={data.signal} match={match} />

            {data.insights && (
              <div className={styles.insights}>
                <h3 className={styles.sectionTitle}>Analiza</h3>

                <div className={styles.statsGrid}>
                  <div className={styles.statsCard}>
                    <div className={styles.statsPlayer}>{p1Name}</div>
                    <div className={styles.statsRow}>
                      <span>Nawierzchnia</span>
                      <span className={styles.statVal}>{data.insights.p1_surface_winrate}%</span>
                    </div>
                    <div className={styles.statsRow}>
                      <span>Forma (ost. 5)</span>
                      <span className={styles.statVal}>{data.insights.p1_form5}%</span>
                    </div>
                    <div className={styles.statsRow}>
                      <span>Mecze / 7 dni</span>
                      <span className={styles.statVal}>{data.insights.p1_fatigue.matches_last7}</span>
                    </div>
                    <FatigueIcon backToBack={data.insights.p1_fatigue.back_to_back} />
                  </div>

                  <div className={styles.statsCard}>
                    <div className={styles.statsPlayer}>{p2Name}</div>
                    <div className={styles.statsRow}>
                      <span>Nawierzchnia</span>
                      <span className={styles.statVal}>{data.insights.p2_surface_winrate}%</span>
                    </div>
                    <div className={styles.statsRow}>
                      <span>Forma (ost. 5)</span>
                      <span className={styles.statVal}>{data.insights.p2_form5}%</span>
                    </div>
                    <div className={styles.statsRow}>
                      <span>Mecze / 7 dni</span>
                      <span className={styles.statVal}>{data.insights.p2_fatigue.matches_last7}</span>
                    </div>
                    <FatigueIcon backToBack={data.insights.p2_fatigue.back_to_back} />
                  </div>
                </div>

                <div className={styles.h2h}>
                  <span className={styles.h2hLabel}>H2H (ta nawierzchnia, ost. 3 lata)</span>
                  <span className={styles.h2hStat} style={{ color: 'var(--accent-green)' }}>
                    {data.insights.h2h.p1_wins} W
                  </span>
                  <span className={styles.h2hStat} style={{ color: 'var(--accent-red)' }}>
                    {data.insights.h2h.p2_wins} W
                  </span>
                  {data.insights.h2h.total === 0 && (
                    <span className={styles.h2hNone}>brak H2H</span>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

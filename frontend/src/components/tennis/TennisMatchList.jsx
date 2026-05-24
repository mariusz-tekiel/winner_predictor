import { useQuery } from '@tanstack/react-query'
import { fetchTennisMatches } from '../../api/tennis'
import styles from './TennisMatchList.module.css'

const SURFACE_COLORS = {
  clay: '#c2603a',
  hard: '#3a7fc2',
  grass: '#3ac264',
}

const TOUR_LABELS = {
  atp: 'ATP',
  wta: 'WTA',
  challenger: 'CH',
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleDateString('pl-PL', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function RankBadge({ rank }) {
  if (!rank) return null
  return <span className={styles.rank}>#{rank}</span>
}

function MatchCard({ match, selected, onClick }) {
  const surfaceColor = SURFACE_COLORS[match.surface] || '#888'
  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ''}`}
      onClick={() => onClick(match)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick(match)}
    >
      <div className={styles.meta}>
        <span className={styles.tour}>{TOUR_LABELS[match.tour] || match.tour}</span>
        <span className={styles.surface} style={{ color: surfaceColor }}>
          ● {match.surface}
        </span>
        <span className={styles.tourney}>{match.tourney_name}</span>
        <span className={styles.date}>{formatDate(match.match_date)}</span>
      </div>

      <div className={styles.players}>
        <div className={styles.player}>
          <RankBadge rank={match.player_1?.rank} />
          <span className={styles.playerName}>{match.player_1?.name || '—'}</span>
          {match.odds_1 && <span className={styles.odds}>{match.odds_1.toFixed(2)}</span>}
        </div>
        <span className={styles.vs}>VS</span>
        <div className={`${styles.player} ${styles.playerRight}`}>
          {match.odds_2 && <span className={styles.odds}>{match.odds_2.toFixed(2)}</span>}
          <span className={styles.playerName}>{match.player_2?.name || '—'}</span>
          <RankBadge rank={match.player_2?.rank} />
        </div>
      </div>

      <div className={styles.round}>{match.round}</div>
    </div>
  )
}

export default function TennisMatchList({ tour, surface, selectedMatchId, onMatchSelect }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['tennisMatches', tour, surface],
    queryFn: () => fetchTennisMatches(tour, surface),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className={styles.loading}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className={styles.skeleton} />
        ))}
      </div>
    )
  }

  if (isError) {
    return <div className={styles.errorMsg}>Błąd: {error.message}</div>
  }

  const matches = data?.matches || []

  if (matches.length === 0) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyIcon}>🎾</span>
        <p>Brak zaplanowanych meczów.</p>
        <p className={styles.emptyHint}>Mecze pojawiają się gdy API zwraca dane na żywo.</p>
      </div>
    )
  }

  return (
    <div className={styles.list}>
      {matches.map((match) => (
        <MatchCard
          key={match.match_id}
          match={match}
          selected={selectedMatchId === match.match_id}
          onClick={onMatchSelect}
        />
      ))}
    </div>
  )
}

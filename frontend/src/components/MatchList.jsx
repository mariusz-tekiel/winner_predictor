import { useQuery } from '@tanstack/react-query'
import { fetchUpcomingMatches } from '../api/matches'
import styles from './MatchList.module.css'

function formatDate(utcDate) {
  const d = new Date(utcDate)
  return d.toLocaleDateString('pl-PL', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function TeamRow({ team, side }) {
  return (
    <div className={`${styles.team} ${side === 'away' ? styles.teamRight : ''}`}>
      {team.crest && (
        <img
          src={team.crest}
          alt={team.shortName}
          className={styles.crest}
          onError={(e) => { e.target.style.display = 'none' }}
        />
      )}
      <span className={styles.teamName}>{team.shortName || team.name}</span>
    </div>
  )
}

function MatchCard({ match, selected, onClick }) {
  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ''}`}
      onClick={() => onClick(match)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick(match)}
    >
      <div className={styles.meta}>
        <span className={styles.matchday}>Kolejka {match.matchday}</span>
        <span className={styles.date}>{formatDate(match.utcDate)}</span>
      </div>
      <div className={styles.teams}>
        <TeamRow team={match.homeTeam} side="home" />
        <span className={styles.vs}>VS</span>
        <TeamRow team={match.awayTeam} side="away" />
      </div>
    </div>
  )
}

export default function MatchList({ competition, selectedMatchId, onMatchSelect }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['upcomingMatches', competition],
    queryFn: () => fetchUpcomingMatches(competition),
    enabled: !!competition,
    staleTime: 5 * 60 * 1000,
  })

  if (!competition) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyIcon}>⚽</span>
        <p>Wybierz ligę, aby zobaczyć nadchodzące mecze.</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className={styles.loading}>
        {Array.from({ length: 6 }).map((_, i) => (
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
        <span className={styles.emptyIcon}>📅</span>
        <p>Brak zaplanowanych meczów w tej lidze.</p>
      </div>
    )
  }

  return (
    <div className={styles.list}>
      {matches.map((match) => (
        <MatchCard
          key={match.id}
          match={match}
          selected={selectedMatchId === match.id}
          onClick={onMatchSelect}
        />
      ))}
    </div>
  )
}

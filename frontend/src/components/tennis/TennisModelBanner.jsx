import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchTennisModelStatus,
  startTennisTraining,
  fetchTennisTrainProgress,
  fetchTennisCsvStatus,
} from '../../api/tennis'
import styles from './TennisModelBanner.module.css'

const DEFAULT_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
const TOURS = ['atp', 'wta', 'challenger']

export default function TennisModelBanner() {
  const queryClient = useQueryClient()
  const [taskId, setTaskId] = useState(null)
  const [progress, setProgress] = useState(null)
  const [training, setTraining] = useState(false)
  const [selectedTour, setSelectedTour] = useState('atp')
  const pollRef = useRef(null)

  const { data: status } = useQuery({
    queryKey: ['tennisModelStatus'],
    queryFn: fetchTennisModelStatus,
    refetchInterval: training ? false : 60000,
  })

  const { data: csvStatus } = useQuery({
    queryKey: ['tennisCsvStatus'],
    queryFn: fetchTennisCsvStatus,
    staleTime: 30000,
  })

  const csvYears = csvStatus?.[selectedTour] || []
  const availableYears = DEFAULT_YEARS.filter((y) => csvYears.includes(y))

  useEffect(() => {
    if (!taskId) return
    pollRef.current = setInterval(async () => {
      try {
        const p = await fetchTennisTrainProgress(taskId)
        setProgress(p)
        if (p.status === 'done' || p.status === 'error') {
          clearInterval(pollRef.current)
          setTaskId(null)
          setTraining(false)
          queryClient.invalidateQueries({ queryKey: ['tennisModelStatus'] })
        }
      } catch {
        clearInterval(pollRef.current)
        setTraining(false)
      }
    }, 3000)
    return () => clearInterval(pollRef.current)
  }, [taskId])

  async function handleTrain() {
    if (availableYears.length === 0) return
    setTraining(true)
    setProgress({ status: 'queued' })
    try {
      const res = await startTennisTraining(selectedTour, availableYears)
      setTaskId(res.taskId)
    } catch (e) {
      setTraining(false)
      alert('Błąd trenowania: ' + e.message)
    }
  }

  const isTrained = status?.trained
  const progressStatus = progress?.status

  return (
    <div className={`${styles.banner} ${isTrained && !training ? styles.ok : styles.warn}`}>
      <div className={styles.left}>
        {training ? (
          <>
            <span className={styles.spinner} />
            <span>
              {progressStatus === 'fetching' && 'Wczytywanie CSV…'}
              {progressStatus === 'building_features' &&
                `Budowanie cech: ${progress.step}/${progress.total}`}
              {progressStatus === 'training' && 'Trenowanie modelu…'}
              {progressStatus === 'queued' && 'Oczekiwanie…'}
            </span>
          </>
        ) : isTrained ? (
          <>
            <span className={styles.dot} />
            <span>
              Model tenis wytrenowany —{' '}
              <strong>{((status.accuracy || 0) * 100).toFixed(1)}%</strong> acc |{' '}
              Brier: <strong>{status.brier_score}</strong> |{' '}
              {status.tour?.toUpperCase()} {status.years?.join(',')}
            </span>
          </>
        ) : (
          <>
            <span className={styles.dotWarn} />
            <span>
              Model tenisowy nie jest wytrenowany.
              {csvYears.length === 0
                ? ' Pobierz CSV: python scripts/download_tennis_csv.py'
                : ` ${csvYears.length} lat CSV dostępnych dla ${selectedTour.toUpperCase()}.`}
            </span>
          </>
        )}

        {progress?.status === 'done' && (
          <span className={styles.badge}>
            Gotowe! {progress.accuracy}% | Brier: {progress.brier_score}
          </span>
        )}
        {progress?.status === 'error' && (
          <span className={styles.error}>Błąd: {progress.message}</span>
        )}
      </div>

      <div className={styles.right}>
        <select
          className={styles.select}
          value={selectedTour}
          onChange={(e) => setSelectedTour(e.target.value)}
          disabled={training}
        >
          {TOURS.map((t) => (
            <option key={t} value={t}>{t.toUpperCase()}</option>
          ))}
        </select>

        <button
          className={styles.btn}
          onClick={handleTrain}
          disabled={training || availableYears.length === 0}
          title={availableYears.length === 0 ? 'Brak plików CSV. Pobierz skryptem.' : ''}
        >
          {training ? 'Trenowanie…' : isTrained ? 'Przetrenuj' : 'Trenuj model'}
        </button>
      </div>
    </div>
  )
}

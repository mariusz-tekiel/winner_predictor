import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchModelStatus, startTraining, fetchTrainProgress } from '../api/model'
import styles from './ModelStatusBanner.module.css'

export default function ModelStatusBanner({ competition }) {
  const queryClient = useQueryClient()
  const [taskId, setTaskId] = useState(null)
  const [progress, setProgress] = useState(null)
  const [training, setTraining] = useState(false)
  const pollRef = useRef(null)

  const { data: status, isLoading } = useQuery({
    queryKey: ['modelStatus'],
    queryFn: fetchModelStatus,
    refetchInterval: training ? false : 60000,
  })

  useEffect(() => {
    if (!taskId) return

    pollRef.current = setInterval(async () => {
      try {
        const p = await fetchTrainProgress(taskId)
        setProgress(p)
        if (p.status === 'done' || p.status === 'error') {
          clearInterval(pollRef.current)
          setTaskId(null)
          setTraining(false)
          queryClient.invalidateQueries({ queryKey: ['modelStatus'] })
        }
      } catch {
        clearInterval(pollRef.current)
        setTraining(false)
      }
    }, 3000)

    return () => clearInterval(pollRef.current)
  }, [taskId])

  async function handleTrain() {
    if (!competition) return
    setTraining(true)
    setProgress({ status: 'queued' })
    try {
      const res = await startTraining(competition, '')
      setTaskId(res.taskId)
    } catch (e) {
      setTraining(false)
      alert('Błąd trenowania: ' + e.message)
    }
  }

  if (isLoading) return null

  const isTrained = status?.trained
  const progressStatus = progress?.status

  return (
    <div className={`${styles.banner} ${isTrained && !training ? styles.ok : styles.warn}`}>
      <div className={styles.left}>
        {training ? (
          <>
            <span className={styles.spinner} />
            <span>
              {progressStatus === 'fetching' && 'Pobieranie danych…'}
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
              Model wytrenowany — dokładność:{' '}
              <strong>{(status.accuracy * 100).toFixed(1)}%</strong> |{' '}
              {status.sampleCount} meczów | {status.competition}
            </span>
          </>
        ) : (
          <>
            <span className={styles.dotWarn} />
            <span>Model nie jest wytrenowany. Wybierz ligę i kliknij "Trenuj".</span>
          </>
        )}

        {progress?.status === 'done' && (
          <span className={styles.badge}>
            Gotowe! Dokładność: {progress.accuracy}%
          </span>
        )}
        {progress?.status === 'error' && (
          <span className={styles.error}>Błąd: {progress.message}</span>
        )}
      </div>

      <button
        className={styles.btn}
        onClick={handleTrain}
        disabled={training || !competition}
        title={!competition ? 'Najpierw wybierz ligę' : ''}
      >
        {training ? 'Trenowanie…' : isTrained ? 'Przetrenuj' : 'Trenuj model'}
      </button>
    </div>
  )
}

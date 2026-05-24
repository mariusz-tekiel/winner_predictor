import client from './client'

export async function fetchTennisTours() {
  const res = await client.get('/tennis/tours')
  return res.data
}

export async function fetchTennisMatches(tour, surface) {
  const params = {}
  if (tour) params.tour = tour
  if (surface) params.surface = surface
  const res = await client.get('/tennis/matches/upcoming', { params })
  return res.data
}

export async function fetchTennisPrediction(matchId, match) {
  const params = {
    tour: match.tour,
    surface: match.surface,
    player_1_name: match.player_1.name,
    player_2_name: match.player_2.name,
    player_1_rank: match.player_1.rank,
    player_2_rank: match.player_2.rank,
    round: match.round,
    tourney_name: match.tourney_name,
  }
  if (match.odds_1) params.odds_1 = match.odds_1
  if (match.odds_2) params.odds_2 = match.odds_2
  const res = await client.get(`/tennis/matches/${matchId}/predict`, { params })
  return res.data
}

export async function fetchTennisModelStatus() {
  const res = await client.get('/tennis/model/status')
  return res.data
}

export async function startTennisTraining(tour, years) {
  const res = await client.post('/tennis/model/train', null, {
    params: { tour, years: years.join(',') },
  })
  return res.data
}

export async function fetchTennisTrainProgress(taskId) {
  const res = await client.get(`/tennis/model/train/${taskId}`)
  return res.data
}

export async function fetchTennisCsvStatus() {
  const res = await client.get('/tennis/csv/status')
  return res.data
}

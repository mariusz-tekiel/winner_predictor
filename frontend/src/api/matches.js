import client from './client'

export async function fetchUpcomingMatches(competition) {
  const res = await client.get('/matches/upcoming', { params: { competition } })
  return res.data
}

export async function fetchPrediction(matchId, competition) {
  const res = await client.get(`/matches/${matchId}/predict`, {
    params: { competition },
  })
  return res.data
}

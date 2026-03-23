import client from './client'

export async function fetchCompetitions() {
  const res = await client.get('/competitions')
  return res.data.competitions
}

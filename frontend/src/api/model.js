import client from './client'

export async function fetchModelStatus() {
  const res = await client.get('/model/status')
  return res.data
}

export async function startTraining(competition, seasons = '') {
  const res = await client.post('/model/train', null, {
    params: { competition, seasons },
  })
  return res.data
}

export async function fetchTrainProgress(taskId) {
  const res = await client.get(`/model/train/${taskId}`)
  return res.data
}

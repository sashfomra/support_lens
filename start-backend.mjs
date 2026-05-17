/**
 * start-backend.mjs - starts the FastAPI backend from the hackathon root
 */
import { spawn } from 'child_process'
import path from 'path'

const backendDir = path.join(process.cwd(), 'support-lens', 'backend')

console.log('Starting SupportLens backend...')
console.log('Directory:', backendDir)

const proc = spawn('python', ['-m', 'uvicorn', 'main:app', '--reload', '--port', '8000'], {
  cwd: backendDir,
  stdio: 'inherit',
  shell: true,
})

proc.on('error', (err) => {
  console.error('Failed to start:', err.message)
})

process.on('SIGINT', () => {
  proc.kill()
  process.exit(0)
})

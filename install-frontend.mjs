/**
 * install-frontend.mjs
 * Run from c:\Users\Relanto\Downloads\hackathon with: node install-frontend.mjs
 */
import { execSync } from 'child_process'
import { existsSync } from 'fs'
import path from 'path'

const frontendDir = path.join(process.cwd(), 'support-lens', 'frontend')

console.log('Installing SupportLens frontend dependencies...')
console.log('Directory:', frontendDir)

if (!existsSync(frontendDir)) {
  console.error('Frontend directory not found:', frontendDir)
  process.exit(1)
}

try {
  execSync('npm install', { cwd: frontendDir, stdio: 'inherit' })
  console.log('\n✓ Frontend npm install complete!')
  console.log('\nTo start the frontend, run:')
  console.log('  cd support-lens/frontend && npm run dev')
} catch (e) {
  console.error('npm install failed:', e.message)
  process.exit(1)
}

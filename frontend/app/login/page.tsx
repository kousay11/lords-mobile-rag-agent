import LoginForm from '@/components/auth/LoginForm'
import { AtmosphericBackground } from '@/components/layout/atmospheric-background'

export const metadata = { title: 'Connexion — Kingdom Sage' }
export default function LoginPage() { return <main className="relative flex min-h-screen items-center justify-center px-4 py-16"><AtmosphericBackground /><LoginForm /></main> }

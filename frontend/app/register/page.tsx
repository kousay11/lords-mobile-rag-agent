import RegisterForm from '@/components/auth/RegisterForm'
import { AtmosphericBackground } from '@/components/layout/atmospheric-background'

export const metadata = { title: 'Créer un compte — Kingdom Sage' }
export default function RegisterPage() { return <main className="relative flex min-h-screen items-center justify-center px-4 py-16"><AtmosphericBackground /><RegisterForm /></main> }

import { NavLink, Outlet } from 'react-router-dom'
import { ShieldCheck, Upload, Award } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Evidence Verification', icon: Upload, end: true },
  { to: '/certificates', label: 'Certificates', icon: Award, end: false },
]

export default function Layout() {
  return (
    <div className="flex flex-col min-h-screen bg-surface text-ink">
      {/* Header */}
      <header className="bg-brand flex items-center gap-3 px-6 h-14 flex-shrink-0 shadow-sm">
        <ShieldCheck className="w-6 h-6 text-white/90" />
        <span className="font-bold tracking-tight text-white text-lg leading-none">ASVS</span>
        <span className="text-white/50 text-sm hidden sm:block leading-none">
          Anonymous Source Verification System
        </span>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="w-56 bg-surface-card border-r border-surface-border flex-shrink-0 flex flex-col py-3 gap-0.5">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand text-white'
                    : 'text-ink/60 hover:text-ink hover:bg-surface-border/40',
                ].join(' ')
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Main content */}
        <main className="flex-1 overflow-auto flex flex-col">
          <Outlet />
        </main>
      </div>

      {/* Footer */}
      <footer className="h-9 bg-surface-card border-t border-surface-border flex items-center justify-center flex-shrink-0">
        <span className="text-ink/40 text-xs">Developed by Jônatas Kirsch</span>
      </footer>
    </div>
  )
}

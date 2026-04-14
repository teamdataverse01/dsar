interface Props { children: React.ReactNode; title?: string }

export default function Layout({ children, title }: Props) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-brand-900 text-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center font-bold text-sm">DV</div>
          <span className="font-semibold text-lg">DataVerse DSAR Portal</span>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-8">
        {title && <h1 className="text-2xl font-bold text-gray-900 mb-6">{title}</h1>}
        {children}
      </main>
    </div>
  )
}

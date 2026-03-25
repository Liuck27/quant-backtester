export default function TopBar() {
  return (
    <header className="bg-background/80 backdrop-blur-xl sticky top-0 z-40 w-full flex justify-between items-center px-8 h-16">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-secondary/10 px-2 py-0.5 rounded border border-secondary/20">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
          <span className="text-[10px] font-bold text-secondary tracking-tight">SYSTEM ONLINE</span>
        </div>
      </div>
      <div className="flex items-center gap-4 text-outline">
        <button className="hover:text-white transition-colors relative">
          <span className="material-symbols-outlined text-[22px]">notifications</span>
        </button>
        <button className="hover:text-white transition-colors">
          <span className="material-symbols-outlined text-[22px]">account_circle</span>
        </button>
      </div>
    </header>
  )
}

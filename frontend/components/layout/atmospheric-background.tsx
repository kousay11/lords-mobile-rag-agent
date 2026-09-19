export function AtmosphericBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 stone-texture" />
      <div className="absolute -left-40 top-10 h-[32rem] w-[32rem] rounded-full bg-secondary/15 blur-[120px]" />
      <div className="absolute -right-40 top-1/4 h-[28rem] w-[28rem] rounded-full bg-primary/10 blur-[120px]" />
      <div className="absolute inset-x-[-10%] bottom-[-10%] h-[42%] animate-drift bg-[radial-gradient(ellipse_at_center,rgba(173,167,148,.09),transparent_65%)] blur-2xl" />
      <div className="absolute inset-0 vignette" />
    </div>
  )
}

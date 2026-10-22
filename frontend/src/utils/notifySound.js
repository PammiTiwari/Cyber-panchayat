// Short synthesized beep via the Web Audio API — no binary audio asset to
// source, host, or embed. Reused wherever a new-notification chime is needed.
//
// Browsers refuse to run an AudioContext until the page has had at least one
// real user gesture (click/tap/keypress) — one created purely from a
// background timer (like the topbar's polling) stays "suspended" and never
// makes a sound. unlockAudio() resumes it in response to a genuine gesture;
// playNotifySound() also tries to resume defensively in case unlock hasn't
// run yet.
let audioCtx = null

function getCtx() {
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
  return audioCtx
}

export function unlockAudio() {
  try {
    const ctx = getCtx()
    if (ctx.state === "suspended") ctx.resume()
  } catch {
    // No Web Audio support — nothing to unlock.
  }
}

export function playNotifySound() {
  try {
    const ctx = getCtx()
    if (ctx.state === "suspended") ctx.resume()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = "sine"
    osc.frequency.value = 880
    gain.gain.setValueAtTime(0.0001, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.01)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.3)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.3)
  } catch {
    // Browsers block audio without a prior user gesture — fine to no-op.
  }
}

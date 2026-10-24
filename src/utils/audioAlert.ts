/**
 * In-Cab Driver Audio Warning Subsystem
 *
 * Provides immediate acoustic warnings (beeps/alarms) using the standard Web Audio API.
 * Synthesizes warning tones client-side with zero external assets, ensuring zero network
 * latency and 100% offline reliability.
 *
 * Patterns:
 * - 'critical': continuous repeating high-urgency wake-up buzzer alarm for eyes closed,
 *   drowsiness, phone use, and distraction until the condition resolves.
 * - 'warning': medium attention chime.
 * - 'test': confirmation tones to verify speaker setup.
 */

let audioCtx: AudioContext | null = null;
let lastPlayedAt = 0;
const MIN_INTERVAL_MS = 1200;

const MUTE_STORAGE_KEY = 'fleetguard_in_cab_audio_muted';
const VOLUME_STORAGE_KEY = 'fleetguard_in_cab_audio_volume';

let continuousAlarmInterval: ReturnType<typeof setInterval> | null = null;
let currentAlarmReason: string | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

export function isAudioMuted(): boolean {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(MUTE_STORAGE_KEY) === 'true';
}

export function setAudioMuted(muted: boolean): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(MUTE_STORAGE_KEY, muted ? 'true' : 'false');
  if (muted) {
    stopContinuousAlarm();
  }
  window.dispatchEvent(new CustomEvent('fleetguard_audio_settings_changed'));
}

export function getAudioVolume(): number {
  if (typeof window === 'undefined') return 0.85;
  const stored = window.localStorage.getItem(VOLUME_STORAGE_KEY);
  if (stored) {
    const val = parseFloat(stored);
    if (!isNaN(val) && val >= 0 && val <= 1) return val;
  }
  return 0.85;
}

export function setAudioVolume(volume: number): void {
  if (typeof window === 'undefined') return;
  const clamped = Math.max(0.05, Math.min(1.0, volume));
  window.localStorage.setItem(VOLUME_STORAGE_KEY, clamped.toString());
  window.dispatchEvent(new CustomEvent('fleetguard_audio_settings_changed'));
}

/**
 * Emits a single sharp wake-up buzzer double-pulse.
 */
function emitBuzzerPulse(ctx: AudioContext, masterVol: number) {
  const startTime = ctx.currentTime;
  const pulses = [
    { offset: 0, freq: 1050, dur: 0.10 },
    { offset: 0.13, freq: 1400, dur: 0.14 },
  ];

  pulses.forEach(({ offset, freq, dur }) => {
    const osc = ctx.createOscillator();
    const pulseGain = ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(freq, startTime + offset);
    osc.frequency.exponentialRampToValueAtTime(freq + 150, startTime + offset + dur);

    pulseGain.gain.setValueAtTime(0.01, startTime + offset);
    pulseGain.gain.exponentialRampToValueAtTime(0.95 * masterVol, startTime + offset + 0.02);
    pulseGain.gain.exponentialRampToValueAtTime(0.01, startTime + offset + dur);

    osc.connect(pulseGain);
    pulseGain.connect(ctx.destination);

    osc.start(startTime + offset);
    osc.stop(startTime + offset + dur + 0.01);
  });
}

/**
 * Starts a relentless, continuous in-cab buzzer alarm loop that keeps beeping
 * until stopContinuousAlarm() is explicitly called (e.g. driver opens eyes / wakes up,
 * stops using phone, or looks back at the road).
 */
export function startContinuousAlarm(reason: string = 'eyes_closed'): void {
  if (isAudioMuted()) return;
  currentAlarmReason = reason;

  if (continuousAlarmInterval !== null) {
    // Already beeping in an active loop
    return;
  }

  const ctx = getAudioContext();
  if (!ctx) return;

  const masterVol = getAudioVolume();
  // Play immediately
  emitBuzzerPulse(ctx, masterVol);

  // Pulse continuously every 350ms without stopping!
  continuousAlarmInterval = setInterval(() => {
    if (isAudioMuted()) {
      stopContinuousAlarm();
      return;
    }
    const currentCtx = getAudioContext();
    if (!currentCtx) return;
    const vol = getAudioVolume();
    emitBuzzerPulse(currentCtx, vol);
  }, 350);
}

/**
 * Instantly stops the continuous alarm and restores cab silence.
 */
export function stopContinuousAlarm(): void {
  if (continuousAlarmInterval !== null) {
    clearInterval(continuousAlarmInterval);
    continuousAlarmInterval = null;
  }
  currentAlarmReason = null;
}

export function isContinuousAlarmActive(): boolean {
  return continuousAlarmInterval !== null;
}

export function getCurrentAlarmReason(): string | null {
  return currentAlarmReason;
}

export function playImmediateDriverWarning(
  type: 'critical' | 'warning' | 'test' = 'critical',
  force: boolean = false
): boolean {
  if (isAudioMuted() && !force) {
    return false;
  }

  const now = Date.now();
  if (!force && now - lastPlayedAt < MIN_INTERVAL_MS) {
    return false;
  }
  lastPlayedAt = now;

  const ctx = getAudioContext();
  if (!ctx) return false;

  const masterVol = getAudioVolume();

  if (type === 'critical') {
    emitBuzzerPulse(ctx, masterVol);
    return true;
  }

  const startTime = ctx.currentTime;

  if (type === 'warning') {
    // 2 medium sine chimes (650Hz)
    const pulses = [0, 0.2];
    pulses.forEach((offset) => {
      const osc = ctx.createOscillator();
      const pulseGain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(650, startTime + offset);

      pulseGain.gain.setValueAtTime(0.01, startTime + offset);
      pulseGain.gain.exponentialRampToValueAtTime(0.6 * masterVol, startTime + offset + 0.03);
      pulseGain.gain.exponentialRampToValueAtTime(0.01, startTime + offset + 0.14);

      osc.connect(pulseGain);
      pulseGain.connect(ctx.destination);

      osc.start(startTime + offset);
      osc.stop(startTime + offset + 0.15);
    });
    return true;
  }

  // 'test' tone: clean confirmation double beep
  const osc1 = ctx.createOscillator();
  const osc2 = ctx.createOscillator();
  const g1 = ctx.createGain();
  const g2 = ctx.createGain();

  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(750, startTime);
  g1.gain.setValueAtTime(0.5 * masterVol, startTime);
  g1.gain.exponentialRampToValueAtTime(0.01, startTime + 0.1);
  osc1.connect(g1);
  g1.connect(ctx.destination);
  osc1.start(startTime);
  osc1.stop(startTime + 0.11);

  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(1000, startTime + 0.14);
  g2.gain.setValueAtTime(0.6 * masterVol, startTime + 0.14);
  g2.gain.exponentialRampToValueAtTime(0.01, startTime + 0.28);
  osc2.connect(g2);
  g2.connect(ctx.destination);
  osc2.start(startTime + 0.14);
  osc2.stop(startTime + 0.29);

  return true;
}

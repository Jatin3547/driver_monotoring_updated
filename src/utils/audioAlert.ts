/**
 * In-Cab Driver Audio Warning Subsystem
 *
 * Provides immediate acoustic warnings (beeps/alarms) using the standard Web Audio API.
 * Synthesizes warning tones client-side with zero external assets, ensuring zero network
 * latency and 100% offline reliability.
 *
 * Patterns:
 * - 'critical': 3 sharp urgent square/sine pulses (950Hz) for drowsiness, eyes closed, phone usage.
 * - 'warning': 2 medium attention chimes (650Hz) for yawning, head distraction.
 * - 'test': 2 confirmation tones to verify speaker setup.
 */

let audioCtx: AudioContext | null = null;
let lastPlayedAt = 0;
const MIN_INTERVAL_MS = 3500; // prevent overlapping ear fatigue while maintaining fast response

const MUTE_STORAGE_KEY = 'fleetguard_in_cab_audio_muted';
const VOLUME_STORAGE_KEY = 'fleetguard_in_cab_audio_volume';

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
  window.dispatchEvent(new CustomEvent('fleetguard_audio_settings_changed'));
}

export function getAudioVolume(): number {
  if (typeof window === 'undefined') return 0.75;
  const stored = window.localStorage.getItem(VOLUME_STORAGE_KEY);
  if (stored) {
    const val = parseFloat(stored);
    if (!isNaN(val) && val >= 0 && val <= 1) return val;
  }
  return 0.75;
}

export function setAudioVolume(volume: number): void {
  if (typeof window === 'undefined') return;
  const clamped = Math.max(0.05, Math.min(1.0, volume));
  window.localStorage.setItem(VOLUME_STORAGE_KEY, clamped.toString());
  window.dispatchEvent(new CustomEvent('fleetguard_audio_settings_changed'));
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
  const gainNode = ctx.createGain();
  gainNode.gain.setValueAtTime(masterVol, ctx.currentTime);
  gainNode.connect(ctx.destination);

  const startTime = ctx.currentTime;

  if (type === 'critical') {
    // 3 rapid, loud 950Hz square-wave pulses with high urgency
    const pulses = [0, 0.16, 0.32];
    pulses.forEach((offset) => {
      const osc = ctx.createOscillator();
      const pulseGain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(950, startTime + offset);
      osc.frequency.exponentialRampToValueAtTime(1100, startTime + offset + 0.11);

      pulseGain.gain.setValueAtTime(0.01, startTime + offset);
      pulseGain.gain.exponentialRampToValueAtTime(0.85 * masterVol, startTime + offset + 0.02);
      pulseGain.gain.exponentialRampToValueAtTime(0.01, startTime + offset + 0.11);

      osc.connect(pulseGain);
      pulseGain.connect(gainNode);

      osc.start(startTime + offset);
      osc.stop(startTime + offset + 0.12);
    });
    return true;
  }

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
      pulseGain.connect(gainNode);

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
  g1.connect(gainNode);
  osc1.start(startTime);
  osc1.stop(startTime + 0.11);

  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(1000, startTime + 0.14);
  g2.gain.setValueAtTime(0.6 * masterVol, startTime + 0.14);
  g2.gain.exponentialRampToValueAtTime(0.01, startTime + 0.28);
  osc2.connect(g2);
  g2.connect(gainNode);
  osc2.start(startTime + 0.14);
  osc2.stop(startTime + 0.29);

  return true;
}

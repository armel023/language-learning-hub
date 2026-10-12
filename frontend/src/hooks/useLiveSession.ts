import { useCallback, useEffect, useRef, useState } from "react";

import { liveSessionUrl } from "../api/sprechen";
import type { TranscriptTurn } from "../types/api";

export type LiveStatus = "idle" | "connecting" | "live" | "ending" | "ended" | "error";

export interface LiveCaption extends TranscriptTurn {
  index: number;
}

// Runs on the audio thread: hands each block of microphone samples to the main thread.
const CAPTURE_WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) this.port.postMessage(channel.slice(0));
    return true;
  }
}
registerProcessor("pcm-capture", PcmCapture);
`;

const SEND_EVERY_MS = 100;

function toPcm16(samples: Float32Array, fromRate: number, toRate: number): ArrayBuffer {
  const length = Math.floor((samples.length * toRate) / fromRate);
  const out = new Int16Array(length);
  const step = fromRate / toRate;
  for (let i = 0; i < length; i++) {
    // Average the source samples that fall into this output sample (cheap low-pass + decimate).
    const start = Math.floor(i * step);
    const end = Math.min(samples.length, Math.floor((i + 1) * step)) || start + 1;
    let sum = 0;
    for (let j = start; j < end; j++) sum += samples[j];
    const value = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    out[i] = value < 0 ? value * 0x8000 : value * 0x7fff;
  }
  return out.buffer;
}

/**
 * A live voice conversation with the AI partner over the backend's WebSocket: streams the
 * microphone as 16-bit PCM, plays the partner's audio gaplessly, shows captions for both sides,
 * and stops the partner's audio as soon as the candidate starts talking.
 */
export function useLiveSession(exerciseId: string | null) {
  const [status, setStatusState] = useState<LiveStatus>("idle");
  const statusRef = useRef<LiveStatus>("idle");
  const setStatus = (next: LiveStatus) => {
    statusRef.current = next;
    setStatusState(next);
  };
  const [captions, setCaptions] = useState<LiveCaption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [maxSeconds, setMaxSeconds] = useState(0);
  const [partnerSpeaking, setPartnerSpeaking] = useState(false);

  const ws = useRef<WebSocket | null>(null);
  const audio = useRef<{
    context: AudioContext;
    stream: MediaStream;
    playheadTime: number;
    sources: Set<AudioBufferSourceNode>;
    outputRate: number;
  } | null>(null);
  const timers = useRef<number[]>([]);

  const cleanup = useCallback(() => {
    timers.current.forEach((t) => window.clearInterval(t));
    timers.current = [];
    if (audio.current) {
      audio.current.sources.forEach((s) => s.stop());
      audio.current.stream.getTracks().forEach((t) => t.stop());
      audio.current.context.close().catch(() => undefined);
      audio.current = null;
    }
    setPartnerSpeaking(false);
  }, []);

  useEffect(() => () => {
    ws.current?.close();
    cleanup();
  }, [cleanup]);

  const stopPlayback = () => {
    const a = audio.current;
    if (!a) return;
    a.sources.forEach((s) => s.stop());
    a.sources.clear();
    a.playheadTime = a.context.currentTime;
  };

  const playChunk = (data: ArrayBuffer) => {
    const a = audio.current;
    if (!a || data.byteLength < 2) return;
    const pcm = new Int16Array(data);
    const buffer = a.context.createBuffer(1, pcm.length, a.outputRate);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) channel[i] = pcm[i] / 0x8000;
    const source = a.context.createBufferSource();
    source.buffer = buffer;
    source.connect(a.context.destination);
    const startAt = Math.max(a.context.currentTime + 0.05, a.playheadTime);
    source.start(startAt);
    a.playheadTime = startAt + buffer.duration;
    a.sources.add(source);
    source.onended = () => a.sources.delete(source);
  };

  const start = useCallback(async () => {
    if (!exerciseId) return;
    setError(null);
    setCaptions([]);
    setAttemptId(null);
    setElapsed(0);
    setStatus("connecting");
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          "The microphone needs a secure page. Open the app over HTTPS (Tailscale address) or via localhost on this computer.",
        );
      }
      // Created inside the click handler so mobile browsers allow audio playback.
      const context = new AudioContext();
      await context.resume();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      audio.current = { context, stream, playheadTime: 0, sources: new Set(), outputRate: 24000 };

      const socket = new WebSocket(liveSessionUrl(exerciseId));
      socket.binaryType = "arraybuffer";
      ws.current = socket;

      socket.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
          playChunk(event.data);
          return;
        }
        const message = JSON.parse(event.data);
        if (message.type === "ready") {
          audio.current!.outputRate = message.output_rate;
          setMaxSeconds(message.max_seconds);
          await startMicrophone(message.input_rate);
          setStatus("live");
          const startedAt = Date.now();
          timers.current.push(window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 500));
          timers.current.push(window.setInterval(() => {
            const a = audio.current;
            setPartnerSpeaking(!!a && a.playheadTime > a.context.currentTime + 0.05);
          }, 150));
        } else if (message.type === "transcript") {
          setCaptions((prev) => {
            const next = prev.filter((c) => c.index !== message.index);
            next.push({ index: message.index, role: message.speaker, text: message.text });
            return next.sort((x, y) => x.index - y.index);
          });
        } else if (message.type === "interrupted") {
          stopPlayback();
        } else if (message.type === "ended") {
          setAttemptId(message.attempt_id);
          if (!message.attempt_id) setError(message.error ?? "Nothing was recorded, so there is no feedback.");
          setStatus("ended");
          cleanup();
        } else if (message.type === "error") {
          setError(message.message);
          setStatus("error");
          cleanup();
        }
      };
      socket.onclose = () => {
        if (statusRef.current !== "ended" && statusRef.current !== "error") {
          setError("The connection closed unexpectedly. Please try again.");
          setStatus("error");
        }
        cleanup();
      };
      socket.onerror = () => setError("Lost the connection to the server.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the conversation.");
      setStatus("error");
      cleanup();
    }
  }, [exerciseId, cleanup]);

  const startMicrophone = async (inputRate: number) => {
    const a = audio.current!;
    const workletUrl = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: "application/javascript" }));
    await a.context.audioWorklet.addModule(workletUrl);
    URL.revokeObjectURL(workletUrl);
    const source = a.context.createMediaStreamSource(a.stream);
    const node = new AudioWorkletNode(a.context, "pcm-capture");
    // Keep the node pulling audio without playing the microphone back (a muted path to output).
    const mute = a.context.createGain();
    mute.gain.value = 0;
    source.connect(node).connect(mute).connect(a.context.destination);

    let pending: Float32Array[] = [];
    node.port.onmessage = (event: MessageEvent<Float32Array>) => pending.push(event.data);
    timers.current.push(window.setInterval(() => {
      if (!pending.length || ws.current?.readyState !== WebSocket.OPEN) return;
      const total = pending.reduce((n, p) => n + p.length, 0);
      const joined = new Float32Array(total);
      let offset = 0;
      for (const p of pending) {
        joined.set(p, offset);
        offset += p.length;
      }
      pending = [];
      ws.current.send(toPcm16(joined, a.context.sampleRate, inputRate));
    }, SEND_EVERY_MS));
  };

  const stop = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "stop" }));
      setStatus("ending");
    }
    // Stop sending microphone audio right away; the server saves the transcript and replies "ended".
    audio.current?.stream.getTracks().forEach((t) => t.stop());
    stopPlayback();
  }, []);

  return { status, captions, error, attemptId, elapsed, maxSeconds, partnerSpeaking, start, stop };
}

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

// Same shape as lucide's "route" icon (the one used in the header logo),
// hand-animated: the start dot pops in, the S-curve draws from it to the
// end dot (900ms, starting at 150ms), the end dot pops in the instant the
// line reaches it (~1050ms), then the title fades in.
const HOLD_MS = 1950;
const FADE_MS = 350;

function TrailIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-12" fill="none" aria-hidden>
      <path
        d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={52}
        className="text-accent animate-[trail-draw_900ms_cubic-bezier(0.65,0,0.35,1)_150ms_both]"
      />
      <circle
        cx={6}
        cy={19}
        r={3}
        className="fill-accent animate-[trail-dot_300ms_ease-out_both]"
        style={{ transformBox: "fill-box", transformOrigin: "center" }}
      />
      <circle
        cx={18}
        cy={5}
        r={3}
        className="fill-accent animate-[trail-dot_300ms_ease-out_both]"
        style={{
          transformBox: "fill-box",
          transformOrigin: "center",
          animationDelay: "1050ms",
        }}
      />
    </svg>
  );
}

export function SplashScreen({ onDone }: { onDone: () => void }) {
  const [fadingOut, setFadingOut] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFadingOut(true), HOLD_MS);
    const doneTimer = setTimeout(onDone, HOLD_MS + FADE_MS);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, [onDone]);

  return (
    <div
      className={cn(
        "fixed inset-0 z-[100] flex flex-col items-center justify-center gap-4 bg-background transition-opacity ease-out",
        fadingOut ? "opacity-0" : "opacity-100",
      )}
      style={{ transitionDuration: `${FADE_MS}ms` }}
      aria-hidden
    >
      <TrailIcon />
      <h1 className="flex gap-2 overflow-hidden text-3xl font-semibold tracking-tight text-foreground">
        <span className="inline-block animate-[splash-in_500ms_cubic-bezier(0.22,1,0.36,1)_1250ms_both]">
          Paper
        </span>
        <span className="inline-block text-accent animate-[splash-in_500ms_cubic-bezier(0.22,1,0.36,1)_1375ms_both]">
          Tail
        </span>
      </h1>
    </div>
  );
}

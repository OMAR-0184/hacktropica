import React, { useEffect, useRef, useCallback } from 'react';

interface Node {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  brightness: number;
  targetBrightness: number;
  pulsePhase: number;
}

interface Edge {
  a: number;
  b: number;
}

const NODE_COUNT   = 38;
const CONNECT_DIST = 180;
const MOUSE_RADIUS = 200;

function getRandom(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export function GraphCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouse     = useRef({ x: -9999, y: -9999 });
  const nodes     = useRef<Node[]>([]);
  const edges     = useRef<Edge[]>([]);
  const rafId     = useRef<number>(0);
  const tick      = useRef(0);

  const buildGraph = useCallback((w: number, h: number) => {
    nodes.current = Array.from({ length: NODE_COUNT }, () => ({
      x:              getRandom(0, w),
      y:              getRandom(0, h),
      r:              getRandom(1.5, 3.5),
      vx:             getRandom(-0.12, 0.12),
      vy:             getRandom(-0.12, 0.12),
      brightness:     0,
      targetBrightness: 0,
      pulsePhase:     getRandom(0, Math.PI * 2),
    }));

    const e: Edge[] = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      for (let j = i + 1; j < NODE_COUNT; j++) {
        const dx = nodes.current[i].x - nodes.current[j].x;
        const dy = nodes.current[i].y - nodes.current[j].y;
        if (Math.sqrt(dx * dx + dy * dy) < CONNECT_DIST) {
          e.push({ a: i, b: j });
        }
      }
    }
    edges.current = e;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
      buildGraph(canvas.width, canvas.height);
    };

    resize();
    window.addEventListener('resize', resize);

    const onMouseMove = (e: MouseEvent) => {
      mouse.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('mousemove', onMouseMove);

    const draw = () => {
      tick.current++;
      const { width: W, height: H } = canvas;
      const ns = nodes.current;
      const mu = mouse.current;

      ctx.clearRect(0, 0, W, H);

      // Update nodes
      for (const n of ns) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < -20) n.x = W + 20;
        if (n.x > W + 20) n.x = -20;
        if (n.y < -20) n.y = H + 20;
        if (n.y > H + 20) n.y = -20;

        const dx = n.x - mu.x;
        const dy = n.y - mu.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        n.targetBrightness = dist < MOUSE_RADIUS
          ? 1 - dist / MOUSE_RADIUS
          : 0;
        n.brightness += (n.targetBrightness - n.brightness) * 0.06;
      }

      // Rebuild edges only occasionally for performance
      if (tick.current % 120 === 0) {
        const e: Edge[] = [];
        for (let i = 0; i < NODE_COUNT; i++) {
          for (let j = i + 1; j < NODE_COUNT; j++) {
            const dx = ns[i].x - ns[j].x;
            const dy = ns[i].y - ns[j].y;
            if (Math.sqrt(dx * dx + dy * dy) < CONNECT_DIST) {
              e.push({ a: i, b: j });
            }
          }
        }
        edges.current = e;
      }

      // Draw edges
      for (const { a, b } of edges.current) {
        const na = ns[a], nb = ns[b];
        const brightness = Math.max(na.brightness, nb.brightness);
        const dx = na.x - nb.x;
        const dy = na.y - nb.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const baseAlpha = Math.max(0, (1 - dist / CONNECT_DIST) * 0.12);
        const alpha = baseAlpha + brightness * 0.35;
        if (alpha < 0.005) continue;

        const grad = ctx.createLinearGradient(na.x, na.y, nb.x, nb.y);
        if (brightness > 0.05) {
          grad.addColorStop(0, `rgba(14, 165, 233, ${alpha})`);
          grad.addColorStop(1, `rgba(139, 92, 246, ${alpha * 0.5})`);
        } else {
          grad.addColorStop(0, `rgba(255, 255, 255, ${alpha})`);
          grad.addColorStop(1, `rgba(255, 255, 255, ${alpha})`);
        }

        ctx.beginPath();
        ctx.moveTo(na.x, na.y);
        ctx.lineTo(nb.x, nb.y);
        ctx.strokeStyle = grad;
        ctx.lineWidth = brightness > 0.1 ? 1.2 : 0.6;
        ctx.stroke();
      }

      // Draw nodes
      for (const n of ns) {
        const pulse = Math.sin(tick.current * 0.02 + n.pulsePhase) * 0.5 + 0.5;
        const b     = n.brightness;
        const alpha = 0.12 + b * 0.7 + pulse * 0.05;

        // Outer glow
        if (b > 0.05) {
          const glowR = n.r * (2 + b * 5);
          const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowR);
          grd.addColorStop(0, `rgba(14, 165, 233, ${b * 0.3})`);
          grd.addColorStop(1, `rgba(14, 165, 233, 0)`);
          ctx.beginPath();
          ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();
        }

        // Core dot
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        if (b > 0.1) {
          ctx.fillStyle = `rgba(14, 165, 233, ${alpha})`;
        } else {
          ctx.fillStyle = `rgba(180, 200, 230, ${alpha * 0.6})`;
        }
        ctx.fill();
      }

      rafId.current = requestAnimationFrame(draw);
    };

    rafId.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafId.current);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMouseMove);
    };
  }, [buildGraph]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      aria-hidden="true"
    />
  );
}

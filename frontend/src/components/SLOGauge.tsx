import React from "react";
import { motion } from "motion/react";

interface SLOGaugeProps {
  currentMs: number;
  forecastMs: number;
  targetMs: number;
  breachInMinutes?: number;
}

const DEG_START = 135;
const DEG_END = 405;
const SWEEP = DEG_END - DEG_START; // 270
const CX = 100;
const CY = 100;
const R = 80;
const STROKE = 10;
const CIRC = 2 * Math.PI * R;
const ARC_LEN = (SWEEP / 360) * CIRC;

function degToRad(deg: number) {
  return (deg * Math.PI) / 180;
}

function valueToAngle(value: number, max: number) {
  const ratio = Math.min(Math.max(value / max, 0), 1);
  return DEG_START + ratio * SWEEP;
}

function pointOnArc(angleDeg: number, radius: number) {
  const r = degToRad(angleDeg);
  return { x: CX + radius * Math.cos(r), y: CY + radius * Math.sin(r) };
}

function statusColor(value: number, target: number): string {
  const ratio = value / target;
  if (ratio > 0.8) return "var(--rh-red, #ee0000)";
  if (ratio > 0.6) return "var(--rh-yellow, #ffcc17)";
  return "var(--rh-green, #63993d)";
}

export function SLOGauge({ currentMs, forecastMs, targetMs, breachInMinutes }: SLOGaugeProps) {
  if (targetMs <= 0) {
    return (
      <div style={{ width: 220, height: 220, display: "flex", alignItems: "center", justifyContent: "center", color: "#888" }}>
        No SLO target
      </div>
    );
  }

  const maxVal = Math.max(targetMs * 1.5, currentMs * 1.2, forecastMs * 1.2, 1);

  const currentAngle = valueToAngle(currentMs, maxVal);
  const forecastAngle = valueToAngle(forecastMs, maxVal);
  const targetAngle = valueToAngle(targetMs, maxVal);

  const currentColor = statusColor(currentMs, targetMs);
  const forecastColor = statusColor(forecastMs, targetMs);

  const needleLen = R - STROKE / 2 - 2;
  const currentTip = pointOnArc(currentAngle, needleLen);
  const forecastTip = pointOnArc(forecastAngle, needleLen);

  const tMarkInner = pointOnArc(targetAngle, R - STROKE / 2 - 8);
  const tMarkOuter = pointOnArc(targetAngle, R + STROKE / 2 + 4);

  const dashOffset = CIRC - ARC_LEN;

  return (
    <div style={{ width: 220, height: 220, position: "relative", fontFamily: "system-ui, sans-serif" }}>
      <svg viewBox="0 0 200 200" width="220" height="220">
        {/* Background arc */}
        <circle
          cx={CX} cy={CY} r={R}
          fill="none"
          stroke="var(--surface-2, #292929)"
          strokeWidth={STROKE}
          strokeDasharray={`${ARC_LEN} ${CIRC}`}
          strokeDashoffset={-((DEG_START / 360) * CIRC)}
          strokeLinecap="round"
          transform={`rotate(0 ${CX} ${CY})`}
          style={{ transformOrigin: `${CX}px ${CY}px` }}
        />

        {/* SLO target marker */}
        <line
          x1={tMarkInner.x} y1={tMarkInner.y}
          x2={tMarkOuter.x} y2={tMarkOuter.y}
          stroke="white"
          strokeWidth={2}
          strokeDasharray="3 2"
        />

        {/* Forecast needle */}
        <motion.line
          x1={CX} y1={CY}
          initial={{ x2: CX, y2: CY }}
          animate={{ x2: forecastTip.x, y2: forecastTip.y }}
          transition={{ type: "spring", stiffness: 60, damping: 15 }}
          stroke={forecastColor}
          strokeWidth={2}
          strokeDasharray="5 3"
          opacity={0.7}
        />

        {/* Current value needle */}
        <motion.line
          x1={CX} y1={CY}
          initial={{ x2: CX, y2: CY }}
          animate={{ x2: currentTip.x, y2: currentTip.y }}
          transition={{ type: "spring", stiffness: 60, damping: 15 }}
          stroke={currentColor}
          strokeWidth={3}
          strokeLinecap="round"
        />

        {/* Center dot */}
        <circle cx={CX} cy={CY} r={4} fill="var(--border, #383838)" />
      </svg>

      {/* Center text overlay */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -38%)",
          textAlign: "center",
          pointerEvents: "none",
        }}
      >
        <div style={{ fontSize: 28, fontWeight: 700, color: currentColor, lineHeight: 1 }}>
          {currentMs.toFixed(0)}
          <span style={{ fontSize: 12, fontWeight: 400, color: "#aaa" }}> ms</span>
        </div>
        <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>P95 Latency</div>
        {breachInMinutes != null && breachInMinutes > 0 && (
          <div style={{ fontSize: 11, color: "var(--rh-red, #ee0000)", marginTop: 4, fontWeight: 600 }}>
            Breach in {breachInMinutes} min
          </div>
        )}
      </div>
    </div>
  );
}

export default SLOGauge;

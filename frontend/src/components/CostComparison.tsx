import React from "react";
import { motion } from "motion/react";

interface CostComparisonProps {
  gpuCost?: number;
  cpuCost?: number;
  animate?: boolean;
}

const MONTHLY_HOURS = 720;

function formatCost(cost: number): string {
  return `$${cost.toFixed(2)}`;
}

function formatMonthlyCost(cost: number): string {
  const monthly = cost * MONTHLY_HOURS;
  return monthly >= 1000
    ? `$${(monthly / 1000).toFixed(1)}k`
    : `$${monthly.toFixed(0)}`;
}

export function CostComparison({
  gpuCost = 32.0,
  cpuCost = 0.6,
  animate = true,
}: CostComparisonProps) {
  const ratio = gpuCost > 0 ? Math.round(gpuCost / cpuCost) : 0;
  const cpuWidthPct = gpuCost > 0 ? Math.max((cpuCost / gpuCost) * 100, 2) : 50;

  const barTransition = animate
    ? { type: "spring" as const, stiffness: 60, damping: 14, delay: 0.2 }
    : { duration: 0 };

  const calloutTransition = animate
    ? { type: "spring" as const, stiffness: 120, damping: 10, delay: 0.6 }
    : { duration: 0 };

  return (
    <div
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "28px 32px",
        fontFamily: "'Red Hat Display', 'Inter', system-ui, sans-serif",
        color: "#e0e0e0",
        maxWidth: 640,
      }}
    >
      {/* GPU bar */}
      <div style={{ marginBottom: 8 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 13,
            marginBottom: 6,
          }}
        >
          <span style={{ fontWeight: 600 }}>GPU (H100)</span>
          <span style={{ color: "var(--rh-orange)", fontWeight: 700 }}>
            {formatCost(gpuCost)}/hr
          </span>
        </div>
        <div
          style={{
            height: 32,
            borderRadius: 6,
            background: "var(--surface-2)",
            overflow: "hidden",
          }}
        >
          <motion.div
            initial={animate ? { width: 0 } : false}
            animate={{ width: "100%" }}
            transition={barTransition}
            style={{
              height: "100%",
              borderRadius: 6,
              background: "linear-gradient(90deg, var(--rh-orange), var(--rh-red))",
            }}
          />
        </div>
      </div>

      {/* Savings callout */}
      <div style={{ textAlign: "center", padding: "12px 0" }}>
        <motion.span
          initial={animate ? { scale: 0, opacity: 0 } : false}
          animate={{ scale: 1, opacity: 1 }}
          transition={calloutTransition}
          style={{
            display: "inline-block",
            fontSize: 36,
            fontWeight: 800,
            color: "var(--rh-green)",
            letterSpacing: "-0.02em",
          }}
        >
          {ratio}x
        </motion.span>
        <span
          style={{
            display: "block",
            fontSize: 12,
            color: "#888",
            marginTop: 2,
          }}
        >
          cost savings
        </span>
      </div>

      {/* CPU bar */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 13,
            marginBottom: 6,
          }}
        >
          <span style={{ fontWeight: 600 }}>CPU (Xeon)</span>
          <span style={{ color: "var(--rh-green)", fontWeight: 700 }}>
            {formatCost(cpuCost)}/hr
          </span>
        </div>
        <div
          style={{
            height: 32,
            borderRadius: 6,
            background: "var(--surface-2)",
            overflow: "hidden",
          }}
        >
          <motion.div
            initial={animate ? { width: 0 } : false}
            animate={{ width: `${cpuWidthPct}%` }}
            transition={barTransition}
            style={{
              height: "100%",
              borderRadius: 6,
              background: "linear-gradient(90deg, var(--rh-teal), var(--rh-green))",
            }}
          />
        </div>
      </div>

      {/* Monthly projection */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          color: "#888",
          borderTop: "1px solid var(--border)",
          paddingTop: 14,
        }}
      >
        <span>
          Monthly projection (24/7):{" "}
          <span style={{ color: "var(--rh-orange)", fontWeight: 600 }}>
            {formatMonthlyCost(gpuCost)}/mo
          </span>
        </span>
        <span>
          vs{" "}
          <span style={{ color: "var(--rh-green)", fontWeight: 600 }}>
            {formatMonthlyCost(cpuCost)}/mo
          </span>
        </span>
      </div>
    </div>
  );
}

export default CostComparison;

import React from "react";
import { motion } from "motion/react";

interface ReplicaEvent {
  time: string;
  replicas: number;
  trigger: string;
}

interface ReplicaTimelineProps {
  events: ReplicaEvent[];
  maxReplicas?: number;
}

const DEFAULT_EVENTS: ReplicaEvent[] = [
  { time: "10:00", replicas: 2, trigger: "Initial" },
  { time: "10:15", replicas: 4, trigger: "HPA: CPU > 70%" },
  { time: "10:30", replicas: 6, trigger: "PreWarm Intent" },
  { time: "10:45", replicas: 3, trigger: "Scale Down" },
];

const BLOCK_SIZE = 24;
const BLOCK_GAP = 3;

export function ReplicaTimeline({ events, maxReplicas }: ReplicaTimelineProps) {
  const data = events.length > 0 ? events : DEFAULT_EVENTS;
  const max = maxReplicas ?? Math.max(...data.map((e) => e.replicas), 1);
  const maxHeight = max * (BLOCK_SIZE + BLOCK_GAP);

  return (
    <div
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "32px 24px 16px",
        fontFamily: "'Red Hat Display', 'Inter', system-ui, sans-serif",
        color: "#e0e0e0",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-evenly",
          position: "relative",
          minHeight: maxHeight + 60,
        }}
      >
        {/* Baseline */}
        <div
          style={{
            position: "absolute",
            bottom: 28,
            left: 0,
            right: 0,
            height: 2,
            background: "var(--border)",
            borderRadius: 1,
          }}
        />

        {data.map((event, i) => (
          <div
            key={`${event.time}-${i}`}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 6,
              flex: 1,
              position: "relative",
              zIndex: 1,
            }}
          >
            {/* Trigger label */}
            <motion.span
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.12 + 0.3, duration: 0.35 }}
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: "var(--rh-teal)",
                textAlign: "center",
                whiteSpace: "nowrap",
                letterSpacing: "0.02em",
              }}
            >
              {event.trigger}
            </motion.span>

            {/* Replica count */}
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.12 + 0.4 }}
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "#fff",
              }}
            >
              {event.replicas}
            </motion.span>

            {/* Stacked blocks */}
            <div
              style={{
                display: "flex",
                flexDirection: "column-reverse",
                gap: BLOCK_GAP,
                minHeight: maxHeight,
                justifyContent: "flex-start",
              }}
            >
              {Array.from({ length: event.replicas }).map((_, b) => (
                <motion.div
                  key={b}
                  initial={{ scaleY: 0, opacity: 0 }}
                  animate={{ scaleY: 1, opacity: 1 }}
                  transition={{
                    type: "spring",
                    stiffness: 260,
                    damping: 20,
                    delay: i * 0.12 + b * 0.06,
                  }}
                  style={{
                    width: 32,
                    height: BLOCK_SIZE,
                    background: "var(--rh-blue)",
                    borderRadius: 4,
                    transformOrigin: "bottom",
                  }}
                />
              ))}
            </div>

            {/* Dot on baseline */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 18,
                delay: i * 0.12,
              }}
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "var(--rh-blue)",
                border: "2px solid var(--surface-1)",
                flexShrink: 0,
              }}
            />

            {/* Time label */}
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.12 + 0.15 }}
              style={{
                fontSize: 12,
                color: "#888",
                fontWeight: 500,
                marginTop: 2,
              }}
            >
              {event.time}
            </motion.span>
          </div>
        ))}
      </div>

      {events.length === 0 && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          transition={{ delay: 0.8 }}
          style={{
            textAlign: "center",
            fontSize: 12,
            color: "#666",
            margin: "8px 0 0",
          }}
        >
          Showing placeholder events
        </motion.p>
      )}
    </div>
  );
}

export default ReplicaTimeline;

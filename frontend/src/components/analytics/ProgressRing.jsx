import { useEffect, useRef } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';

/**
 * Animated SVG progress ring with spring animation.
 */
export default function ProgressRing({
    value = 0,
    max = 100,
    size = 100,
    strokeWidth = 8,
    color = '#7c5cff',
    label = '',
    sublabel = '',
}) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = Math.min(value / max, 1);

    const motionVal = useMotionValue(0);
    const strokeDashoffset = useTransform(motionVal, (v) => circumference * (1 - v));

    useEffect(() => {
        const controls = animate(motionVal, progress, {
            duration: 1.2,
            ease: 'easeOut',
        });
        return controls.stop;
    }, [progress, motionVal]);

    return (
        <div className="flex flex-col items-center gap-2">
            <div className="relative" style={{ width: size, height: size }}>
                <svg width={size} height={size} className="-rotate-90">
                    {/* Background circle */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="rgba(255,255,255,0.06)"
                        strokeWidth={strokeWidth}
                    />
                    {/* Progress circle */}
                    <motion.circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke={color}
                        strokeWidth={strokeWidth}
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        style={{ strokeDashoffset }}
                        filter={`drop-shadow(0 0 6px ${color}40)`}
                    />
                </svg>
                {/* Center text */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-xl font-bold font-display" style={{ color }}>
                        {Math.round(value)}%
                    </span>
                </div>
            </div>
            {label && <span className="text-sm font-medium text-gray-300">{label}</span>}
            {sublabel && <span className="text-xs text-gray-500">{sublabel}</span>}
        </div>
    );
}

import { useEffect, useState, useRef } from 'react';

/**
 * Animated counting number with spring effect.
 */
export default function AnimatedCounter({ value, duration = 1000, suffix = '', prefix = '', className = '' }) {
    const [displayValue, setDisplayValue] = useState(0);
    const startTime = useRef(null);
    const animFrame = useRef(null);

    useEffect(() => {
        const targetValue = typeof value === 'number' ? value : parseFloat(value) || 0;
        const startValue = displayValue;

        const step = (timestamp) => {
            if (!startTime.current) startTime.current = timestamp;
            const elapsed = timestamp - startTime.current;
            const progress = Math.min(elapsed / duration, 1);

            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = startValue + (targetValue - startValue) * eased;

            setDisplayValue(current);

            if (progress < 1) {
                animFrame.current = requestAnimationFrame(step);
            }
        };

        startTime.current = null;
        animFrame.current = requestAnimationFrame(step);

        return () => {
            if (animFrame.current) cancelAnimationFrame(animFrame.current);
        };
    }, [value, duration]);

    return (
        <span className={`font-display font-bold tabular-nums ${className}`}>
            {prefix}{Number.isInteger(value) ? Math.round(displayValue) : displayValue.toFixed(1)}{suffix}
        </span>
    );
}

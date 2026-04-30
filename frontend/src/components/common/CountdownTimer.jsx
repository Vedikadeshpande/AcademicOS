import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { daysUntil } from '../../lib/utils';

/**
 * Animated countdown timer showing days, hours, minutes, seconds until exam.
 */
export default function CountdownTimer({ targetDate, label = 'Time Remaining', compact = false }) {
    const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());

    function calculateTimeLeft() {
        if (!targetDate) return null;
        const diff = new Date(targetDate) - new Date();
        if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, expired: true };
        return {
            days: Math.floor(diff / (1000 * 60 * 60 * 24)),
            hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
            minutes: Math.floor((diff / (1000 * 60)) % 60),
            seconds: Math.floor((diff / 1000) % 60),
            expired: false,
        };
    }

    useEffect(() => {
        const timer = setInterval(() => setTimeLeft(calculateTimeLeft()), 1000);
        return () => clearInterval(timer);
    }, [targetDate]);

    if (!timeLeft) return null;

    const urgencyColor = timeLeft.days <= 3
        ? 'text-red-400'
        : timeLeft.days <= 7
            ? 'text-yellow-400'
            : 'text-accent-green';

    if (compact) {
        return (
            <span className={`text-sm font-mono font-medium ${urgencyColor}`}>
                {timeLeft.days}d {timeLeft.hours}h {timeLeft.minutes}m
            </span>
        );
    }

    const blocks = [
        { value: timeLeft.days, label: 'Days' },
        { value: timeLeft.hours, label: 'Hours' },
        { value: timeLeft.minutes, label: 'Min' },
        { value: timeLeft.seconds, label: 'Sec' },
    ];

    return (
        <div className="flex flex-col items-center gap-3">
            <div className="flex items-center gap-1.5 text-gray-400">
                <Clock className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
            </div>
            <div className="flex items-center gap-2">
                {blocks.map(({ value, label }, i) => (
                    <div key={label} className="flex items-center gap-2">
                        <motion.div
                            key={value}
                            initial={{ y: -4, opacity: 0.6 }}
                            animate={{ y: 0, opacity: 1 }}
                            className={`flex flex-col items-center px-3 py-2 rounded-xl
                         bg-dark-700/60 border border-white/[0.06] min-w-[56px]`}
                        >
                            <span className={`text-xl font-display font-bold tabular-nums ${urgencyColor}`}>
                                {String(value).padStart(2, '0')}
                            </span>
                            <span className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</span>
                        </motion.div>
                        {i < blocks.length - 1 && (
                            <span className={`text-lg font-bold ${urgencyColor} animate-pulse-soft`}>:</span>
                        )}
                    </div>
                ))}
            </div>
            {timeLeft.expired && (
                <span className="text-sm text-red-400 font-medium animate-pulse">Exam time!</span>
            )}
        </div>
    );
}

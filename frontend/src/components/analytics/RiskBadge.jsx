import { motion } from 'framer-motion';
import { AlertTriangle, Shield, ShieldCheck } from 'lucide-react';

/**
 * Animated risk level indicator with pulse for High risk.
 */
export default function RiskBadge({ level = 'N/A', size = 'normal' }) {
    const config = {
        Low: {
            icon: ShieldCheck,
            color: '#5cffb1',
            bg: 'bg-green-500/10',
            border: 'border-green-500/20',
            label: 'Low Risk',
            desc: "You're on track! Keep going.",
        },
        Medium: {
            icon: Shield,
            color: '#ff9f5c',
            bg: 'bg-yellow-500/10',
            border: 'border-yellow-500/20',
            label: 'Medium Risk',
            desc: 'Some areas need attention.',
        },
        High: {
            icon: AlertTriangle,
            color: '#ff5ca0',
            bg: 'bg-red-500/10',
            border: 'border-red-500/20',
            label: 'High Risk',
            desc: 'Focus on weak topics urgently!',
        },
    };

    const c = config[level] || {
        icon: Shield,
        color: '#8888a0',
        bg: 'bg-white/[0.04]',
        border: 'border-white/[0.08]',
        label: 'No Data',
        desc: 'Take quizzes to assess risk.',
    };

    const Icon = c.icon;
    const isCompact = size === 'compact';

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`${c.bg} border ${c.border} rounded-2xl ${isCompact ? 'px-3 py-2' : 'px-5 py-4'} flex items-center gap-3`}
        >
            <motion.div
                animate={level === 'High' ? { scale: [1, 1.15, 1] } : {}}
                transition={level === 'High' ? { duration: 1.5, repeat: Infinity } : {}}
            >
                <Icon className={isCompact ? 'w-5 h-5' : 'w-7 h-7'} style={{ color: c.color }} />
            </motion.div>
            <div>
                <p className={`font-display font-bold ${isCompact ? 'text-sm' : 'text-lg'}`} style={{ color: c.color }}>
                    {c.label}
                </p>
                {!isCompact && <p className="text-xs text-gray-500 mt-0.5">{c.desc}</p>}
            </div>
        </motion.div>
    );
}

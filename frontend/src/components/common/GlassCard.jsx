import { motion } from 'framer-motion';

/**
 * Glassmorphism card with optional floating animation.
 */
export default function GlassCard({ children, className = '', floating = false, glow = '', onClick, ...props }) {
    const glowClass = glow ? `glow-border-${glow}` : '';

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            whileHover={floating ? { y: -4, transition: { duration: 0.2 } } : undefined}
            onClick={onClick}
            className={`glass-card p-5 ${glowClass} ${onClick ? 'cursor-pointer' : ''} ${className}`}
            {...props}
        >
            {children}
        </motion.div>
    );
}

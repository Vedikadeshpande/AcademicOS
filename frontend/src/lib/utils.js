/**
 * Utility functions for the Academic OS frontend.
 */

/**
 * Format a date to a human-readable string.
 */
export function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * Calculate days remaining until a date.
 */
export function daysUntil(dateStr) {
    if (!dateStr) return null;
    const target = new Date(dateStr);
    const now = new Date();
    const diff = target - now;
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

/**
 * Get a human-readable time-remaining string.
 */
export function timeRemaining(dateStr) {
    const days = daysUntil(dateStr);
    if (days === null) return 'No date set';
    if (days === 0) return 'Today!';
    if (days === 1) return '1 day left';
    if (days < 7) return `${days} days left`;
    if (days < 30) return `${Math.floor(days / 7)} weeks left`;
    return `${Math.floor(days / 30)} months left`;
}

/**
 * Get risk level color class.
 */
export function riskColor(level) {
    switch (level?.toLowerCase()) {
        case 'low': return 'text-green-400';
        case 'medium': return 'text-yellow-400';
        case 'high': return 'text-red-400';
        default: return 'text-gray-400';
    }
}

/**
 * Get risk badge class.
 */
export function riskBadgeClass(level) {
    switch (level?.toLowerCase()) {
        case 'low': return 'badge-success';
        case 'medium': return 'badge-warning';
        case 'high': return 'badge-danger';
        default: return 'badge-info';
    }
}

/**
 * Clamp a value between min and max.
 */
export function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

/**
 * Generate a random subject color from the accent palette.
 */
const ACCENT_COLORS = ['#7c5cff', '#5c9cff', '#5cffb1', '#ff5ca0', '#ff9f5c', '#5cdcff'];
export function randomAccentColor() {
    return ACCENT_COLORS[Math.floor(Math.random() * ACCENT_COLORS.length)];
}

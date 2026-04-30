import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { BookOpen, FileText, CheckCircle, Clock, Trash2 } from 'lucide-react';
import ProgressRing from '../analytics/ProgressRing';
import CountdownTimer from '../common/CountdownTimer';
import { daysUntil, timeRemaining } from '../../lib/utils';

/**
 * Subject workspace card — floating panel with key stats.
 */
export default function SubjectCard({ subject, onDelete }) {
    const navigate = useNavigate();
    const days = daysUntil(subject.exam_date);

    const urgency = days !== null
        ? days <= 3 ? 'border-red-500/30' : days <= 7 ? 'border-yellow-500/20' : 'border-white/[0.08]'
        : 'border-white/[0.08]';

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            className={`glass-card p-5 cursor-pointer group border ${urgency}
                   hover:shadow-float transition-shadow duration-300`}
            onClick={() => navigate(`/subjects/${subject.id}`)}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: `${subject.color}20` }}
                    >
                        <BookOpen className="w-5 h-5" style={{ color: subject.color }} />
                    </div>
                    <div>
                        <h3 className="font-display font-semibold text-gray-100 group-hover:text-white transition-colors">
                            {subject.name}
                        </h3>
                        {subject.code && (
                            <span className="text-xs text-gray-500 font-mono">{subject.code}</span>
                        )}
                    </div>
                </div>

                {/* Delete button */}
                <button
                    onClick={(e) => { e.stopPropagation(); onDelete?.(subject.id); }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg
                     text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
            </div>

            {/* Stats row */}
            <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    <FileText className="w-3.5 h-3.5" />
                    <span>{subject.upload_count || 0} files</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>{subject.total_topics || 0} topics</span>
                </div>
                {subject.exam_date ? (
                    <div className="flex items-center gap-1.5 text-xs text-gray-400">
                        <Clock className="w-3.5 h-3.5" />
                        <span>{timeRemaining(subject.exam_date)}</span>
                    </div>
                ) : (
                    <div className="flex items-center gap-1.5 text-xs text-gray-500 italic">
                        <Clock className="w-3.5 h-3.5" />
                        <span>No exam date</span>
                    </div>
                )}
            </div>

            {/* Coverage bar */}
            <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Coverage</span>
                    <span className="font-medium" style={{ color: subject.color }}>
                        {subject.coverage_pct?.toFixed(1) || 0}%
                    </span>
                </div>
                <div className="h-1.5 bg-dark-600 rounded-full overflow-hidden">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${subject.coverage_pct || 0}%` }}
                        transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
                        className="h-full rounded-full"
                        style={{ backgroundColor: subject.color }}
                    />
                </div>
            </div>
        </motion.div>
    );
}

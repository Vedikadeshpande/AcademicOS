import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import useSubjectStore from '../../stores/subjectStore';
import useUIStore from '../../stores/uiStore';
import { randomAccentColor } from '../../lib/utils';

const ICONS = ['book', 'code', 'flask', 'calculator', 'globe', 'pen', 'cpu', 'music'];
const COLORS = ['#7c5cff', '#5c9cff', '#5cffb1', '#ff5ca0', '#ff9f5c', '#5cdcff'];

export default function CreateSubjectModal() {
    const { createModalOpen, closeCreateModal } = useUIStore();
    const { addSubject } = useSubjectStore();

    const [form, setForm] = useState({
        name: '',
        code: '',
        color: randomAccentColor(),
        icon: 'book',
        credits: 3,
        exam_date: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setLoading(true);
        setError('');
        try {
            const payload = {
                name: form.name.trim(),
                color: form.color,
                icon: form.icon,
                credits: form.credits,
                code: form.code.trim() || null,
                exam_date: form.exam_date || null,
            };
            await addSubject(payload);
            setForm({ name: '', code: '', color: randomAccentColor(), icon: 'book', credits: 3, exam_date: '' });
            closeCreateModal();
        } catch (err) {
            console.error('Create subject error:', err);
            const detail = err?.response?.data?.detail;
            console.log('Error detail:', detail);
            if (Array.isArray(detail)) {
                setError(detail.map(d => d.msg).join(', '));
            } else if (typeof detail === 'string') {
                setError(detail);
            } else {
                setError('Failed to create subject. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };


    return (
        <AnimatePresence>
            {createModalOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                >
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={closeCreateModal}
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="relative w-full max-w-md glass-card p-6 border border-white/[0.1]
                       shadow-float-lg z-10"
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-display font-semibold text-gradient-purple">
                                Create Subject
                            </h2>
                            <button
                                onClick={closeCreateModal}
                                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-200
                           hover:bg-white/[0.06] transition-all"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {error && (
                            <div className="mb-4 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {/* Name */}
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1.5">Subject Name *</label>
                                <input
                                    type="text"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    placeholder="e.g. Data Structures & Algorithms"
                                    className="input-field"
                                    required
                                />
                            </div>

                            {/* Code */}
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1.5">Subject Code</label>
                                <input
                                    type="text"
                                    value={form.code}
                                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                                    placeholder="e.g. CS201"
                                    className="input-field"
                                />
                            </div>

                            {/* Credits */}
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1.5">
                                    Course Credits <span className="text-accent-purple font-bold">{form.credits}</span>
                                </label>
                                <input
                                    type="range"
                                    min="1" max="6" step="1"
                                    value={form.credits}
                                    onChange={(e) => setForm({ ...form, credits: parseInt(e.target.value) })}
                                    className="w-full h-1.5 bg-dark-600 rounded-full appearance-none cursor-pointer
                                             [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                                             [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                                             [&::-webkit-slider-thumb]:bg-accent-purple [&::-webkit-slider-thumb]:shadow-glow-purple"
                                />
                                <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                                    <span>1 (Low)</span>
                                    <span>6 (High)</span>
                                </div>
                            </div>

                            {/* Color picker */}
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1.5">Accent Color</label>
                                <div className="flex gap-2">
                                    {COLORS.map((c) => (
                                        <button
                                            key={c}
                                            type="button"
                                            onClick={() => setForm({ ...form, color: c })}
                                            className={`w-8 h-8 rounded-xl transition-all ${form.color === c ? 'ring-2 ring-white/30 scale-110' : 'hover:scale-105'}`}
                                            style={{ backgroundColor: c }}
                                        />
                                    ))}
                                </div>
                            </div>

                            {/* Exam date */}
                            <div>
                                <label className="block text-xs font-medium text-gray-400 mb-1.5">Exam Date</label>
                                <input
                                    type="date"
                                    value={form.exam_date}
                                    onChange={(e) => setForm({ ...form, exam_date: e.target.value })}
                                    className="input-field"
                                />
                            </div>

                            {/* Submit */}
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={closeCreateModal} className="btn-secondary flex-1">
                                    Cancel
                                </button>
                                <button type="submit" disabled={loading} className="btn-primary flex-1">
                                    {loading ? 'Creating...' : 'Create Subject'}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

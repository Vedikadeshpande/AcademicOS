import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, CheckCircle, Circle, TrendingUp, X, Pencil, Check } from 'lucide-react';
import { toggleTopicCovered } from '../../lib/api';

/**
 * Syllabus tree viewer — displays units and topics with coverage status.
 * Supports editable mode: rename, delete topics and units.
 * Click the circle icon to toggle a topic as covered/uncovered.
 */
export default function SyllabusViewer({ units = [], onUnitsChange, editable = false }) {
    const [expandedUnits, setExpandedUnits] = useState(
        units.reduce((acc, u) => ({ ...acc, [u.id]: true }), {})
    );
    const [editingTopic, setEditingTopic] = useState(null);
    const [editValue, setEditValue] = useState('');
    const [togglingId, setTogglingId] = useState(null);

    const toggleUnit = (id) => {
        setExpandedUnits((prev) => ({ ...prev, [id]: !prev[id] }));
    };

    const handleDeleteTopic = (unitIdx, topicIdx) => {
        if (!onUnitsChange) return;
        const newUnits = [...units];
        const newTopics = [...newUnits[unitIdx].topics];
        newTopics.splice(topicIdx, 1);
        newUnits[unitIdx] = { ...newUnits[unitIdx], topics: newTopics };
        onUnitsChange(newUnits);
    };

    const handleStartEdit = (unitIdx, topicIdx, currentTitle) => {
        setEditingTopic({ unitIdx, topicIdx });
        setEditValue(currentTitle);
    };

    const handleSaveEdit = () => {
        if (!editingTopic || !onUnitsChange || !editValue.trim()) {
            setEditingTopic(null);
            return;
        }
        const { unitIdx, topicIdx } = editingTopic;
        const newUnits = [...units];
        const newTopics = [...newUnits[unitIdx].topics];
        newTopics[topicIdx] = { ...newTopics[topicIdx], title: editValue.trim() };
        newUnits[unitIdx] = { ...newUnits[unitIdx], topics: newTopics };
        onUnitsChange(newUnits);
        setEditingTopic(null);
    };

    const handleDeleteUnit = (unitIdx) => {
        if (!onUnitsChange) return;
        const newUnits = [...units];
        newUnits.splice(unitIdx, 1);
        onUnitsChange(newUnits);
    };

    const handleToggleCovered = async (unitIdx, topicIdx, topic) => {
        if (!topic.id || togglingId) return;
        setTogglingId(topic.id);
        try {
            const res = await toggleTopicCovered(topic.id);
            if (onUnitsChange) {
                const newUnits = [...units];
                const newTopics = [...newUnits[unitIdx].topics];
                newTopics[topicIdx] = { ...newTopics[topicIdx], is_covered: res.data.is_covered };
                newUnits[unitIdx] = { ...newUnits[unitIdx], coverage_pct: res.data.unit_coverage_pct };
                onUnitsChange(newUnits);
            }
        } catch (err) {
            console.error('Toggle coverage failed:', err);
        } finally {
            setTogglingId(null);
        }
    };

    if (units.length === 0) {
        return (
            <div className="text-center py-12 text-gray-500">
                <p className="text-sm">No syllabus parsed yet.</p>
                <p className="text-xs mt-1">Enter your syllabus above and click "Parse & Add".</p>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {units.map((unit, unitIdx) => (
                <motion.div
                    key={unit.id || unitIdx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: unitIdx * 0.05 }}
                >
                    {/* Unit header */}
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => toggleUnit(unit.id || unitIdx)}
                            className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl
                           glass-card-hover text-left group"
                        >
                            {expandedUnits[unit.id || unitIdx]
                                ? <ChevronDown className="w-4 h-4 text-gray-400" />
                                : <ChevronRight className="w-4 h-4 text-gray-400" />
                            }
                            <span className="text-xs font-mono text-gray-500 w-8">U{unit.unit_number}</span>
                            <span className="flex-1 text-sm font-medium text-gray-200">{unit.title}</span>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-500">
                                    {unit.topics?.length || 0} topic{(unit.topics?.length || 0) !== 1 ? 's' : ''}
                                </span>
                                {(unit.coverage_pct > 0 || unit.topics?.some(t => t.is_covered)) && (
                                    <>
                                        <div className="h-1 w-12 bg-dark-600 rounded-full overflow-hidden">
                                            <div
                                                className="h-full rounded-full bg-accent-green transition-all duration-500"
                                                style={{ width: `${unit.coverage_pct || 0}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-gray-500 w-8 text-right">
                                            {unit.coverage_pct?.toFixed(0) || 0}%
                                        </span>
                                    </>
                                )}
                            </div>
                        </button>
                        {editable && (
                            <button
                                onClick={() => handleDeleteUnit(unitIdx)}
                                className="p-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                                title="Delete unit"
                            >
                                <X className="w-3.5 h-3.5" />
                            </button>
                        )}
                    </div>

                    {/* Topics */}
                    <AnimatePresence>
                        {expandedUnits[unit.id || unitIdx] && unit.topics && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="ml-11 space-y-0.5 py-1 overflow-hidden"
                            >
                                {unit.topics.map((topic, tIdx) => {
                                    const isEditing = editingTopic?.unitIdx === unitIdx && editingTopic?.topicIdx === tIdx;
                                    const topicTitle = typeof topic === 'string' ? topic : topic.title;
                                    const isToggling = togglingId === topic.id;

                                    return (
                                        <motion.div
                                            key={topic.id || `${unitIdx}-${tIdx}`}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: tIdx * 0.03 }}
                                            className="flex items-center gap-3 px-3 py-2 rounded-lg
                               hover:bg-white/[0.03] transition-colors group"
                                        >
                                            {/* Clickable coverage toggle */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleToggleCovered(unitIdx, tIdx, topic);
                                                }}
                                                disabled={isToggling}
                                                className="flex-shrink-0 transition-all duration-200 hover:scale-110"
                                                title={topic.is_covered ? 'Mark as not covered' : 'Mark as covered'}
                                            >
                                                {isToggling ? (
                                                    <div className="w-3.5 h-3.5 border-2 border-accent-green border-t-transparent rounded-full animate-spin" />
                                                ) : topic.is_covered ? (
                                                    <CheckCircle className="w-3.5 h-3.5 text-accent-green" />
                                                ) : (
                                                    <Circle className="w-3.5 h-3.5 text-gray-600 hover:text-gray-400" />
                                                )}
                                            </button>

                                            {isEditing ? (
                                                <div className="flex-1 flex items-center gap-2">
                                                    <input
                                                        type="text"
                                                        value={editValue}
                                                        onChange={(e) => setEditValue(e.target.value)}
                                                        onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit()}
                                                        className="flex-1 px-2 py-1 rounded bg-dark-700 border border-accent-purple/30 text-sm text-gray-200 focus:outline-none"
                                                        autoFocus
                                                    />
                                                    <button onClick={handleSaveEdit} className="text-accent-green">
                                                        <Check className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            ) : (
                                                <>
                                                    <span className={`flex-1 text-sm ${topic.is_covered ? 'text-gray-300 line-through opacity-60' : 'text-gray-400'}`}>
                                                        {topicTitle}
                                                    </span>

                                                    {topic.pyq_frequency > 0 && (
                                                        <span className="flex items-center gap-1 text-xs text-accent-orange">
                                                            <TrendingUp className="w-3 h-3" />
                                                            {(topic.pyq_frequency * 100).toFixed(0)}%
                                                        </span>
                                                    )}
                                                    {topic.quiz_accuracy > 0 && (
                                                        <span className="text-xs text-accent-blue">
                                                            {topic.quiz_accuracy.toFixed(0)}% acc
                                                        </span>
                                                    )}

                                                    {editable && (
                                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                            <button
                                                                onClick={() => handleStartEdit(unitIdx, tIdx, topicTitle)}
                                                                className="p-1 rounded text-gray-600 hover:text-accent-blue transition-colors"
                                                                title="Rename topic"
                                                            >
                                                                <Pencil className="w-3 h-3" />
                                                            </button>
                                                            <button
                                                                onClick={() => handleDeleteTopic(unitIdx, tIdx)}
                                                                className="p-1 rounded text-gray-600 hover:text-red-400 transition-colors"
                                                                title="Remove topic"
                                                            >
                                                                <X className="w-3 h-3" />
                                                            </button>
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                        </motion.div>
                                    );
                                })}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            ))}
        </div>
    );
}

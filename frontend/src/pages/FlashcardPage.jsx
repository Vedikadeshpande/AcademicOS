import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Layers, RotateCcw, CheckCircle, XCircle,
    Sparkles, ChevronRight, BookOpen, Globe, FolderOpen, FileText, Trash2, Clock
} from 'lucide-react';
import GlassCard from '../components/common/GlassCard';
import useSubjectStore from '../stores/subjectStore';
import { getAllFlashcards, getDueFlashcards, generateFlashcards, reviewFlashcard, getSyllabusUnits, clearFlashcards } from '../lib/api';

const BOX_COLORS = ['#ff5c5c', '#ff9f5c', '#ffd95c', '#5cffb1', '#5cdcff'];
const BOX_LABELS = ['New', 'Learning', 'Review', 'Known', 'Mastered'];

export default function FlashcardPage() {
    const { subjects, fetchSubjects } = useSubjectStore();
    const [selectedSubject, setSelectedSubject] = useState('');
    const [mode, setMode] = useState('overview'); // overview, study, generate
    const [cards, setCards] = useState([]);
    const [dueCards, setDueCards] = useState([]);
    const [currentIdx, setCurrentIdx] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [loading, setLoading] = useState(false);
    const [units, setUnits] = useState([]);
    const [genCount, setGenCount] = useState(5);
    const [stats, setStats] = useState({ total: 0, boxes: [0, 0, 0, 0, 0] });

    // Generate scope state
    const [scope, setScope] = useState('all'); // 'all', 'unit', 'topic'
    const [selectedUnit, setSelectedUnit] = useState('');
    const [selectedTopic, setSelectedTopic] = useState('');

    // Study timer
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const timerRef = useRef(null);

    useEffect(() => { fetchSubjects(); }, []);

    useEffect(() => {
        if (selectedSubject) loadData();
    }, [selectedSubject]);

    const loadData = async () => {
        try {
            const [allRes, dueRes, unitsRes] = await Promise.all([
                getAllFlashcards(selectedSubject),
                getDueFlashcards(selectedSubject),
                getSyllabusUnits(selectedSubject),
            ]);
            setCards(allRes.data.cards || []);
            setDueCards(dueRes.data.cards || []);

            const allCards = allRes.data.cards || [];
            const boxes = [0, 0, 0, 0, 0];
            allCards.forEach(c => { if (c.leitner_box >= 1 && c.leitner_box <= 5) boxes[c.leitner_box - 1]++; });
            setStats({ total: allCards.length, boxes });

            setUnits(unitsRes.data || []);
        } catch (err) {
            console.error(err);
        }
    };

    const handleGenerate = async () => {
        // Validate based on scope
        if (scope === 'topic' && !selectedTopic) return;
        if (scope === 'unit' && !selectedUnit) return;

        setLoading(true);
        try {
            const payload = {
                subject_id: selectedSubject,
                scope,
                count: genCount,
            };
            if (scope === 'unit') payload.unit_id = selectedUnit;
            if (scope === 'topic') payload.topic_id = selectedTopic;

            await generateFlashcards(payload);
            await loadData();
            setMode('overview');
        } catch (err) {
            console.error('Generate flashcards error:', err);
            alert('Failed to generate flashcards. Make sure you have a syllabus parsed.');
        } finally {
            setLoading(false);
        }
    };

    const startStudy = () => {
        if (dueCards.length === 0 && cards.length === 0) {
            alert('No flashcards available. Generate some first!');
            return;
        }
        setCurrentIdx(0);
        setFlipped(false);
        setElapsedSeconds(0);
        // Start timer
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => setElapsedSeconds(s => s + 1), 1000);
        setMode('study');
    };

    const handleReview = async (isCorrect) => {
        const activeCards = dueCards.length > 0 ? dueCards : cards;
        const card = activeCards[currentIdx];
        if (!card) return;

        try {
            await reviewFlashcard({ card_id: card.id, is_correct: isCorrect });
        } catch (err) {
            console.error(err);
        }

        setFlipped(false);

        if (currentIdx < activeCards.length - 1) {
            setTimeout(() => setCurrentIdx(prev => prev + 1), 300);
        } else {
            if (timerRef.current) clearInterval(timerRef.current);
            await loadData();
            setMode('overview');
        }
    };

    // Get topics for selected unit
    const unitTopics = units.find(u => u.id === selectedUnit)?.topics || [];
    const allTopics = units.flatMap(u => u.topics || []);

    const activeCards = dueCards.length > 0 ? dueCards : cards;
    const currentCard = activeCards[currentIdx];

    return (
        <div className="space-y-6 max-w-3xl mx-auto">
            {/* Subject selector */}
            <GlassCard className="!p-4">
                <div className="flex items-center gap-4">
                    <Layers className="w-5 h-5 text-accent-purple" />
                    <select
                        value={selectedSubject}
                        onChange={(e) => { setSelectedSubject(e.target.value); setMode('overview'); }}
                        className="input-field flex-1"
                    >
                        <option value="">Select a subject...</option>
                        {subjects.map(s => (
                            <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                    </select>
                </div>
            </GlassCard>

            {selectedSubject && (
                <AnimatePresence mode="wait">
                    {/* ── OVERVIEW ── */}
                    {mode === 'overview' && (
                        <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
                            {/* Leitner boxes */}
                            <GlassCard>
                                <h3 className="text-sm font-display font-semibold text-gray-300 mb-4">Leitner Boxes</h3>
                                <div className="flex gap-3">
                                    {stats.boxes.map((count, i) => (
                                        <div key={i} className="flex-1 text-center">
                                            <div
                                                className="h-20 rounded-xl flex items-end justify-center pb-2 border border-white/[0.06] relative overflow-hidden"
                                            >
                                                <motion.div
                                                    initial={{ height: 0 }}
                                                    animate={{ height: `${stats.total > 0 ? (count / stats.total) * 100 : 0}%` }}
                                                    transition={{ duration: 0.8, delay: i * 0.1 }}
                                                    className="absolute bottom-0 left-0 right-0 rounded-b-xl"
                                                    style={{ backgroundColor: `${BOX_COLORS[i]}30` }}
                                                />
                                                <span className="relative text-lg font-display font-bold" style={{ color: BOX_COLORS[i] }}>
                                                    {count}
                                                </span>
                                            </div>
                                            <span className="text-[10px] text-gray-500 mt-1 block">{BOX_LABELS[i]}</span>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/[0.06]">
                                    <span className="text-xs text-gray-500">{stats.total} total cards • {dueCards.length} due</span>
                                </div>
                            </GlassCard>

                            {/* Action buttons */}
                            <div className="grid grid-cols-2 gap-3">
                                <button onClick={startStudy} className="btn-primary flex items-center justify-center gap-2 py-4">
                                    <BookOpen className="w-5 h-5" /> Study ({dueCards.length > 0 ? `${dueCards.length} due` : `${cards.length} cards`})
                                </button>
                                <button onClick={() => setMode('generate')} className="btn-secondary flex items-center justify-center gap-2 py-4">
                                    <Sparkles className="w-5 h-5" /> Generate New
                                </button>
                            </div>

                            {/* Clear flashcards */}
                            {cards.length > 0 && (
                                <button
                                    onClick={async () => {
                                        if (!confirm(`Are you sure you want to delete all ${cards.length} flashcards for this subject? This cannot be undone.`)) return;
                                        try {
                                            await clearFlashcards(selectedSubject);
                                            await loadData();
                                        } catch (err) {
                                            console.error('Failed to clear flashcards:', err);
                                        }
                                    }}
                                    className="w-full py-2.5 rounded-xl text-sm text-red-400/70 hover:text-red-400
                                        hover:bg-red-500/10 border border-transparent hover:border-red-500/20
                                        transition-all flex items-center justify-center gap-2"
                                >
                                    <Trash2 className="w-4 h-4" /> Clear All Flashcards
                                </button>
                            )}

                            {/* Card list preview */}
                            {cards.length > 0 && (
                                <GlassCard>
                                    <h3 className="text-sm font-display font-semibold text-gray-300 mb-3">All Cards</h3>
                                    <div className="space-y-1.5 max-h-60 overflow-y-auto pr-2">
                                        {cards.slice(0, 20).map((c, i) => (
                                            <div key={c.id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.03]">
                                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: BOX_COLORS[c.leitner_box - 1] }} />
                                                <span className="text-sm text-gray-300 flex-1 truncate">{c.front}</span>
                                                <span className="text-xs text-gray-600">Box {c.leitner_box}</span>
                                            </div>
                                        ))}
                                    </div>
                                </GlassCard>
                            )}
                        </motion.div>
                    )}

                    {/* ── STUDY MODE ── */}
                    {mode === 'study' && currentCard && (
                        <motion.div key="study" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
                            {/* Progress + Timer */}
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-gray-400">Card {currentIdx + 1} of {activeCards.length}</span>
                                <div className="flex items-center gap-4">
                                    <span className="flex items-center gap-1.5 text-gray-500">
                                        <Clock className="w-3.5 h-3.5" />
                                        {String(Math.floor(elapsedSeconds / 60)).padStart(2, '0')}:{String(elapsedSeconds % 60).padStart(2, '0')}
                                    </span>
                                    <button onClick={() => { if (timerRef.current) clearInterval(timerRef.current); setMode('overview'); loadData(); }} className="text-xs text-gray-500 hover:text-gray-300">
                                        Exit
                                    </button>
                                </div>
                            </div>
                            <div className="h-1 bg-dark-600 rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-accent-purple rounded-full"
                                    animate={{ width: `${((currentIdx + 1) / activeCards.length) * 100}%` }}
                                />
                            </div>

                            {/* Flashcard */}
                            <div
                                className="relative cursor-pointer"
                                onClick={() => setFlipped(!flipped)}
                                style={{ perspective: '1000px' }}
                            >
                                <motion.div
                                    animate={{ rotateY: flipped ? 180 : 0 }}
                                    transition={{ duration: 0.5, type: 'spring', stiffness: 200 }}
                                    style={{ transformStyle: 'preserve-3d' }}
                                    className="relative h-64"
                                >
                                    {/* Front */}
                                    <div
                                        className="absolute inset-0 glass-card flex items-center justify-center p-8 text-center"
                                        style={{ backfaceVisibility: 'hidden' }}
                                    >
                                        <div>
                                            <span className="text-xs text-accent-purple font-medium uppercase tracking-wider mb-3 block">Question</span>
                                            <p className="text-lg text-gray-200 font-medium leading-relaxed">{currentCard.front}</p>
                                            <span className="text-xs text-gray-600 mt-4 block">Tap to reveal answer</span>
                                        </div>
                                    </div>

                                    {/* Back */}
                                    <div
                                        className="absolute inset-0 glass-card flex items-center justify-center p-8 text-center"
                                        style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
                                    >
                                        <div>
                                            <span className="text-xs text-accent-green font-medium uppercase tracking-wider mb-3 block">Answer</span>
                                            <p className="text-gray-200 leading-relaxed">{currentCard.back}</p>
                                        </div>
                                    </div>
                                </motion.div>
                            </div>

                            {/* Review buttons */}
                            <AnimatePresence>
                                {flipped && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="flex gap-3"
                                    >
                                        <button
                                            onClick={() => handleReview(false)}
                                            className="flex-1 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400
                                 hover:bg-red-500/20 transition-all flex items-center justify-center gap-2"
                                        >
                                            <XCircle className="w-5 h-5" /> Didn't Know
                                        </button>
                                        <button
                                            onClick={() => handleReview(true)}
                                            className="flex-1 py-3 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400
                                 hover:bg-green-500/20 transition-all flex items-center justify-center gap-2"
                                        >
                                            <CheckCircle className="w-5 h-5" /> Got It!
                                        </button>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Box indicator */}
                            <div className="text-center">
                                <span className="text-xs text-gray-600">
                                    Box {currentCard.leitner_box} • Reviewed {currentCard.review_count} time{currentCard.review_count !== 1 ? 's' : ''}
                                </span>
                            </div>
                        </motion.div>
                    )}

                    {/* ── GENERATE MODE ── */}
                    {mode === 'generate' && (
                        <motion.div key="generate" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
                            <GlassCard>
                                <h3 className="text-sm font-display font-semibold text-gray-300 mb-4">
                                    <Sparkles className="w-4 h-4 inline mr-2 text-accent-purple" />Generate Flashcards
                                </h3>

                                {/* ── Scope selector ── */}
                                <label className="block text-xs font-medium text-gray-400 mb-3">Choose scope</label>
                                <div className="grid grid-cols-3 gap-3 mb-5">
                                    {[
                                        { key: 'all', icon: Globe, label: 'Entire Syllabus', desc: 'All topics' },
                                        { key: 'unit', icon: FolderOpen, label: 'By Unit', desc: 'Pick a unit' },
                                        { key: 'topic', icon: FileText, label: 'By Topic', desc: 'Single topic' },
                                    ].map(({ key, icon: Icon, label, desc }) => (
                                        <button
                                            key={key}
                                            onClick={() => { setScope(key); setSelectedUnit(''); setSelectedTopic(''); }}
                                            className={`p-4 rounded-xl border text-left transition-all group
                                                ${scope === key
                                                    ? 'border-accent-purple/50 bg-accent-purple/10 shadow-glow-purple'
                                                    : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]'
                                                }`}
                                        >
                                            <Icon className={`w-5 h-5 mb-2 ${scope === key ? 'text-accent-purple' : 'text-gray-500'}`} />
                                            <div className={`text-sm font-medium ${scope === key ? 'text-accent-purple' : 'text-gray-300'}`}>{label}</div>
                                            <div className="text-[10px] text-gray-500 mt-0.5">{desc}</div>
                                        </button>
                                    ))}
                                </div>

                                {/* ── Conditional selectors ── */}
                                {scope === 'unit' && (
                                    <div className="mb-4">
                                        <label className="block text-xs font-medium text-gray-400 mb-1.5">Select Unit</label>
                                        <select
                                            value={selectedUnit}
                                            onChange={(e) => setSelectedUnit(e.target.value)}
                                            className="input-field"
                                        >
                                            <option value="">Choose a unit...</option>
                                            {units.map(u => (
                                                <option key={u.id} value={u.id}>
                                                    Unit {u.unit_number}: {u.title} ({u.topics?.length || 0} topics)
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                {scope === 'topic' && (
                                    <div className="mb-4">
                                        <label className="block text-xs font-medium text-gray-400 mb-1.5">Select Topic</label>
                                        <select
                                            value={selectedTopic}
                                            onChange={(e) => setSelectedTopic(e.target.value)}
                                            className="input-field"
                                        >
                                            <option value="">Choose a topic...</option>
                                            {units.map(u => (
                                                <optgroup key={u.id} label={`Unit ${u.unit_number}: ${u.title}`}>
                                                    {(u.topics || []).map(t => (
                                                        <option key={t.id} value={t.id}>{t.title}</option>
                                                    ))}
                                                </optgroup>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                {/* ── Cards count ── */}
                                <div className="mb-5">
                                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                                        Cards to generate: <span className="text-accent-purple font-bold">{genCount}</span>
                                        {scope !== 'topic' && (
                                            <span className="text-gray-600 ml-1">(distributed across topics)</span>
                                        )}
                                    </label>
                                    <input
                                        type="range"
                                        min="3" max="20" step="1"
                                        value={genCount}
                                        onChange={(e) => setGenCount(parseInt(e.target.value))}
                                        className="w-full accent-accent-purple"
                                    />
                                </div>

                                {/* ── Actions ── */}
                                <div className="flex gap-3">
                                    <button onClick={() => setMode('overview')} className="btn-secondary flex-1">
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleGenerate}
                                        disabled={
                                            loading ||
                                            (scope === 'topic' && !selectedTopic) ||
                                            (scope === 'unit' && !selectedUnit)
                                        }
                                        className="btn-primary flex-1 flex items-center justify-center gap-2"
                                    >
                                        {loading ? (
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <><Sparkles className="w-4 h-4" /> Generate</>
                                        )}
                                    </button>
                                </div>
                            </GlassCard>
                        </motion.div>
                    )}
                </AnimatePresence>
            )}
        </div>
    );
}

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Plus, BookOpen } from 'lucide-react';
import useSubjectStore from '../stores/subjectStore';
import useUIStore from '../stores/uiStore';
import SubjectCard from '../components/subject/SubjectCard';

const container = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
};

/**
 * Full subjects list page — mirrors the dashboard subject grid.
 */
export function SubjectsListPage() {
    const { subjects, loading, fetchSubjects, removeSubject } = useSubjectStore();
    const { openCreateModal } = useUIStore();

    useEffect(() => {
        fetchSubjects();
    }, [fetchSubjects]);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-display font-bold text-gray-100">All Subjects</h2>
                    <p className="text-sm text-gray-500 mt-0.5">
                        {subjects.length} subject{subjects.length !== 1 ? 's' : ''} in your workspace
                    </p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" />
                    Add Subject
                </button>
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-44 skeleton rounded-2xl" />
                    ))}
                </div>
            ) : subjects.length === 0 ? (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="glass-card p-16 text-center"
                >
                    <BookOpen className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                    <h3 className="text-lg font-display font-semibold text-gray-300 mb-2">
                        No subjects yet
                    </h3>
                    <p className="text-sm text-gray-500 mb-5">
                        Create your first subject to start building your intelligent workspace.
                    </p>
                    <button onClick={openCreateModal} className="btn-primary">
                        <Plus className="w-4 h-4 inline mr-2" />
                        Create First Subject
                    </button>
                </motion.div>
            ) : (
                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="visible"
                    className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
                >
                    {subjects.map((subject) => (
                        <motion.div key={subject.id} variants={item}>
                            <SubjectCard
                                subject={subject}
                                onDelete={(id) => {
                                    if (confirm('Delete this subject and all its data?')) {
                                        removeSubject(id);
                                    }
                                }}
                            />
                        </motion.div>
                    ))}
                </motion.div>
            )}
        </div>
    );
}

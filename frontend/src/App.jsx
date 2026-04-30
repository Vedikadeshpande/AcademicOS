import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import CreateSubjectModal from './components/subject/CreateSubjectModal';
import Dashboard from './pages/Dashboard';
import SubjectWorkspace from './pages/SubjectWorkspace';
import QuizPage from './pages/QuizPage';
import FlashcardPage from './pages/FlashcardPage';
import StudyPlanPage from './pages/StudyPlanPage';
import AnalyticsPage from './pages/AnalyticsPage';
import { SubjectsListPage } from './pages/PlaceholderPages';
import VivaPage from './pages/VivaPage';
import useUIStore from './stores/uiStore';


export default function App() {
  const { sidebarOpen } = useUIStore();

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-dark-900">
        <Sidebar />

        {/* Main content area */}
        <motion.main
          animate={{ marginLeft: sidebarOpen ? 240 : 72 }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
          className="flex-1 min-h-screen"
        >
          <Routes>
            <Route
              path="/"
              element={
                <>
                  <TopBar title="Dashboard" subtitle="Your academic command center" />
                  <div className="p-6"><Dashboard /></div>
                </>
              }
            />
            <Route
              path="/subjects"
              element={
                <>
                  <TopBar title="Subjects" subtitle="Manage your subject workspaces" />
                  <div className="p-6"><SubjectsListPage /></div>
                </>
              }
            />
            <Route
              path="/subjects/:id"
              element={
                <>
                  <TopBar title="Subject Workspace" subtitle="Manage content, syllabus, and analytics" />
                  <div className="p-6"><SubjectWorkspace /></div>
                </>
              }
            />
            <Route
              path="/quizzes"
              element={
                <>
                  <TopBar title="Quizzes" subtitle="Test your knowledge" />
                  <div className="p-6"><QuizPage /></div>
                </>
              }
            />
            <Route
              path="/flashcards"
              element={
                <>
                  <TopBar title="Flashcards" subtitle="Spaced repetition learning" />
                  <div className="p-6"><FlashcardPage /></div>
                </>
              }
            />
            <Route
              path="/study-plan"
              element={
                <>
                  <TopBar title="Study Plan" subtitle="Your adaptive schedule" />
                  <div className="p-6"><StudyPlanPage /></div>
                </>
              }
            />
            <Route
              path="/analytics"
              element={
                <>
                  <TopBar title="Analytics" subtitle="Performance insights" />
                  <div className="p-6"><AnalyticsPage /></div>
                </>
              }
            />
            <Route
              path="/viva"
              element={
                <>
                  <TopBar title="Viva Mode" subtitle="AI Oral Examination" />
                  <div className="p-6 h-[calc(100vh-80px)] overflow-hidden"><VivaPage /></div>
                </>
              }
            />
          </Routes>
        </motion.main>

        {/* Global modals */}
        <CreateSubjectModal />
      </div>
    </BrowserRouter>
  );
}

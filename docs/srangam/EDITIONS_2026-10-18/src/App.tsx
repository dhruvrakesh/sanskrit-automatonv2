import React, { Suspense, lazy } from 'react';
// LOAD_L2_2026_10_09: the toast hosts load right after the first render instead of in the entry.
// Radix toasts raised before the host mounts are kept in use-toast's memory state and shown on mount.
const Toaster = lazy(() => import("@/components/ui/toaster").then((m) => ({ default: m.Toaster })));
const Sonner = lazy(() => import("@/components/ui/sonner").then((m) => ({ default: m.Toaster })));
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { LanguageProvider } from "@/components/language/LanguageProvider";
import { HelmetProvider } from 'react-helmet-async';
import { ThemeProvider } from 'next-themes';
import { Loader2 } from 'lucide-react';
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/admin/ProtectedRoute";
import { ScrollToTop } from "@/components/ScrollToTop";
import { SiteSchema } from "@/components/seo/SiteSchema";

// Phase L.1 — dev-only TTS telemetry panel. Vite tree-shakes both the
// import and the JSX branch from production bundles via import.meta.env.DEV.
const NarrationDebugPanel = import.meta.env.DEV
  ? lazy(() => import('@/components/dev/NarrationDebugPanel').then(m => ({ default: m.NarrationDebugPanel })))
  : null;

// Immediate load for critical pages
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";

// Lazy load theme pages for better performance
const AncientIndia = lazy(() => import("./pages/themes/AncientIndia"));
const IndianOceanWorld = lazy(() => import("./pages/themes/IndianOceanWorld"));
const ScriptsInscriptions = lazy(() => import("./pages/themes/ScriptsInscriptions"));
const GeologyDeepTime = lazy(() => import("./pages/themes/GeologyDeepTime"));
const EmpiresExchange = lazy(() => import("./pages/themes/EmpiresExchange"));

// Lazy load secondary pages
const BeginJourney = lazy(() => import("./pages/BeginJourney"));
const Articles = lazy(() => import("./pages/Articles"));
const FieldNotes = lazy(() => import("./pages/FieldNotes"));
const MapsData = lazy(() => import("./pages/MapsData"));
const ReadingRoom = lazy(() => import("./pages/ReadingRoom"));
const SourcesMethod = lazy(() => import("./pages/SourcesMethod"));
const Search = lazy(() => import("./pages/Search"));
const About = lazy(() => import("./pages/About"));
const Brand = lazy(() => import("./pages/Brand"));

// Lazy load research pages
const ResearchSubmission = lazy(() => import("./pages/ResearchSubmission"));
const Partnership = lazy(() => import("./pages/Partnership"));
const SupportResearch = lazy(() => import("./pages/SupportResearch"));
const DataVisualization = lazy(() => import("./pages/DataVisualization"));
const ResearchNetwork = lazy(() => import("./pages/ResearchNetwork"));

// Batch pages (still used directly)
const BatchBujangNagapattinamOcean = lazy(() => import("./pages/BatchBujangNagapattinamOcean"));
const BatchMuzirisKutaiAshoka = lazy(() => import("./pages/BatchMuzirisKutaiAshoka"));
const Sitemap = lazy(() => import("./pages/Sitemap"));
const SitemapXML = lazy(() => import("./pages/SitemapXML"));

// Lazy load oceanic article system
const OceanicRouter = lazy(() => import("./pages/oceanic/OceanicRouter"));
const OceanicBharat = lazy(() => import("./pages/oceanic/OceanicBharat"));

// Lazy load articles router
const ArticlesRouter = lazy(() => import("./pages/articles/ArticlesRouter"));

// Lazy load tools
const SanskritTranslator = lazy(() => import("./pages/SanskritTranslator"));
// TEXTS_READER_2026_09_27 - the published Sanskrit corpus (srangam_texts)
const TextsIndex = lazy(() => import("./pages/texts/TextsIndex"));
const TextReader = lazy(() => import("./pages/texts/TextReader"));
// CORPUS_READER_C5_2026_10_08: the working corpus for signed-in readers
const CorpusHome = lazy(() => import("./pages/corpus/CorpusHome"));
const CorpusDoc = lazy(() => import("./pages/corpus/CorpusDoc"));
// CORPUS_LIBRARY_C6_2026_10_08: the library's stories and names
const CorpusStories = lazy(() => import("./pages/corpus/CorpusStories"));
const CorpusNames = lazy(() => import("./pages/corpus/CorpusNames"));
// CORPUS_MEDIA_C8_2026_10_09: the pictures and the graphic novels
const CorpusImages = lazy(() => import("./pages/corpus/CorpusImages"));
const CorpusNovels = lazy(() => import("./pages/corpus/CorpusNovels"));
// CORNER_C9_2026_10_09: the Researchers' Corner and its anthologies
const CorpusCorner = lazy(() => import("./pages/corpus/CorpusCorner"));
const CorpusAnthology = lazy(() => import("./pages/corpus/CorpusAnthology"));
// STATE_LEARN_2026_10_09: Learn, the quests that teach every tool
const CorpusLearn = lazy(() => import("./pages/corpus/CorpusLearn"));
// EDITIONS_SITE_2026_10_18: the scholarly editions, open to everyone (public/scholarly/, written by the automaton)
const Editions = lazy(() => import("./pages/Editions"));
// RBAC_RESEARCHERS_2026_10_08: where an invited researcher lands
const InviteAccept = lazy(() => import("./pages/InviteAccept"));
const JyotishHoroscope = lazy(() => import("./pages/JyotishHoroscope"));

// Admin Pages
const MarkdownImport = lazy(() => import("./pages/admin/MarkdownImport"));
const Dashboard = lazy(() => import("./pages/admin/Dashboard"));
const ArticleManagement = lazy(() => import("./pages/admin/ArticleManagement"));
const TagManagement = lazy(() => import("./pages/admin/TagManagement"));
const CrossReferencesBrowser = lazy(() => import("./pages/admin/CrossReferencesBrowser"));
const CulturalTermsExplorer = lazy(() => import("./pages/admin/CulturalTermsExplorer"));
const ImportAnalytics = lazy(() => import("./pages/admin/ImportAnalytics"));
const PuranaReferences = lazy(() => import("./pages/admin/PuranaReferences"));
const GitHubSync = lazy(() => import("./pages/admin/GitHubSync"));
const ContextManagement = lazy(() => import("./pages/admin/ContextManagement"));
const DataHealth = lazy(() => import("./pages/admin/DataHealth"));
const GeographyMedia = lazy(() => import("./pages/admin/GeographyMedia"));
const CorpusCorrelations = lazy(() => import("./pages/admin/CorpusCorrelations"));
const Researchers = lazy(() => import("./pages/admin/Researchers"));   // RBAC_RESEARCHERS_2026_10_08
const Auth = lazy(() => import("./pages/Auth"));
// LOAD_W8_2026_10_07: admin only, so out of the entry bundle (with the sidebar it uses).
const AdminLayout = lazy(() => import("./components/admin/AdminLayout").then((m) => ({ default: m.AdminLayout })));

// Sources Pages
const Edicts = lazy(() => import("./pages/sources/Edicts"));
const Epigraphy = lazy(() => import("./pages/sources/Epigraphy"));
const TradeDocs = lazy(() => import("./pages/sources/TradeDocs"));
const SourcesIndex = lazy(() => import("./pages/sources/Index"));
const SanskritTerminology = lazy(() => import("./pages/sources/SanskritTerminology"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

// Optimized loading component
function PageLoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="flex items-center justify-center mb-4">
          <Loader2 className="animate-spin text-primary" size={32} />
        </div>
        <p className="text-muted-foreground">Loading sacred knowledge...</p>
      </div>
    </div>
  );
}

const App = () => (
  <ErrorBoundary>
    <HelmetProvider>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <LanguageProvider>
              <TooltipProvider>
                <Suspense fallback={null}>
                  <Toaster />
                  <Sonner />
                </Suspense>
                <SiteSchema />
                {import.meta.env.DEV && NarrationDebugPanel && (
                  <Suspense fallback={null}>
                    <NarrationDebugPanel />
                  </Suspense>
                )}
                <BrowserRouter>
                  <ScrollToTop />
                  <Layout>
                    <Suspense fallback={<PageLoadingFallback />}>
                    <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/begin-journey" element={<BeginJourney />} />
                  <Route path="/themes/ancient-india" element={<AncientIndia />} />
                  <Route path="/themes/indian-ocean-world" element={<IndianOceanWorld />} />
                  <Route path="/themes/scripts-inscriptions" element={<ScriptsInscriptions />} />
                  <Route path="/themes/geology-deep-time" element={<GeologyDeepTime />} />
                  <Route path="/themes/empires-exchange" element={<EmpiresExchange />} />
              <Route path="/field-notes" element={<FieldNotes />} />
              <Route path="/maps-data" element={<MapsData />} />
              <Route path="/data-viz" element={<DataVisualization />} />
              <Route path="/research-network" element={<ResearchNetwork />} />
              <Route path="/reading-room" element={<ReadingRoom />} />
              {/* TEXTS_READER_2026_09_27 */}
              <Route path="/texts" element={<TextsIndex />} />
              <Route path="/texts/:docCode" element={<TextReader />} />
              {/* EDITIONS_SITE_2026_10_18 */}
              <Route path="/editions" element={<Editions />} />
              {/* CORPUS_READER_C5_2026_10_08 */}
              <Route path="/corpus" element={<CorpusHome />} />
              {/* CORPUS_LIBRARY_C6_2026_10_08 */}
              <Route path="/corpus/stories" element={<CorpusStories />} />
              <Route path="/corpus/stories/:docCode/:storyId" element={<CorpusStories />} />
              <Route path="/corpus/names" element={<CorpusNames />} />
              <Route path="/corpus/names/:canonical" element={<CorpusNames />} />
              {/* CORPUS_MEDIA_C8_2026_10_09 */}
              <Route path="/corpus/images" element={<CorpusImages />} />
              <Route path="/corpus/novels" element={<CorpusNovels />} />
              <Route path="/corpus/novels/:novelId" element={<CorpusNovels />} />
              {/* CORNER_C9_2026_10_09 */}
              <Route path="/corpus/corner" element={<CorpusCorner />} />
              <Route path="/corpus/anthologies/new" element={<CorpusAnthology />} />
              <Route path="/corpus/anthologies/:collectionId" element={<CorpusAnthology />} />
              {/* STATE_LEARN_2026_10_09 */}
              <Route path="/corpus/learn" element={<CorpusLearn />} />
              <Route path="/corpus/:docCode" element={<CorpusDoc />} />
              
              {/* Sources Routes */}
              <Route path="/sources" element={<SourcesIndex />} />
              <Route path="/sources/index" element={<SourcesIndex />} />
              <Route path="/sources/edicts" element={<Edicts />} />
              <Route path="/sources/epigraphy" element={<Epigraphy />} />
              <Route path="/sources/trade-docs" element={<TradeDocs />} />
              <Route path="/sources/sanskrit-terminology" element={<SanskritTerminology />} />
                  <Route path="/sources-method" element={<SourcesMethod />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/about" element={<About />} />
                  <Route path="/brand" element={<Brand />} />
                  {/* Legacy root-level article routes → redirect to canonical /articles/:slug */}
                  <Route path="/monsoon-trade-clock" element={<Navigate to="/articles/monsoon-trade-clock" replace />} />
                  <Route path="/scripts-that-sailed" element={<Navigate to="/articles/scripts-that-sailed" replace />} />
                  <Route path="/scripts-that-sailed-ii" element={<Navigate to="/articles/scripts-that-sailed-ii" replace />} />
                  <Route path="/gondwana-to-himalaya" element={<Navigate to="/articles/gondwana-to-himalaya" replace />} />
                  <Route path="/indian-ocean-power-networks" element={<Navigate to="/articles/indian-ocean-power-networks" replace />} />
                  <Route path="/ashoka-kandahar-edicts" element={<Navigate to="/articles/ashoka-kandahar-edicts" replace />} />
                  <Route path="/reassessing-ashoka-legacy" element={<Navigate to="/articles/reassessing-ashoka-legacy" replace />} />
                  <Route path="/kutai-yupa-borneo" element={<Navigate to="/articles/kutai-yupa-borneo" replace />} />
                  <Route path="/maritime-memories-south-india" element={<Navigate to="/articles/maritime-memories-south-india" replace />} />
                  <Route path="/riders-on-monsoon" element={<Navigate to="/articles/riders-on-monsoon" replace />} />
                  <Route path="/pepper-and-bullion" element={<Navigate to="/articles/pepper-and-bullion" replace />} />
                  <Route path="/earth-sea-sangam" element={<Navigate to="/articles/earth-sea-sangam" replace />} />
                  <Route path="/jambudvipa-connected" element={<Navigate to="/articles/jambudvipa-connected" replace />} />
                  <Route path="/cosmic-island-sacred-land" element={<Navigate to="/articles/cosmic-island-sacred-land" replace />} />
                  <Route path="/stone-purana" element={<Navigate to="/articles/stone-purana" replace />} />
                  <Route path="/janajati-oral-traditions" element={<Navigate to="/articles/janajati-oral-traditions" replace />} />
                  <Route path="/sacred-tree-harvest-rhythms" element={<Navigate to="/articles/sacred-tree-harvest-rhythms" replace />} />
                  <Route path="/stone-song-and-sea" element={<Navigate to="/articles/stone-song-and-sea" replace />} />
                  <Route path="/chola-naval-raid" element={<Navigate to="/articles/chola-naval-raid" replace />} />
                  <Route path="/asura-exiles-indo-iranian" element={<Navigate to="/articles/asura-exiles-indo-iranian" replace />} />
                  <Route path="/sarira-and-atman-vedic-preservation" element={<Navigate to="/articles/sarira-and-atman-vedic-preservation" replace />} />
                  <Route path="/rishi-genealogies-vedic-tradition" element={<Navigate to="/articles/rishi-genealogies-vedic-tradition" replace />} />
                  <Route path="/reassessing-rigveda-antiquity" element={<Navigate to="/articles/reassessing-rigveda-antiquity" replace />} />
                  <Route path="/geomythology-land-reclamation" element={<Navigate to="/articles/geomythology-land-reclamation" replace />} />
                  <Route path="/dashanami-ascetics-sacred-geography" element={<Navigate to="/articles/dashanami-ascetics-sacred-geography" replace />} />
                  <Route path="/continuous-habitation-uttarapatha" element={<Navigate to="/articles/continuous-habitation-uttarapatha" replace />} />
                  <Route path="/somnatha-prabhasa-itihasa" element={<Navigate to="/articles/somnatha-prabhasa-itihasa" replace />} />
                  <Route path="/ringing-rocks-rhythmic-cosmology" element={<Navigate to="/articles/ringing-rocks-rhythmic-cosmology" replace />} />

                  {/* Articles browse page + dynamic article routes */}
                  <Route path="/articles/*" element={<ArticlesRouter />} />
                  
                  {/* Oceanic section remains separate */}
                  <Route path="/oceanic/*" element={<OceanicRouter />} />
                  
                  {/* Tools */}
                  <Route path="/sanskrit-translator" element={<SanskritTranslator />} />
                  <Route path="/jyotish-horoscope" element={<JyotishHoroscope />} />

<Route path="/themes/geology-deep-time/stone-purana" element={<Navigate to="/articles/stone-purana" replace />} />
                  <Route path="/themes/ancient-india/pepper-routes" element={<Navigate to="/articles/indian-ocean-power-networks" replace />} />
                  <Route path="/batch/bujang-nagapattinam-ocean" element={<BatchBujangNagapattinamOcean />} />
                  <Route path="/batch/muziris-kutai-ashoka" element={<BatchMuzirisKutaiAshoka />} />
                  <Route path="/research-submission" element={<ResearchSubmission />} />
                  <Route path="/partnership" element={<Partnership />} />
                  <Route path="/support-research" element={<SupportResearch />} />
                  <Route path="/sitemap" element={<Sitemap />} />
                  <Route path="/sitemap.xml" element={<SitemapXML />} />
                  
                  {/* Oceanic Bharat Landing Page */}
                  <Route path="/oceanic" element={<OceanicBharat />} />

                  {/* Auth Route */}
                  <Route path="/auth" element={<Auth />} />
                  {/* RBAC_RESEARCHERS_2026_10_08: research invitations */}
                  <Route path="/invite/:token" element={<InviteAccept />} />
                  
                  {/* Admin Routes with Layout - Protected */}
                  <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
                    <Route index element={<Dashboard />} />
                    <Route path="articles" element={<ArticleManagement />} />
                    <Route path="import" element={<MarkdownImport />} />
                    <Route path="github-sync" element={<GitHubSync />} />
                    <Route path="tags" element={<TagManagement />} />
                    <Route path="cross-refs" element={<CrossReferencesBrowser />} />
                    <Route path="cultural-terms" element={<CulturalTermsExplorer />} />
                    <Route path="purana-refs" element={<PuranaReferences />} />
                    <Route path="analytics" element={<ImportAnalytics />} />
                    <Route path="context" element={<ContextManagement />} />
                    <Route path="geography-media" element={<GeographyMedia />} />
                    <Route path="corpus-correlations" element={<CorpusCorrelations />} />
                    <Route path="data-health" element={<DataHealth />} />
                    <Route path="researchers" element={<Researchers />} />
                  </Route>
                  
                  <Route path="*" element={<NotFound />} />
                    </Routes>
                    </Suspense>
                </Layout>
              </BrowserRouter>
            </TooltipProvider>
            </LanguageProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </HelmetProvider>
  </ErrorBoundary>
);

export default App;
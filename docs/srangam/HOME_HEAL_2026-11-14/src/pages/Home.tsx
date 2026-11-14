import React, { useState, useMemo, Suspense, lazy } from "react";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";
import { ArticleCard } from "@/components/ui/ArticleCard";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getDisplayArticles } from "@/lib/multilingualArticleUtils";
import { mergeArticleSources, filterUnifiedArticles } from "@/lib/unifiedArticleUtils";
import { useAllArticles } from "@/hooks/useArticles";
import { useLanguage } from "@/components/language/LanguageProvider";
import { ArticleThemeChips } from "@/components/articles/ArticleThemeChips";
import { IconMonsoon, IconScript, IconBasalt, IconPort, IconEdict, IconDharmaChakra, IconSarnathLion, IconLotus, IconConch, IconOm } from "@/components/icons";
import { Link } from "react-router-dom";
import { ArrowRight, Waves, Mountain, BookOpen, Map, Users, Network, Loader2 } from "lucide-react";
// Phase 1.1 (2026-07-12): GeomythologySection transitively imports the full
// cultural-terms dataset (~610 KB pre-gzip) via CulturalTermTooltip. Home is
// eagerly imported in App.tsx, so a static import here put that dataset in
// the entry bundle for every visitor. Both below-the-fold sections are
// lazy-loaded instead; the entry chunk stays lean and the sections hydrate
// right after first paint.
const GeomythologySection = lazy(() => import("@/components/home/GeomythologySection"));
const ToolsSection = lazy(() => import("@/components/home/ToolsSection"));
// HOME_HEAL_2026_11_14: "Start here" - the texts themselves, in plain words (lazy, as the sections below).
const CorpusStartSection = lazy(() => import("@/components/home/CorpusStartSection"));
import { Skeleton } from "@/components/ui/skeleton";

export default function Home() {
  const { t } = useTranslation();
  const { currentLanguage } = useLanguage();
  
  // Article browsing state
  const [showAllArticles, setShowAllArticles] = useState(false);
  const [selectedThemes, setSelectedThemes] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<'recent' | 'oldest' | 'longest' | 'shortest' | 'title'>('recent');

  // Fetch database articles
  const { data: dbArticles, isLoading, isFetching, error: dbError, isDegraded, refetch } = useAllArticles(currentLanguage);

  // Merge JSON and database articles
  const allArticles = useMemo(() => {
    const jsonArticles = getDisplayArticles(currentLanguage);
    return mergeArticleSources(jsonArticles, dbArticles);
  }, [currentLanguage, dbArticles]);

  // Get filtered articles
  const filteredArticles = useMemo(() => 
    filterUnifiedArticles(allArticles, {
      themes: selectedThemes.length > 0 ? selectedThemes : undefined,
      sortBy,
      limit: showAllArticles ? undefined : 6
    }),
    [allArticles, selectedThemes, sortBy, showAllArticles]
  );

  const totalArticles = useMemo(() => 
    filterUnifiedArticles(allArticles, {
      themes: selectedThemes.length > 0 ? selectedThemes : undefined,
      sortBy
    }).length,
    [allArticles, selectedThemes, sortBy]
  );

  const handleThemeToggle = (theme: string) => {
    if (theme === 'all') {
      setSelectedThemes([]);
    } else {
      setSelectedThemes(prev =>
        prev.includes(theme)
          ? prev.filter(t => t !== theme)
          : [...prev, theme]
      );
    }
    setShowAllArticles(false); // Reset when changing filters
  };
  
  const themes = useMemo(() => [
    {
      title: t('themes.ancientIndia'),
      description: t('themes.ancientIndiaDesc'),
      path: "/themes/ancient-india",
      icon: IconSarnathLion,
      color: "text-saffron",
      bgPattern: "mandala-bg"
    },
    {
      title: t('themes.indianOcean'), 
      description: t('themes.indianOceanDesc'),
      path: "/themes/indian-ocean-world",
      icon: IconConch,
      color: "text-peacock-blue",
      bgPattern: "chakra-pattern"
    },
    {
      title: t('themes.scripts'),
      description: t('themes.scriptsDesc'),
      path: "/themes/scripts-inscriptions", 
      icon: IconOm,
      color: "text-indigo-dharma",
      bgPattern: "dharma-scroll"
    },
    {
      title: t('themes.geology'),
      description: t('themes.geologyDesc'),
      path: "/themes/geology-deep-time",
      icon: IconBasalt,
      color: "text-terracotta",
      bgPattern: "mandala-bg"
    },
    {
      title: t('themes.empires'),
      description: t('themes.empiresDesc'),
      path: "/themes/empires-exchange",
      icon: IconDharmaChakra,
      color: "text-turmeric",
      bgPattern: "chakra-pattern"
    }
  ], [t]);

  return (
    <div className="bg-background relative overflow-hidden">
      <Helmet>
        <title>Srangam — Histories of the Indian Ocean World</title>
        <meta name="description" content="Dharmic Scholarship for the Digital Age. Explore interconnected histories of the Indian Ocean through archaeology, epigraphy, Sanskrit literature, and deep time." />
        <link rel="canonical" href="https://srangam.nartiang.org/" />
        <meta property="og:title" content="Srangam — Histories of the Indian Ocean World" />
        <meta property="og:description" content="Dharmic Scholarship for the Digital Age — Exploring the interconnected histories of the Indian Ocean through archaeology, epigraphy, and deep time" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://srangam.nartiang.org/" />
        <meta property="og:image" content="https://srangam.nartiang.org/brand/og-image.png" />
      </Helmet>
      {/* Ocean-inspired Background Patterns */}
      <div className="fixed inset-0 ocean-waves opacity-60 pointer-events-none" />
      <div className="fixed top-0 right-0 w-96 h-96 ancient-navigation rounded-full opacity-20 pointer-events-none" />
      
      {/* Hero Section with Dharmic Aesthetics */}
      <section className="relative min-h-screen">
        {/* Hero Image Background with Sacred Overlays */}
        <div className="absolute inset-0">
          {/* Phase 1.2 (2026-07-12): WebP hero (172 KB) with PNG fallback
              (2.7 MB) — same 1536×1024 source pixels. Keep the preload in
              index.html pointed at the same WebP URL. */}
          <picture>
            <source srcSet="/images/hero_indian-ocean_aerial_21x9_v1.webp" type="image/webp" />
            <img
              src="/images/hero_indian-ocean_aerial_21x9_v1.png"
              alt="सागर - The sacred waters of the Indian Ocean connecting ancient civilizations"
              className="w-full h-full object-cover"
              width={2100}
              height={900}
              fetchPriority="high"
              decoding="async"
            />
          </picture>

          <div className="absolute inset-0 bg-gradient-to-b from-indigo-dharma/20 via-saffron/10 to-charcoal-om/80" />
          <div className="absolute inset-0 lotus-gradient opacity-20" />
        </div>
        
        {/* Optimized Sacred Symbols - Reduced Animation Load */}
        <div className="absolute top-20 left-10 animate-pulse-gentle opacity-20">
          <IconLotus size={32} className="text-lotus-pink" />
        </div>
        <div className="absolute top-32 right-16 animate-pulse-gentle opacity-25" style={{ animationDelay: '1s' }}>
          <IconOm size={28} className="text-saffron" />
        </div>
        <div className="absolute bottom-32 left-20 animate-slow-spin opacity-15" style={{ animationDelay: '2s' }}>
          <IconDharmaChakra size={40} className="text-turmeric" />
        </div>
        
        {/* Hero Content with Sanskrit Touches */}
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="animate-fade-in">
              {/* Sanskrit blessing above title */}
              <div className="text-saffron/80 text-lg mb-4 font-serif">
                {t('hero.sanskritBlessing')}
              </div>
              
              <h1 className="font-serif text-5xl lg:text-7xl font-bold text-sandalwood mb-6 drop-shadow-2xl tracking-wide">
                {t('hero.title')}
              </h1>
              
              {/* Sanskrit subtitle */}
              <div className="text-turmeric/90 text-xl mb-4 font-serif">
                {t('hero.sanskritSubtitle')}
              </div>
              
              <h2 className="font-serif text-2xl lg:text-3xl text-sandalwood/95 mb-8 max-w-3xl mx-auto drop-shadow-lg font-medium">
                {t('hero.subtitle')}
              </h2>
              <p className="text-lg lg:text-xl text-sandalwood/85 mb-12 max-w-2xl mx-auto leading-relaxed drop-shadow-md font-light">
                {t('hero.description')}
              </p>
            </div>
            
            {/* Optimized Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-6 justify-center">
              <Button asChild size="lg" className="bg-saffron hover:bg-saffron-light text-charcoal-om border-0 shadow-lg hover:shadow-saffron/20 transition-all duration-200 hover:scale-[1.02]">
                <Link to="/begin-journey">
                  <IconSarnathLion size={20} className="mr-2" />
                  {t('hero.beginJourney')}
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="border-2 border-sandalwood text-sandalwood hover:bg-sandalwood hover:text-charcoal-om shadow-lg hover:shadow-sandalwood/20 transition-all duration-200 hover:scale-[1.02] backdrop-blur-sm bg-indigo-dharma/20">
                <Link to="/about">
                  <IconLotus size={20} className="mr-2" />
                  {t('hero.aboutProject')}
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {/* Optimized Scroll Indicator */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-pulse-gentle">
          <div className="w-6 h-10 border-2 border-turmeric/60 rounded-full flex justify-center backdrop-blur-sm bg-indigo-dharma/20 shadow-md">
            <div className="w-1 h-3 bg-saffron/70 rounded-full mt-2 animate-pulse" />
          </div>
        </div>
      </section>

      {/* HOME_HEAL_2026_11_14: start here - the texts, the editions, the dynasties (lazy) */}
      <Suspense fallback={null}>
        <CorpusStartSection />
      </Suspense>

      {/* Featured Articles - Enhanced Browsing */}
      <section className="py-16 bg-sandalwood/20 relative">
        <div className="absolute inset-0 dharma-scroll opacity-30" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <IconConch size={48} className="text-peacock-blue om-pulse" />
            </div>
            <h2 className="font-serif text-3xl font-bold text-foreground mb-4">
              {t('sections.recentResearch')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-4">
              {t('sections.recentResearchDesc')}
            </p>
            {(() => {
              const filterActive = selectedThemes.length > 0;
              const lastUpdated = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
              if (!filterActive && !showAllArticles && filteredArticles.length < totalArticles) {
                // No filter, paginated preview: collapse the two counters into one honest line.
                return (
                  <p className="text-base sm:text-lg text-foreground mb-4">
                    Showing <span className="text-saffron font-semibold">{filteredArticles.length}</span>
                    {' '}of{' '}
                    <span className="text-saffron font-semibold">{totalArticles}</span> research articles
                    <span className="text-muted-foreground"> · Last updated {lastUpdated}</span>
                  </p>
                );
              }
              return (
                <>
                  <div className="flex items-center justify-center gap-6 mb-4">
                    <p className="text-2xl font-semibold text-foreground">
                      <span className="text-saffron">{totalArticles}</span> Research Articles
                    </p>
                    <span className="text-muted-foreground">•</span>
                    <p className="text-sm text-muted-foreground">Last updated: {lastUpdated}</p>
                  </div>
                  {filterActive && (
                    <p className="text-sm text-muted-foreground">
                      {filteredArticles.length} {t('filters.articlesShowing')}
                    </p>
                  )}
                </>
              );
            })()}

          </div>

          {/* Filter Chips */}
          <ArticleThemeChips 
            selectedThemes={selectedThemes}
            onThemeToggle={handleThemeToggle}
            articles={allArticles}
          />

          {/* Sort Dropdown */}
          <div className="flex justify-end mb-6">
            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">{t('sort.mostRecent')}</SelectItem>
                <SelectItem value="oldest">{t('sort.oldest')}</SelectItem>
                <SelectItem value="longest">{t('sort.longestReads')}</SelectItem>
                <SelectItem value="shortest">{t('sort.shortestReads')}</SelectItem>
                <SelectItem value="title">{t('sort.alphabetical')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Phase X.8.1 — Render-first, hydrate-second.
              Never block the JSON-backed corpus on a pending DB roundtrip. */}
          {isFetching && filteredArticles.length > 0 && (
            <div className="flex justify-end mb-3">
              <span className="inline-flex items-center gap-2 text-xs text-muted-foreground bg-muted/60 px-3 py-1 rounded-full">
                <Loader2 className="animate-spin" size={12} />
                Refreshing…
              </span>
            </div>
          )}
          {(isDegraded || (dbError && !isFetching)) && filteredArticles.length > 0 && (
            <div className="mb-4 text-xs text-muted-foreground bg-card border border-border rounded-md px-3 py-2 flex items-center justify-center gap-3">
              <span>Showing cached articles — syncing latest…</span>
              <button
                type="button"
                onClick={() => refetch()}
                className="text-saffron hover:underline font-medium"
              >
                Retry
              </button>
            </div>
          )}

          {filteredArticles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
              {filteredArticles.map((article, index) => (
                <div key={article.id} className="animate-fade-in" style={{ animationDelay: `${index * 0.1}s` }}>
                  <ArticleCard article={article} />
                </div>
              ))}
            </div>
          ) : isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-64 w-full rounded-lg" />
              ))}
            </div>
          ) : null}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {!showAllArticles && filteredArticles.length < totalArticles && (
              <Button 
                onClick={() => setShowAllArticles(true)}
                variant="outline" 
                size="lg" 
                className="border-2 border-ocean text-ocean hover:bg-ocean hover:text-cream transition-all duration-200 hover:scale-[1.02]"
              >
                <BookOpen size={20} className="mr-2" />
                {t('actions.showAll')} ({totalArticles} {t('filters.articles')})
              </Button>
            )}
            
            <Button asChild variant="outline" size="lg" className="border-2 border-saffron text-saffron hover:bg-saffron hover:text-charcoal-om transition-all duration-200 hover:scale-[1.02]">
              <Link to="/articles">
                <IconLotus size={20} className="mr-2" />
                {t('sections.viewAllResearch')}
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Featured Collections Section - विशेष संग्रह */}
      <section className="py-16 bg-turmeric/5 relative">
        <div className="absolute inset-0 chakra-pattern opacity-20" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-12">
            <div className="flex justify-center mb-4">
              <IconScript size={48} className="text-turmeric animate-pulse-gentle" />
            </div>
            <h2 className="font-serif text-3xl font-bold text-foreground mb-4">
              {t('sections.featuredCollections')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {t('sections.featuredCollectionsDesc')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Scripts & Trade Empire Collection */}
            <Link
              to="/batch/muziris-kutai-ashoka"
              className="group block p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 hover:border-saffron/50 relative overflow-hidden animate-fade-in"
            >
              <div className="absolute inset-0 manuscript-texture opacity-30" />
              <div className="relative z-10">
                <div className="flex items-center justify-center mb-6">
                  <div className="text-saffron animate-pulse-gentle">
                    <IconEdict size={40} />
                  </div>
                </div>
                <h3 className="font-serif text-xl font-bold text-foreground group-hover:text-saffron transition-colors mb-2 text-center">
                  {t('collections.scriptsTradeTitle')}
                </h3>
                <p className="text-sm text-muted-foreground mb-4 text-center">
                  {t('collections.scriptsTradeItems')}
                </p>
                <p className="text-sm text-muted-foreground leading-relaxed text-center">
                  {t('collections.scriptsTradeDesc')}
                </p>
                <div className="flex justify-center mt-4">
                  <ArrowRight size={20} className="text-saffron group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </Link>

            {/* Ocean Networks Collection */}
            <Link
              to="/batch/bujang-nagapattinam-ocean"
              className="group block p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 hover:border-peacock-blue/50 relative overflow-hidden animate-fade-in"
              style={{ animationDelay: '0.1s' }}
            >
              <div className="absolute inset-0 ocean-waves opacity-30" />
              <div className="relative z-10">
                <div className="flex items-center justify-center mb-6">
                  <div className="text-peacock-blue animate-pulse-gentle">
                    <IconPort size={40} />
                  </div>
                </div>
                <h3 className="font-serif text-xl font-bold text-foreground group-hover:text-peacock-blue transition-colors mb-2 text-center">
                  {t('collections.oceanNetworksTitle')}
                </h3>
                <p className="text-sm text-muted-foreground mb-4 text-center">
                  {t('collections.oceanNetworksItems')}
                </p>
                <p className="text-sm text-muted-foreground leading-relaxed text-center">
                  {t('collections.oceanNetworksDesc')}
                </p>
                <div className="flex justify-center mt-4">
                  <ArrowRight size={20} className="text-peacock-blue group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Research Network Section */}
      <section className="py-16 bg-background">
        <div className="max-w-4xl mx-auto px-4">
          <Link to="/research-network" className="group block p-10 bg-card rounded-lg border-2 border-peacock-blue/30 hover:border-peacock-blue hover:shadow-2xl transition-all">
            <div className="flex items-center justify-center mb-6">
              <Network className="text-peacock-blue" size={56} />
            </div>
            <h3 className="font-serif text-3xl font-bold text-center mb-4">
              Explore the Research Network
            </h3>
            <div className="grid md:grid-cols-3 gap-6 mb-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-saffron">474</div>
                <div className="text-sm text-muted-foreground">Connections</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-peacock-blue">22</div>
                <div className="text-sm text-muted-foreground">Articles</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-turmeric">6.5</div>
                <div className="text-sm text-muted-foreground">Avg Strength</div>
              </div>
            </div>
            <p className="text-center text-muted-foreground mb-4">
              Visualize how our research interconnects through themes, methods, and sources.
            </p>
            <div className="flex justify-center">
              <span className="text-peacock-blue font-medium group-hover:translate-x-2 transition-transform inline-flex items-center gap-2">
                Explore Interactive Network <ArrowRight size={20} />
              </span>
            </div>
          </Link>
        </div>
      </section>

      {/* Geomythology & Cultural Continuity Section (lazy, below the fold) */}
      <Suspense fallback={null}>
        <GeomythologySection />
      </Suspense>

      {/* Research Tools Section (lazy, below the fold) */}
      <Suspense fallback={null}>
        <ToolsSection />
      </Suspense>

      {/* Themes Grid - Dharmic Mandala Layout */}
      <section className="py-16 bg-background relative">
        <div className="absolute inset-0 ancient-navigation opacity-15" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-12">
            <div className="flex justify-center gap-4 mb-6">
              <IconDharmaChakra size={48} className="text-turmeric animate-slow-spin" />
            </div>
            <h2 className="font-serif text-3xl font-bold text-foreground mb-4">
              अनुसंधान विषयाः | Research Themes
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Explore our interdisciplinary approach to Indian Ocean studies through dharmic wisdom
            </p>
          </div>

          {/* First row - 3 themes in sacred triangle */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {themes.slice(0, 3).map((theme, index) => {
              const IconComponent = theme.icon;
              return (
                <Link
                  key={theme.path}
                  to={theme.path}
                  className={`group block p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 hover:border-primary/50 relative overflow-hidden animate-fade-in ${theme.bgPattern || ''}`}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <div className="absolute inset-0 opacity-5 pointer-events-none">
                    <div className={theme.bgPattern} />
                  </div>
                  <div className="relative z-10">
                    <div className="flex items-center justify-center mb-6">
                      <div className={`${theme.color} animate-pulse-gentle`}>
                        <IconComponent size={40} />
                      </div>
                    </div>
                    <h3 className="font-serif text-xl font-bold text-foreground group-hover:text-primary transition-colors mb-4 text-center">
                      {theme.title}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed text-center">
                      {theme.description}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Second row - 2 themes in sacred balance */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {themes.slice(3).map((theme, index) => {
              const IconComponent = theme.icon;
              return (
                <Link
                  key={theme.path}
                   to={theme.path}
                   className={`group block p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 hover:border-primary/50 relative overflow-hidden animate-fade-in ${theme.bgPattern || ''}`}
                   style={{ animationDelay: `${(index + 3) * 0.1}s` }}
                >
                  <div className="absolute inset-0 opacity-5 pointer-events-none">
                    <div className={theme.bgPattern} />
                  </div>
                  <div className="relative z-10">
                    <div className="flex items-center justify-center mb-6">
                      <div className={`${theme.color} animate-pulse-gentle`}>
                        <IconComponent size={40} />
                      </div>
                    </div>
                    <h3 className="font-serif text-xl font-bold text-foreground group-hover:text-primary transition-colors mb-4 text-center">
                      {theme.title}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed text-center">
                      {theme.description}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* Quick Links - Sacred Trinity */}
      <section className="py-16 bg-lotus-pink/10 relative">
        <div className="absolute inset-0 chakra-pattern opacity-10" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-12">
            <h2 className="font-serif text-3xl font-bold text-foreground mb-4">
              त्रिमार्ग | Sacred Paths
            </h2>
            <p className="text-lg text-muted-foreground">
              Three pillars of knowledge in the dharmic tradition
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Link to="/field-notes" className="group text-center p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 animate-fade-in relative overflow-hidden">
              <div className="absolute inset-0 manuscript-texture opacity-30" />
              <IconOm size={48} className="mx-auto text-saffron mb-6 group-hover:scale-105 transition-transform animate-pulse-gentle" />
              <h3 className="font-serif text-xl font-bold text-foreground mb-2">Field Notes</h3>
              <p className="text-muted-foreground mb-4">क्षेत्र अध्ययन</p>
              <p className="text-sm text-muted-foreground">Sacred fieldwork and revelations from the earth</p>
            </Link>

            <Link to="/maps-data" className="group text-center p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 animate-fade-in relative overflow-hidden" style={{ animationDelay: '0.1s' }}>
              <div className="absolute inset-0 chakra-pattern opacity-3" />
              <IconDharmaChakra size={48} className="mx-auto text-turmeric mb-6 group-hover:scale-105 transition-transform animate-slow-spin" />
              <h3 className="font-serif text-xl font-bold text-foreground mb-2">Maps & Data</h3>
              <p className="text-muted-foreground mb-4">भूगोल ज्ञान</p>
              <p className="text-sm text-muted-foreground">Sacred geography and cosmic visualizations</p>
            </Link>

            <Link to="/about" className="group text-center p-8 bg-card rounded-lg border border-border hover:shadow-lg transition-all duration-200 animate-fade-in relative overflow-hidden" style={{ animationDelay: '0.2s' }}>
              <div className="absolute inset-0 dharma-scroll opacity-3" />
              <IconLotus size={48} className="mx-auto text-lotus-pink mb-6 group-hover:scale-105 transition-transform animate-pulse-gentle" />
              <h3 className="font-serif text-xl font-bold text-foreground mb-2">About</h3>
              <p className="text-muted-foreground mb-4">आश्रम परिचय</p>
              <p className="text-sm text-muted-foreground">Our dharmic scholarly community and mission</p>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
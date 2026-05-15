import { useState, useEffect, useCallback, useRef } from 'react';
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import { useLang } from '../context/LanguageContext';
import { getDashboardLayout, updateDashboardLayout, resetDashboardLayout } from '../api/dashboard';
import DashboardHeader from '../components/dashboard/DashboardHeader';
import WidgetSettings from '../components/dashboard/WidgetSettings';
import MetricsManager from '../components/dashboard/MetricsManager';
import StreakWidget from '../components/dashboard/widgets/StreakWidget';
import MoodTrendsWidget from '../components/dashboard/widgets/MoodTrendsWidget';
import OnThisDayWidget from '../components/dashboard/widgets/OnThisDayWidget';
import HabitCheckInWidget from '../components/dashboard/widgets/HabitCheckInWidget';
import AISuggestionsWidget from '../components/dashboard/widgets/AISuggestionsWidget';
import SleepStatsWidget from '../components/dashboard/widgets/SleepStatsWidget';
import ConfirmDialog from '../components/ui/ConfirmDialog';

const ResponsiveGridLayout = GridLayout.WidthProvider(GridLayout.Responsive);

const DEFAULT_LAYOUT = {
  widgets: [
    { id: 'streak', x: 0, y: 0, w: 4, h: 2, enabled: true },
    { id: 'mood_trends', x: 4, y: 0, w: 8, h: 4, enabled: true },
    { id: 'on_this_day', x: 0, y: 2, w: 4, h: 4, enabled: true },
    { id: 'habit_checkin', x: 0, y: 6, w: 6, h: 3, enabled: true },
    { id: 'ai_suggestions', x: 6, y: 6, w: 6, h: 3, enabled: true },
    { id: 'sleep_stats', x: 0, y: 9, w: 12, h: 4, enabled: true },
  ],
};

export default function PersonalDashboardPage() {
  const { t } = useLang();
  const [widgets, setWidgets] = useState(DEFAULT_LAYOUT.widgets);
  const [isEditMode, setIsEditMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [selectedWidget, setSelectedWidget] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const saveTimeoutRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const res = await getDashboardLayout();
        if (cancelled) return;
        if (res.data.layout_config?.widgets) {
          setWidgets(res.data.layout_config.widgets);
        }
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load dashboard layout:', err);
        setWidgets(DEFAULT_LAYOUT.widgets);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true };
  }, []);

  useEffect(() => {
    document.title = `${t('dashboard.title')} — HeartBox`;
  }, [t]);

  const saveLayout = useCallback(async (widgetsToSave) => {
    try {
      await updateDashboardLayout({ widgets: widgetsToSave });
      setHasUnsavedChanges(false);
      window.dispatchEvent(new CustomEvent('api-success', {
        detail: { messageKey: 'dashboard.layoutSaved' },
      }));
    } catch (err) {
      console.error('Failed to save layout:', err);
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.saveFailed' },
      }));
    }
  }, []);

  const handleLayoutChange = useCallback((newLayout) => {
    if (!isEditMode || loading) return;

    const updatedWidgets = widgets.map(widget => {
      const layoutItem = newLayout.find(item => item.i === widget.id);
      if (layoutItem) {
        return {
          ...widget,
          x: layoutItem.x,
          y: layoutItem.y,
          w: layoutItem.w,
          h: layoutItem.h,
        };
      }
      return widget;
    });

    setWidgets(updatedWidgets);
    setHasUnsavedChanges(true);

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(() => {
      saveLayout(updatedWidgets);
    }, 1000);
  }, [isEditMode, loading, widgets, saveLayout]);

  const handleReset = async () => {
    setShowResetConfirm(false);
    try {
      await resetDashboardLayout();
      // reload by re-running the effect via state reset
      const res = await getDashboardLayout();
      if (res.data.layout_config?.widgets) {
        setWidgets(res.data.layout_config.widgets);
      } else {
        setWidgets(DEFAULT_LAYOUT.widgets);
      }
      setHasUnsavedChanges(false);
      window.dispatchEvent(new CustomEvent('api-success', {
        detail: { messageKey: 'dashboard.layoutReset' },
      }));
    } catch (err) {
      console.error('Failed to reset layout:', err);
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.resetFailed' },
      }));
    }
  };

  const handleToggleWidget = (widgetId) => {
    const updatedWidgets = widgets.map(w =>
      w.id === widgetId ? { ...w, enabled: !w.enabled } : w
    );
    setWidgets(updatedWidgets);
    setHasUnsavedChanges(true);
    saveLayout(updatedWidgets);
  };

  const handleOpenSettings = (widgetId) => {
    const widget = widgets.find(w => w.id === widgetId);
    setSelectedWidget(widget);
    setShowSettings(true);
  };

  const renderWidget = (widget) => {
    if (!widget.enabled) return null;

    const commonProps = {
      widgetId: widget.id,
      isEditMode,
      onSettings: () => handleOpenSettings(widget.id),
    };

    switch (widget.id) {
      case 'streak':
        return <StreakWidget key={widget.id} {...commonProps} />;
      case 'mood_trends':
        return <MoodTrendsWidget key={widget.id} {...commonProps} />;
      case 'on_this_day':
        return <OnThisDayWidget key={widget.id} {...commonProps} />;
      case 'habit_checkin':
        return <HabitCheckInWidget key={widget.id} {...commonProps} />;
      case 'ai_suggestions':
        return <AISuggestionsWidget key={widget.id} {...commonProps} />;
      case 'sleep_stats':
        return <SleepStatsWidget key={widget.id} {...commonProps} />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-orange-500 border-t-transparent"></div>
      </div>
    );
  }

  // Convert widgets to layout format for react-grid-layout
  const layoutLg = widgets.map(w => ({
    i: w.id,
    x: w.x,
    y: w.y,
    w: w.w,
    h: w.h,
  }));

  // Responsive breakpoints
  const layouts = {
    lg: layoutLg,
    md: widgets.map(w => ({
      i: w.id,
      x: w.x >= 4 ? 0 : w.x,
      y: w.y,
      w: Math.min(w.w, 8),
      h: w.h,
    })),
    sm: widgets.map((w, idx) => ({
      i: w.id,
      x: 0,
      y: idx,
      w: 1,
      h: w.h,
    })),
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <DashboardHeader
        isEditMode={isEditMode}
        onToggleEdit={() => setIsEditMode(!isEditMode)}
        onReset={() => setShowResetConfirm(true)}
        onManageMetrics={() => setShowMetrics(true)}
        onSave={() => saveLayout(widgets)}
        hasUnsavedChanges={hasUnsavedChanges}
      />

      <ResponsiveGridLayout
        className="layout"
        layouts={layouts}
        breakpoints={{ lg: 1024, md: 768, sm: 0 }}
        cols={{ lg: 12, md: 8, sm: 1 }}
        rowHeight={60}
        onLayoutChange={(layout) => handleLayoutChange(layout)}
        isDraggable={isEditMode}
        isResizable={isEditMode}
        draggableHandle=".drag-handle"
        compactType="vertical"
        margin={[24, 24]}
        containerPadding={[0, 0]}
      >
        {widgets.filter(w => w.enabled).map(widget => (
          <div key={widget.id} className="dashboard-widget">
            {renderWidget(widget)}
          </div>
        ))}
      </ResponsiveGridLayout>

      {/* Modals */}
      <WidgetSettings
        widget={selectedWidget}
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        onToggle={handleToggleWidget}
      />

      <MetricsManager
        isOpen={showMetrics}
        onClose={() => setShowMetrics(false)}
      />

      <ConfirmDialog
        isOpen={showResetConfirm}
        onClose={() => setShowResetConfirm(false)}
        onConfirm={handleReset}
        title={t('dashboard.resetConfirmTitle')}
        message={t('dashboard.resetConfirmMessage')}
        confirmText={t('common.confirm')}
        cancelText={t('common.cancel')}
      />
    </div>
  );
}

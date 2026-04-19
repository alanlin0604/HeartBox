import { useEffect } from 'react';
import { useLang } from '../context/LanguageContext';
import HabitTracker from '../components/HabitTracker';

export default function HabitsPage() {
  const { t } = useLang();

  useEffect(() => {
    document.title = `${t('habit.title')} — ${t('app.name')}`;
  }, [t]);

  return <HabitTracker />;
}

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { trpc } from '@/lib/trpc';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { AlertCircle, Video, X } from 'lucide-react';
import { toast } from 'sonner';

const JAM_TEAM_ID = import.meta.env.VITE_JAM_TEAM_ID?.trim();

function loadJamRecorder(): void {
  if (!JAM_TEAM_ID || typeof document === 'undefined') return;
  if (document.querySelector('script[data-jam-recorder]')) return;
  const s = document.createElement('script');
  s.src = 'https://js.jam.dev/recorder.js';
  s.async = true;
  s.dataset.jamRecorder = '1';
  s.dataset.jamTeamId = JAM_TEAM_ID;
  document.head.appendChild(s);
}

interface BugReportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function BugReportModal({ isOpen, onClose }: BugReportModalProps) {
  const { t } = useTranslation();
  useEffect(() => {
    if (isOpen) loadJamRecorder();
  }, [isOpen]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitBugReportMutation = trpc.bugReports.submitBugReport.useMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim() || !description.trim()) {
      toast.error(t('feedback.feedbackError'));
      return;
    }

    setIsSubmitting(true);
    try {
      await submitBugReportMutation.mutateAsync({
        title: title.trim(),
        description: description.trim(),
        severity,
        url: window.location.href,
        userAgent: navigator.userAgent,
      });

      toast.success(t('feedback.feedbackSubmitted'));
      setTitle('');
      setDescription('');
      setSeverity('medium');
      onClose();
    } catch {
      toast.error(t('feedback.feedbackError'));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card text-card-foreground rounded-lg shadow-lg max-w-md w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-bold">{t('bugReport.title')}</h2>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-6 w-6 p-0">
            <X className="w-4 h-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">{t('bugReport.titleLabel')}</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('bugReport.titlePlaceholder')}
              className="bg-background text-foreground border-border"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">{t('bugReport.descriptionLabel')}</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('bugReport.descriptionPlaceholder')}
              className="bg-background text-foreground border-border min-h-24"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">{t('bugReport.severityLabel')}</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as typeof severity)}
              className="w-full px-3 py-2 bg-background text-foreground border border-border rounded text-sm"
              disabled={isSubmitting}
            >
              <option value="low">{t('bugReport.severity.low')}</option>
              <option value="medium">{t('bugReport.severity.medium')}</option>
              <option value="high">{t('bugReport.severity.high')}</option>
              <option value="critical">{t('bugReport.severity.critical')}</option>
            </select>
          </div>

          {JAM_TEAM_ID && (
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Video className="w-3 h-3" />
              可使用 Jam 錄影回報 — 點右下角 Jam 浮動按鈕
            </p>
          )}

          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              className="bg-accent text-accent-foreground hover:bg-accent/90"
              disabled={isSubmitting}
            >
              {isSubmitting ? t('bugReport.submitting') : t('bugReport.submit')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
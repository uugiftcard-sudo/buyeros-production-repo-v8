// components/ConfirmModal.tsx
'use client';

import { useEffect, useRef } from 'react';

interface ConfirmModalProps {
  open: boolean;
  title: string;
  body?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'default' | 'danger';
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  open,
  title,
  body,
  confirmLabel = '確認',
  cancelLabel = '取消',
  variant = 'default',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      ref={overlayRef}
      onClick={e => { if (e.target === overlayRef.current) onCancel(); }}
    >
      <div className="modal-box" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal-header">
          <h3 id="modal-title">{title}</h3>
          <button className="modal-close" onClick={onCancel} aria-label="關閉">✕</button>
        </div>
        {body && <div className="modal-body">{body}</div>}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </button>
          <button
            className={`btn ${variant === 'danger' ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? '處理中...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

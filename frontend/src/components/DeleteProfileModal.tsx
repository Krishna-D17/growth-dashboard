import React from 'react';

interface DeleteProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  username: string;
  platform: string;
  displayName?: string | null;
  isDeleting?: boolean;
}

export const DeleteProfileModal: React.FC<DeleteProfileModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  username,
  platform,
  displayName,
  isDeleting = false,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
        <div className="modal-header" style={{ borderColor: 'var(--color-danger-border, #fecaca)' }}>
          <h3 className="modal-title" style={{ color: 'var(--color-danger, #ef4444)' }}>
            ⚠️ Delete Target?
          </h3>
          <button type="button" className="btn-close" onClick={onClose} disabled={isDeleting}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <p style={{ marginBottom: '1rem', fontWeight: 500 }}>
            Are you sure you want to delete:
          </p>

          <div
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: 'var(--bg-card-hover, #f8fafc)',
              borderRadius: '8px',
              borderLeft: '4px solid var(--color-danger, #ef4444)',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>@{username}</div>
            <div style={{ color: 'var(--text-muted, #64748b)', fontSize: '0.9rem' }}>
              {platform.toUpperCase()} {displayName ? `— ${displayName}` : ''}
            </div>
          </div>

          <p style={{ marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary, #475569)' }}>
            This will permanently remove:
          </p>
          <ul
            style={{
              margin: '0 0 1.25rem 1.25rem',
              padding: 0,
              fontSize: '0.9rem',
              lineHeight: '1.6',
              color: 'var(--text-secondary, #475569)',
            }}
          >
            <li>profile snapshots</li>
            <li>collected posts</li>
            <li>post snapshots</li>
            <li>collection history</li>
            <li>collection errors</li>
            <li>anomaly history</li>
            <li>scheduled collection for this target</li>
          </ul>

          <p style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-danger, #ef4444)' }}>
            This action cannot be undone.
          </p>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isDeleting}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={onConfirm}
            disabled={isDeleting}
            style={{
              backgroundColor: '#ef4444',
              color: '#ffffff',
              borderColor: '#dc2626',
              fontWeight: 600,
            }}
          >
            {isDeleting ? 'Deleting Target...' : 'Delete Target'}
          </button>
        </div>
      </div>
    </div>
  );
};

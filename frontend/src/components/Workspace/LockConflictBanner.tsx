import React from 'react';

interface Props {
  lockState: 'ACQUIRING' | 'LOCKED' | 'READONLY_CONFLICT';
}

export const LockConflictBanner: React.FC<Props> = ({ lockState }) => {
  if (lockState !== 'READONLY_CONFLICT') return null;

  return (
    <div style={{
      width: '100%',
      backgroundColor: '#fffbe6',
      borderBottom: '1px solid #ffe58f',
      color: '#d48806',
      padding: '8px 24px',
      textAlign: 'center',
      fontSize: '14px',
      fontWeight: 500,
      zIndex: 10
    }}>
      ⚠️ 当前公文正被其他人编辑，或您已失去编辑锁，现处于只读模式。
    </div>
  );
};

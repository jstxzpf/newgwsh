import React from 'react';

interface Props {
  lockState: 'ACQUIRING' | 'LOCKED' | 'READONLY_CONFLICT';
  isImmutable?: boolean;
}

export const LockConflictBanner: React.FC<Props> = ({ lockState, isImmutable }) => {
  const isConflict = lockState === 'READONLY_CONFLICT';

  if (isConflict) {
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
        ⚠️ 当前公文正被其他人编辑，现处于只读模式。
      </div>
    );
  }

  if (isImmutable) {
    return (
      <div style={{
        width: '100%',
        backgroundColor: '#e6f4ff',
        borderBottom: '1px solid #91caff',
        color: '#0958d9',
        padding: '8px 24px',
        textAlign: 'center',
        fontSize: '14px',
        fontWeight: 500,
        zIndex: 10
      }}>
        ℹ️ 公文已归档或处于审批流转中，不可编辑。
      </div>
    );
  }

  return null;
};

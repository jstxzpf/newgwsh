import React from 'react';
import { ConfigProvider } from 'antd';
import { taixingTheme } from './theme/themeConfig';
import { AntiLeakWatermark } from './components/Security/AntiLeakWatermark';
import { Workspace } from './pages/Workspace';
import { useAuthStore } from './store/useAuthStore';
import './styles/global.css';

function App() {
  const userInfo = useAuthStore(state => state.userInfo);

  return (
    <ConfigProvider theme={taixingTheme}>
      {userInfo && <AntiLeakWatermark username={userInfo.username} department={userInfo.deptName} />}
      <Workspace />
    </ConfigProvider>
  );
}

export default App;

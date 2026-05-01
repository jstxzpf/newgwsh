import { ThemeConfig } from 'antd';

export const TAIXING_TOKENS: ThemeConfig = {
  token: {
    colorPrimary: '#003366',
    colorInfo: '#003366',
    borderRadius: 4,
    fontFamily: '"方正仿宋_GBK", "FZFS", "仿宋_GB2312", "仿宋", "FangSong", "STFangsong", "华文仿宋", "Noto Serif CJK SC", serif',
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      siderBg: '#003366',
    },
    Menu: {
      darkItemBg: '#003366',
      darkItemSelectedBg: '#002244',
    },
    Button: {
      borderRadius: 2,
    },
  },
};

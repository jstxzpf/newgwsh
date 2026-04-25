import type { ThemeConfig } from 'antd';

export const taixingTheme: ThemeConfig = {
  token: {
    colorPrimary: '#003366', // 政务蓝
    colorBgBase: '#fcfcfc',  // 珍珠白底色
    colorBgLayout: '#f0f2f5',// 空间底色
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
    borderRadius: 4,
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      siderBg: '#003366',
    }
  }
};

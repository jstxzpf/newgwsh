export const countPureText = (markdownText: string): number => {
  if (!markdownText) return 0;
  
  // 1. 预处理：剔除 Markdown 语法标记
  let text = markdownText
    .replace(/!\[.*?\]\(.*?\)/g, '') // 图片
    .replace(/\[.*?\]\(.*?\)/g, '')  // 链接
    .replace(/[#*`_~>\[\]()-]/g, '') // 常用符号
    .replace(/\s+/g, '');            // 所有空白符
  
  // 2. 核心过滤：仅保留中文字符和英文字母
  // \u4e00-\u9fa5 是基本汉字区块
  // [a-zA-Z] 是英文字母
  const matches = text.match(/[\u4e00-\u9fa5a-zA-Z]/g);
  
  return matches ? matches.length : 0;
};

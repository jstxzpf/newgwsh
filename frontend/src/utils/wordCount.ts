export const countPureText = (markdownText: string): number => {
  if (!markdownText) return 0;
  // 简单剔除常见 markdown 符号
  let text = markdownText
    .replace(/[#*`_~>\[\]()-]/g, '')
    .replace(/!\[.*?\]\(.*?\)/g, '')
    .replace(/\[.*?\]\(.*?\)/g, '')
    .replace(/\s+/g, '');
  
  // 剔除标点符号 (中文+英文)
  text = text.replace(/[.,/#!$%^&*;:{}=\-_`~()'"<>\?。，、；：？！…—·（）《》〈〉【】『』「」]/g, '');
  return text.length;
};

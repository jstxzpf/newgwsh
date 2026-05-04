/**
 * 泰兴调查队公文字数统计引擎
 * 口径：剔除 Markdown 语法标记（#、*、>、[]()、``` 等）后的纯中英文字符数
 */
export function countWords(markdown: string): number {
  if (!markdown) return 0;

  // 1. 剔除代码块
  let text = markdown.replace(/```[\s\S]*?```/g, '');
  
  // 2. 剔除图片和链接标记，保留文本
  text = text.replace(/!\[.*?\]\(.*?\)/g, '');
  text = text.replace(/\[(.*?)\]\(.*?\)/g, '$1');
  
  // 3. 剔除标题符、引用符、分隔线
  text = text.replace(/^(#+|\s*>\s*|-{3,}|_+|\*+)/gm, '');
  
  // 4. 剔除粗体、斜体、删除线标记
  text = text.replace(/(\*\*|__|\*|_|~~)/g, '');
  
  // 5. 统计中文字符、英文字母及数字（不计空格和特殊符号）
  const match = text.match(/[\u4e00-\u9fa5]|\w/g);
  
  return match ? match.length : 0;
}
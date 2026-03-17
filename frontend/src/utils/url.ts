export function normalizeClueUrl(url?: string, source?: string): string | undefined {
  if (!url) return url;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  if (url.startsWith('//')) return `https:${url}`;
  if (url.startsWith('/')) {
    const map: Record<string, string> = {
      sogou: 'https://www.sogou.com',
      wechat: 'https://weixin.sogou.com',
      baidu: 'https://www.baidu.com',
      bing: 'https://cn.bing.com'
    };
    const base = map[source || ''] || 'https://www.sogou.com';
    return `${base}${url}`;
  }
  // Fallback for urls missing scheme
  return `https://${url}`;
}

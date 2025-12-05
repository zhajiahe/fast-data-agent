/**
 * 日期格式化工具函数
 */

/**
 * 解析后端返回的日期字符串，处理时区问题
 * @param dateString 日期字符串
 * @returns Date 对象
 */
export const parseBackendDate = (dateString: string): Date => {
  // 如果时间字符串没有时区标识（Z、+、-），自动添加 'Z' 表示 UTC
  if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
    return new Date(`${dateString}Z`);
  }
  return new Date(dateString);
};

/**
 * 格式化时间为 HH:MM 格式（中国时区）
 * @param dateString 日期字符串
 * @returns 格式化后的时间字符串
 */
export const formatTime = (dateString: string): string => {
  try {
    const date = parseBackendDate(dateString);
    if (Number.isNaN(date.getTime())) {
      return '时间未知';
    }
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Shanghai',
    });
  } catch (e) {
    console.error('Error formatting time:', dateString, e);
    return '时间未知';
  }
};

/**
 * 格式化日期为 M/D 格式（中国时区）
 * @param dateString 日期字符串
 * @returns 格式化后的日期字符串
 */
export const formatDate = (dateString: string): string => {
  try {
    const date = parseBackendDate(dateString);
    if (Number.isNaN(date.getTime())) {
      return '日期未知';
    }
    return date.toLocaleDateString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      timeZone: 'Asia/Shanghai',
    });
  } catch (e) {
    console.error('Error formatting date:', dateString, e);
    return '日期未知';
  }
};

/**
 * 格式化完整日期时间（中国时区）
 * @param dateString 日期字符串
 * @returns 格式化后的日期时间字符串
 */
export const formatDateTime = (dateString: string): string => {
  try {
    const date = parseBackendDate(dateString);
    if (Number.isNaN(date.getTime())) {
      return '时间未知';
    }
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Shanghai',
    });
  } catch (e) {
    console.error('Error formatting datetime:', dateString, e);
    return '时间未知';
  }
};

/**
 * 获取相对时间描述（如：刚刚、5分钟前、1小时前）
 * @param dateString 日期字符串
 * @returns 相对时间描述
 */
export const getRelativeTime = (dateString: string): string => {
  try {
    const date = parseBackendDate(dateString);
    if (Number.isNaN(date.getTime())) {
      return '时间未知';
    }

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return '刚刚';
    if (diffMin < 60) return `${diffMin}分钟前`;
    if (diffHour < 24) return `${diffHour}小时前`;
    if (diffDay < 7) return `${diffDay}天前`;

    // 超过7天显示具体日期
    return formatDate(dateString);
  } catch (e) {
    console.error('Error getting relative time:', dateString, e);
    return '时间未知';
  }
};

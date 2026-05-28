export const APP_VERSION = import.meta.env.VITE_APP_VERSION || 'NORMAL';

export const isNormal = APP_VERSION === 'NORMAL';
export const isLite = APP_VERSION === 'LITE';
export const isUltraLite = APP_VERSION === 'ULTRALITE';

/**
 * Utility functions for JARVIS HUD
 */

// Generate safe UUID for components
export const safeUUID = (): string => 
  `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;

// Clamp percentage values
export const clampPercent = (value: number): number => 
  Math.max(0, Math.min(100, value || 0));

// Format time in Swedish locale
export const formatTime = (): string => 
  new Date().toLocaleTimeString("sv-SE", { 
    hour: "2-digit", 
    minute: "2-digit" 
  });

// Check if browser supports Speech Recognition
export const supportsSpeechRecognition = (): boolean => {
  if (typeof window === 'undefined') return false;
  return !!(window.webkitSpeechRecognition || window.SpeechRecognition);
};

// Get Speech Recognition constructor
export const getSpeechRecognition = () => {
  if (typeof window === 'undefined') return null;
  return window.webkitSpeechRecognition || window.SpeechRecognition;
};

// Debounce function for performance
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Throttle function for animations
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

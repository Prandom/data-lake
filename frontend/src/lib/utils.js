import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind classes with conflict resolution.
 * cn('px-2 py-1', condition && 'px-4') → 'py-1 px-4'
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

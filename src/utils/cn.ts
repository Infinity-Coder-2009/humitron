import { clsx } from 'clsx'

export function cn(...inputs: (string | boolean | undefined | null | Record<string, boolean>)[]): string {
  return clsx(inputs)
}
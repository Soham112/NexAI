import { Redis } from '@upstash/redis'

// Initialize the Redis client
// This will reuse the connection in serverless environments
let redisClient: Redis | null = null

function getRedisClient(): Redis | null {
  if (redisClient) {
    return redisClient
  }

  const url = process.env.UPSTASH_REDIS_REST_URL
  const token = process.env.UPSTASH_REDIS_REST_TOKEN

  if (!url || !token) {
    console.warn('Upstash Redis environment variables are not set')
    return null
  }

  try {
    redisClient = new Redis({
      url,
      token,
    })
    return redisClient
  } catch (error) {
    console.warn('Failed to initialize Redis client:', error)
    return null
  }
}

/**
 * Gets a value from the Redis cache
 * @param key - The cache key
 * @returns The cached value or null if not found
 */
export async function getCache(key: string): Promise<string | null> {
  const client = getRedisClient()
  
  if (!client) {
    console.warn('Redis client not available, skipping cache get')
    return null
  }

  try {
    const value = await client.get(key)
    return value as string | null
  } catch (error) {
    console.warn('Redis get error:', error)
    return null
  }
}

/**
 * Sets a value in the Redis cache with a 6 hour TTL
 * @param key - The cache key
 * @param value - The value to cache
 */
export async function setCache(key: string, value: string): Promise<void> {
  const client = getRedisClient()
  
  if (!client) {
    console.warn('Redis client not available, skipping cache set')
    return
  }

  try {
    // Set TTL to 6 hours (21600 seconds)
    await client.setex(key, 21600, value)
  } catch (error) {
    console.warn('Redis set error:', error)
  }
}

/**
 * Normalizes a string to create a consistent cache key
 * - Trims whitespace
 * - Converts to lowercase
 * - Removes punctuation
 * - Normalizes multiple spaces to single space
 * This ensures slight variations of the same question map to the same cache key
 * @param input - The string to normalize
 * @returns The normalized string
 */
export function normalizeCacheKey(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[.,!?'"\\]/g, '')
    .replace(/\s+/g, ' ')
}


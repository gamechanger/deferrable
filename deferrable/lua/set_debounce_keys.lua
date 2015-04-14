local lastPushKey = KEYS[1]
local debounceKey = KEYS[2]

local now = ARGV[1]
local secondsToDelay = ARGV[2]
local debounceSeconds = ARGV[3]

redis.call('set', lastPushKey, now + secondsToDelay, 'PX', 2 * debounceSeconds * 1000)
redis.call('set', debounceKey, '_', 'PX', debounceSeconds * 1000)

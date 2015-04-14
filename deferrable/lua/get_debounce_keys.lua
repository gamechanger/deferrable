local lastPushKey = KEYS[1]
local debounceKey = KEYS[2]

return {redis.call('get', lastPushKey), redis.call('get', debounceKey)}

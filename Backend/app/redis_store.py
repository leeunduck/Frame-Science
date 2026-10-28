from redis import Redis
from .config import get_settings

settings = get_settings()
redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3)
def key(suffix):
    return settings.redis_prefix + suffix

def revoke_all(user_id):
    """계정별 Set과 Refresh 키를 원자적으로 삭제해 폐기 중 누락을 방지한다."""
    index = key(f'sessions:{user_id}')
    redis.eval("""
    local members = redis.call('SMEMBERS', KEYS[1])
    for _, member in ipairs(members) do redis.call('DEL', member) end
    redis.call('DEL', KEYS[1])
    return #members
    """, 1, index)

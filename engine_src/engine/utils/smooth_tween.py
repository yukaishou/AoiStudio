import time


def linear(t: float) -> float:
    """线性"""
    return t


def ease_in_out(t: float) -> float:
    """平滑缓入缓出 (Hermite S曲线)"""
    return 3 * t * t - 2 * t * t * t


def ease_out_cubic(t: float) -> float:
    """缓出"""
    return 1 - (1 - t) ** 3


def ease_in_cubic(t: float) -> float:
    """缓入"""
    return t ** 3


def smoothstep(t: float) -> float:
    """内置smoothstep"""
    return t * t * (3 - 2 * t)


def lerp(a: float, b: float, t: float) -> float:
    """基础线性插值"""
    return a + (b - a) * t


def get_tween_value(start: float, target: float,
                    start_time: float, duration: float,
                    ease_func, now=None) -> tuple[float, bool]:
    """
    根据时间计算当前插值值
    :return: (当前数值, 是否完成)
    """
    if now is None:
        now = time.perf_counter()
    elapsed = now - start_time
    t = min(elapsed / duration, 1.0)
    smooth_t = ease_func(t)
    val = lerp(start, target, smooth_t)
    finished = t >= 1.0
    return val, finished


def lerp2(sx, sy, tx, ty, start_time, duration, ease_func, now=None):
    """二维坐标插值 (x,y, finished)"""
    if now is None:
        now = time.perf_counter()
    elapsed = now - start_time
    t = min(elapsed / duration, 1.0)
    st = ease_func(t)
    x = lerp(sx, tx, st)
    y = lerp(sy, ty, st)
    finished = t >= 1.0
    return x, y, finished



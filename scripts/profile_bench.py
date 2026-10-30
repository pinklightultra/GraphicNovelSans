"""Performance benchmark for GraphicNovelSans hot paths."""
import cProfile
import pstats
import numpy as np
from graphicnovelsans.trace import trace_mask_to_contours, rdp_simplify
from graphicnovelsans.kern import compute_edge_profile, compute_flanks, compute_kern_pairs
from graphicnovelsans.transform import dilate_with_counter_protection
from graphicnovelsans.segment import connected_components


def benchmark_trace():
    """Benchmark contour tracing on a realistic glyph."""
    mask = np.zeros((100, 100), dtype=bool)
    mask[20:80, 20:80] = True
    mask[30:70, 30:70] = False
    mask[25:45, 50:60] = True
    mask[55:75, 50:60] = True
    
    for _ in range(100):
        contours = trace_mask_to_contours(mask, scale=10.0, baseline_offset=50.0)


def benchmark_dilate():
    """Benchmark dilation with counter protection."""
    mask = np.zeros((100, 100), dtype=bool)
    mask[20:80, 20:80] = True
    mask[30:70, 30:70] = False
    
    for _ in range(100):
        dilated = dilate_with_counter_protection(mask, radius=2)


def benchmark_kern():
    """Benchmark kerning calculation."""
    profiles = {}
    for i in range(26):
        char = chr(ord('A') + i)
        contours = [[(i*10, 0), (i*10+10, 0), (i*10+10, 100), (i*10, 100)]]
        profile = compute_edge_profile(contours, advance=500, descender=-220, ascender=800)
        profiles[char] = profile
    
    for _ in range(100):
        kerns = compute_kern_pairs(profiles)


def benchmark_segment():
    """Benchmark connected components on a noisy sheet."""
    mask = np.random.rand(500, 500) > 0.95
    mask[100:200, 100:200] = True
    mask[300:400, 300:400] = True
    
    for _ in range(50):
        labels, comps = connected_components(mask)


if __name__ == "__main__":
    print("Running benchmarks...")
    
    funcs = [
        ("trace", benchmark_trace),
        ("dilate", benchmark_dilate),
        ("kern", benchmark_kern),
        ("segment", benchmark_segment),
    ]
    
    for name, func in funcs:
        print(f"\n--- {name.upper()} ---")
        profiler = cProfile.Profile()
        profiler.enable()
        func()
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)

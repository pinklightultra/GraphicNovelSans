# API Reference: Segment Module

Performs connected component analysis, noise filtering, and line clustering to isolate characters from comic artwork.

## Functions

### `connected_components(mask)`
Labels 4-connected ink components.
- **Returns**: `(labels_array, list_of_components)` where each component has `id`, `x0`, `y0`, `x1`, `y1`, `pixels`.

### `tighten(mask)`
Crops mask tightly to its nonzero bounding box.
- **Returns**: Cropped boolean array.

### `drop_rules(comps, width, height, max_w_frac=0.55, max_h_frac=0.42)`
Filters out panel borders and balloon contours spanning most of the canvas.
- **Returns**: Filtered list of components.

### `filter_noise(comps, min_pixels=8)`
Removes tiny dust specks and paper grain.
- **Returns**: Filtered list.

### `group_lines(comps)`
Clusters components into text lines by bottom-edge alignment.
- **Returns**: List of line objects with `base`, `items`, `x0`, `x1`, `y0`, `y1`.
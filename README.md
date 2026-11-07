
# Svg2Pattern

**Svg2Pattern** is a lightweight Python script that converts SVG paths into GLSL code using customizable macros.

It automatically parses SVG path elements, extracts fill colors, and converts vector commands into GLSL-compatible expressions.

The generated code can be directly integrated into GLSL shaders to render vector shapes using custom functions such as Bezier curves and SDFs.

## Features

- Automatic extraction of all SVG paths.
- Automatic fill color detection.
- Support for relative and absolute SVG commands.
- Cubic Bezier conversion.
- Quadratic Bezier conversion.
- Arc-to-Bezier conversion.
- Smooth curve support.
- GLSL-compatible floating-point formatting.
- Preserves relative coordinates where possible.

## Usage

Run the script with an SVG file as an argument:

```bash
python3 main.py <SVG_FILE>
```

### Example

```bash
python3 main.py linux-svgrepo-com.svg > result.txt
```

The generated GLSL code will be saved to `result.txt`.

Copy the generated output into your GLSL shader and place it inside your `SVG()` function.

## Example Output

```glsl
path( style(FILL,0x020204)
    m(106.95,0.0)
    c(-6.0,0.0,-12.02,1.18,-17.46,4.12)
    c(-5.78,3.11,-10.52,8.09,-13.43,13.97)
    z
);
```

## Requirements

- Python 3.8+
- No external dependencies required.

## TODO

- [ ] Add contour and stroke support.
- [ ] Support customizable output patterns without depending on `sample.glsl`.
- [ ] Improve handling of SVG transformations.
- [ ] Add support for gradients and opacity.
- [ ] Optimize generated GLSL for complex SVG files.

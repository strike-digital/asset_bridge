from pathlib import Path
import bpy
import gpu


def load_shader(vert_path: Path, frag_path: Path, geom_path: Path = "") -> gpu.types.GPUShader:
    """Creates a shader from a fragment and vertex glsl file"""
    if bpy.app.background:
        return None

    paths = [Path(vert_path), Path(frag_path)]
    if geom_path:
        paths.append(Path(geom_path))
    shader_texts = []

    for path in paths:
        if not path.is_absolute():
            path = Path(__file__).parents[1] / path
        with open(path, "r") as f:
            lines = f.readlines()
            text = ""
            for line in lines:
                if "#version" not in line:
                    text += line
            shader_texts.append(text)
    vert_shader = shader_texts[0]
    frag_shader = shader_texts[1]
    if len(shader_texts) == 3:
        geom_shader = shader_texts[2]
        return gpu.types.GPUShader(vert_shader, frag_shader, geocode=geom_shader)
    else:
        return gpu.types.GPUShader(vert_shader, frag_shader)


ASSET_PROGRESS_SHADER = load_shader(
    Path(__file__).parent / "shader_files" / "asset_progress.vert",
    Path(__file__).parent / "shader_files" / "asset_progress.frag",
)

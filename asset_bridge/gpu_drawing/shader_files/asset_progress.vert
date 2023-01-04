uniform mat4 ModelViewProjectionMatrix;

in vec2 pos;
in vec2 uv;

out vec2 Uv;

void main() {
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 0., 1.);
  Uv = uv;
}